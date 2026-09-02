(function() {
  if (!globalThis.BrowserScheduler) return;
  // Feature guard doubles as the version-skew guard: when the versioned
  // core replaces a stale BrowserScheduler class, the new prototype has
  // no setupTracks yet, so this extension re-installs onto it; a stale
  // copy of this file running later sees the methods present and no-ops.
  // Keyed on the V2 marker (not setupTracks) so pages carrying a stale
  // pre-V2 copy from saved outputs get THIS build's preloadControlBuffer
  // (the pre-V2 one raced /b_alloc and left control envelopes silent).
  if (globalThis.BrowserScheduler.prototype.__klothoScoreExtV2) return;

  var FIRST_PRIVATE_BUS = 48; // keep in sync with scheduler_core.js
  var BUS_CHANNELS = 2;
  var CTRL_ENVELOPE_CHUNK = 200;
  // Widest single run any caller may ask for. A speaker array is capped far
  // below this (the hardware mirror carries at most 30 speakers), so a width
  // above it is a caller bug, not a venue — refuse rather than swallow a
  // quarter of the bus space on a typo.
  var MAX_BUS_WIDTH = 256;
  // Assumed audio-bus budget when the page cannot say what it booted with.
  // No stash means the engine was started by an output saved before 10.16,
  // when Klotho passed no scsynthOptions at all — so that engine booted on
  // SuperSonic's OWN defaults, and supersonic-scsynth@0.71.0 defaults
  // numAudioBusChannels to 128 (verified against the published dist bundle;
  // bootConfig and scsynthOptions both arrived in the same 10.16 commit, so
  // "no bootConfig" cannot mean "booted with a Klotho budget"). Guessing
  // higher would hand out buses scsynth does not have — silent cross-talk
  // between unrelated voices instead of a loud refusal, which is the exact
  // failure this fallback exists to prevent.
  var LEGACY_AUDIO_BUSES = 128;
  // Geometry-buffer layout, mirrored from klotho.thetos.spatial: N frames of
  // SIX channels, one frame per speaker lane, fields in the order
  // (delay_l, delay_r, gain_l, gain_r, shadow_l_hz, shadow_r_hz). The
  // compiled __spatialDecodeN blobs index those six positionally, so the
  // payload's own `stride` is checked against this rather than trusted --
  // "N*6 frames of 1 channel" holds the same floats and is MISREAD in
  // silence, which is the whole failure class this feature guards against.
  var BINAURAL_STRIDE = 6;
  // klotho.thetos.spatial.MAX_DECODER_SPEAKERS. SpeakerArray refuses wider at
  // construction, so a wider array reaching here means the payload did not
  // come from one -- and a too-wide decoder is exactly the def scsynth SKIPS
  // (one printed line, then the /s_new does nothing and the piece is silent).
  var MAX_SPATIAL_WIDTH = 32;

  var proto = globalThis.BrowserScheduler.prototype;

  // '__busRouter' at stereo, '__busRouterN' at every other width.
  //
  // Width 2 keeps the ORIGINAL undecorated name deliberately. __busRouter2 is
  // the same graph and would work, but a score with no speaker array has to
  // put the same bytes on the wire as it did before this feature existed, and
  // the def name is in those bytes.
  function routerDefName(width) {
    return (width === BUS_CHANNELS) ? '__busRouter' : '__busRouter' + width;
  }

  function decoderDefName(width) {
    return '__spatialDecode' + width;
  }

  // Refuse a spatial def this page was never sent.
  //
  // scsynth does not report a missing SynthDef: the /s_new names nothing, so
  // nothing is created and the track is SILENT with no message anywhere. The
  // registry is the page's merged asset table (engine.py ships one blob per
  // def name a payload needs), so a name missing from it means the width is
  // off the precompiled family -- refuse here, before any node exists, rather
  // than at the concert.
  //
  // No registry at all (a bare harness, or a page whose merge has not run) is
  // NOT evidence of absence, so the check stands down rather than guessing.
  function requireDef(name, why) {
    var reg = globalThis.__klothoSynthdefAssets;
    if (!reg || typeof reg !== 'object') return;
    if (Object.prototype.hasOwnProperty.call(reg, name)) return;
    throw new Error('[Klotho] this page has no SynthDef named ' + name
      + ', which ' + why + ' needs. Klotho precompiles the spatial family at '
      + 'widths 1, 2, 4, 6, 8, 12, 16, 24 and 32; a speaker count outside '
      + 'that list has no compiled def to send, and scsynth does not refuse a '
      + 'missing def -- it creates nothing and the array plays SILENTLY. '
      + 'Declare an array at one of those widths, or fold to stereo offline '
      + 'with klotho.thetos.spatial.fold_to_stereo, which has neither a '
      + 'wire-buffer budget nor a delay line. (Klotho refuses an off-family '
      + 'width in Python now, so a payload reaching here in this state was '
      + 'either hand-built or saved by an older release.)');
  }

  // How many audio bus CHANNELS this page's engine actually booted with.
  // ss_init stashes its boot config on globalThis.__klothoSonic; an engine
  // booted by a stale pre-10.16 output has no stash, which is exactly how the
  // recorder detects that page state too. getSystemReport() is deliberately
  // not consulted: it publishes the HARDWARE channel count
  // (audio.channelCount, which the bridge's stemCapacity reads), not the
  // private audio-bus count, so there is nothing there to read.
  proto._audioBusCapacity = function() {
    var n = 0;
    try {
      var st = globalThis.__klothoSonic;
      var so = st && st.bootConfig && st.bootConfig.scsynthOptions;
      if (so && so.numAudioBusChannels) n = so.numAudioBusChannels;
    } catch (e) {}
    return n || LEGACY_AUDIO_BUSES;
  };

  // Allocate a run of `width` CONSECUTIVE audio bus channels; returns the
  // first channel of the run.
  //
  // ONE cursor, ONE implementation: _allocAudioBus() below is literally
  // _allocAudioBusN(BUS_CHANNELS), so a stereo track and a 24-wide spatial
  // track draw from the same page-global __klothoBusAlloc. Two allocators
  // would be two chances to drift, and an overlap here is two unrelated
  // voices silently summing into each other — the exact failure this whole
  // feature exists to remove.
  //
  // A shared cursor is only half of it, and saying otherwise is what let a
  // real overlap ship: allocation being monotonic means nothing if a FREE
  // can wind the cursor back over somebody else's live range. The other
  // half is scheduler_core.js's _reclaimBusRuns, which gives back only the
  // runs this play allocated and only while they are on top of the cursor.
  //
  // Widths are rounded UP TO EVEN. scsynth imposes no alignment rule, and
  // correctness comes from the single monotonic cursor rather than from
  // parity — so this is a deliberate choice, not a requirement. The cursor
  // starts at an even floor (48) and every allocation in the tree today
  // steps it by 2, so it has always been even; one odd-width run would
  // de-align it permanently and every stereo pair allocated afterwards on
  // that page would straddle an odd boundary. Preserving the invariant costs
  // at most one wasted channel per odd-width run; losing it costs every bus
  // number in every log its match with the "pairs from 48" model this file
  // is written around.
  proto._allocAudioBusN = function(width) {
    if (typeof width !== 'number' || !isFinite(width)
        || Math.floor(width) !== width
        || width <= 0 || width > MAX_BUS_WIDTH) {
      throw new Error('[Klotho] audio bus width must be a whole number from 1 '
        + 'to ' + MAX_BUS_WIDTH + '; got ' + width + '. One bus channel per '
        + 'speaker: pass the number of channels the run has to carry.');
    }
    // Draw from the SHARED cursor when it has moved past this scheduler's
    // own copy of it. Two widgets whose play() calls interleave each
    // snapshot the cursor when they start, so the one that allocates second
    // would otherwise hand out channels the first has already taken.
    var g = globalThis.__klothoBusAlloc;
    var idx = Math.max(this._nextAudioBus, g.nextAudio);
    var w = width + (width & 1); // round up to even — see note above
    var capacity = this._audioBusCapacity();
    if (idx + w > capacity) {
      throw new Error('[Klotho] out of private audio buses: a ' + width
        + '-channel run at bus ' + idx + ' would reach ' + (idx + w)
        + ', past this page\'s engine budget of ' + capacity
        + ' audio bus channels (' + (capacity - FIRST_PRIVATE_BUS)
        + ' above the private floor of ' + FIRST_PRIVATE_BUS + '). Use fewer '
        + 'tracks, fewer inserts, or a smaller speaker array. If you upgraded '
        + 'Klotho since this engine started, reload the notebook page and '
        + 're-run the cells -- a running engine keeps the bus budget it '
        + 'booted with.');
    }
    this._nextAudioBus = idx + w;
    if (this._nextAudioBus > g.nextAudio) g.nextAudio = this._nextAudioBus;
    // Ledger entry for the reclaim in scheduler_core.js. Guarded because a
    // page could pair this file with an older core: no ledger there means
    // no reclaim, which leaks bus numbers — never an overlap.
    if (this._noteAudioBusRun) this._noteAudioBusRun(idx, this._nextAudioBus);
    return idx;
  };

  proto._allocAudioBus = function() {
    return this._allocAudioBusN(BUS_CHANNELS);
  };

  // Allocate one scsynth BUFFER number, from a single page-global cursor.
  //
  // AUD-126: the spatial geometry table and the control-envelope buffer used
  // to pick their bufnum with two copies of the same inline snippet, whose
  // fallback was "no __klothoSonic stash on the page means use 0". With no
  // stash BOTH preloads therefore allocated bufnum 0 and the second /b_alloc
  // replaced the first buffer's contents. Nothing raises: the decoder then
  // reads envelope samples as geometry (every speaker in the wrong place) or
  // the envelope reads geometry coefficients as levels. Same failure shape as
  // an audio-bus overlap, so it gets the same shape of answer as
  // __klothoBusAlloc -- ONE cursor, ONE implementation.
  //
  // __klothoSonic._nextBufnum stays authoritative WHEN THE STASH EXISTS,
  // because _lifecycle.js's sample loader draws its bufnums from that same
  // field. The two cursors are kept as one cursor by taking the max, so a
  // sample loaded between two preloads can never be handed out twice.
  proto._allocBufnum = function() {
    var g = globalThis.__klothoBufAlloc;
    if (!g) g = globalThis.__klothoBufAlloc = { next: 0 };
    var state = globalThis.__klothoSonic;
    if (state) {
      if (state._nextBufnum == null || state._nextBufnum < g.next) {
        state._nextBufnum = g.next;
      }
      g.next = state._nextBufnum;
    }
    var bufnum = g.next++;
    if (state) state._nextBufnum = g.next;
    return bufnum;
  };

  proto._allocControlBus = function() {
    var g = globalThis.__klothoBusAlloc;
    var idx = Math.max(this._nextControlBus, g.nextControl);
    this._nextControlBus = idx + 1;
    if (this._nextControlBus > g.nextControl) g.nextControl = this._nextControlBus;
    if (this._noteControlBusRun) this._noteControlBusRun(idx, this._nextControlBus);
    return idx;
  };

  proto._createScoreGroup = function() {
    var gid = this.sonic.nextNodeId();
    this.sonic.send('/g_new', gid, 0, 0);
    this._scoreGroupId = gid;
    this._groupId = gid;
    return gid;
  };

  // Read meta.spatial into the shape setupTracks needs, or null for a score
  // with no speaker array. Every refusal in here happens BEFORE a single
  // node or bus exists, so a rejected payload leaves the engine untouched.
  //
  // What it decides, and why those are the answers:
  //
  // * **main is as wide as the widest spatial track.** Every track sums into
  //   main, and a 24-wide track summing into a 2-wide main would write 22
  //   channels past the end of main's bus run -- straight onto whatever the
  //   allocator handed out next, which is another track's live audio. The
  //   main chain is the one place the whole array exists at once, so it is
  //   the place the array bus has to live.
  // * **the fold uses the WIDEST array's geometry.** The decoder reads main's
  //   bus, so its lane count is main's width; an array narrower than main
  //   cannot describe the lanes above its own. When the widest array is
  //   labels-only (no positions, hence no geometry) there is no fold at any
  //   width, and that is reported as decoder: null rather than invented.
  proto._spatialPlan = function(meta) {
    var sp = meta && meta.spatial;
    if (!sp || !sp.tracks) return null;
    var trackMeta = sp.tracks;
    var arrays = sp.arrays || {};
    var names = Object.keys(trackMeta);
    if (names.length === 0) return null;

    var widths = {};
    var mainWidth = BUS_CHANNELS;
    for (var i = 0; i < names.length; i++) {
      var nm = names[i];
      var w = (trackMeta[nm] || {}).width;
      if (typeof w !== 'number' || !isFinite(w) || Math.floor(w) !== w || w < 1) {
        throw new Error('[Klotho] spatial track ' + JSON.stringify(nm)
          + ' declares width '
          + (typeof w === 'string' ? JSON.stringify(w) : String(w))
          + '; a speaker count must be a whole number of at least 1.');
      }
      if (w > MAX_SPATIAL_WIDTH) {
        throw new Error('[Klotho] spatial track ' + JSON.stringify(nm)
          + ' declares ' + w + ' speakers and the decoder family stops at '
          + MAX_SPATIAL_WIDTH + '. SpeakerArray refuses a wider array at '
          + 'construction, so this payload was not built by one. Refusing '
          + 'here rather than sending it: scsynth would skip the oversized '
          + 'SynthDef and the array would play SILENTLY.');
      }
      widths[nm] = w;
      if (w > mainWidth) mainWidth = w;
    }

    // Deterministic pick among tracks tied at the widest width: main's own
    // array first (it is the chain the decoder sits on), then declaration
    // order. Ties matter only when two DIFFERENT arrays share the width --
    // they all sum lane-for-lane into one main bus, so exactly one geometry
    // can describe the result, and the composer is told which was used.
    var order = (meta.groups || []).slice();
    order.push('main');
    var widest = [];
    for (var oi = 0; oi < order.length; oi++) {
      if (widths[order[oi]] === mainWidth && widest.indexOf(order[oi]) === -1) {
        widest.push(order[oi]);
      }
    }
    for (var ni = 0; ni < names.length; ni++) {
      if (widths[names[ni]] === mainWidth && widest.indexOf(names[ni]) === -1) {
        widest.push(names[ni]);
      }
    }
    var chosen = (widest.indexOf('main') !== -1) ? 'main' : widest[0];
    var arrayName = chosen != null ? (trackMeta[chosen] || {}).array : null;
    var arrayMeta = (arrayName != null) ? arrays[arrayName] : null;
    var decoder = (arrayMeta && arrayMeta.decoder) || null;

    var distinct = [];
    for (var wi = 0; wi < widest.length; wi++) {
      var an = (trackMeta[widest[wi]] || {}).array;
      if (an != null && distinct.indexOf(an) === -1) distinct.push(an);
    }
    if (distinct.length > 1) {
      console.warn('[Klotho] tracks ' + widest.join(', ') + ' declare '
        + distinct.length + ' different speaker arrays (' + distinct.join(', ')
        + ') at the same width. They sum lane for lane onto one set of '
        + 'speakers; the headphone fold uses ' + JSON.stringify(arrayName)
        + "'s geometry.");
    }

    if (decoder) {
      var stride = decoder.stride;
      var coeffs = decoder.coefficients;
      if (stride !== BINAURAL_STRIDE) {
        throw new Error('[Klotho] the geometry table for array '
          + JSON.stringify(arrayName) + ' declares stride ' + stride
          + ' and the compiled decoders index ' + BINAURAL_STRIDE
          + ' fields per lane positionally. Loading it would misread every '
          + 'lane -- a silent geometry error, not a load failure.');
      }
      if (!coeffs || coeffs.length !== mainWidth * BINAURAL_STRIDE) {
        throw new Error('[Klotho] the geometry table for array '
          + JSON.stringify(arrayName) + ' has '
          + (coeffs ? coeffs.length : 'no') + ' floats; a ' + mainWidth
          + '-lane decoder needs exactly '
          + (mainWidth * BINAURAL_STRIDE) + '.');
      }
      requireDef(decoderDefName(mainWidth),
        'the ' + mainWidth + '-speaker headphone fold');
    }

    // Every router width the chain will name, checked once, up front.
    var seen = {};
    for (var ci = 0; ci < names.length; ci++) seen[widths[names[ci]]] = true;
    seen[mainWidth] = true;
    for (var key in seen) {
      if (!seen.hasOwnProperty(key)) continue;
      var wdt = Number(key);
      requireDef(routerDefName(wdt), 'a ' + wdt + '-channel track chain');
    }

    return {
      widths: widths,
      mainWidth: mainWidth,
      arrayName: arrayName,
      decoderTrack: chosen,
      decoder: decoder,
      // One key per distinct geometry table, so a replay of the same widget
      // reuses the buffer it already uploaded instead of allocating another.
      geomKey: arrayName + '|' + mainWidth
    };
  };

  proto.setupTracks = async function(meta, scoreGroupId) {
    if (!meta || (!meta.groups && !meta.inserts && !meta.spatial)) {
      this._trackMap = null;
      return;
    }

    var sonic = this.sonic;
    var trackNames = (meta.groups || []).slice();
    var insertSpecs = meta.inserts || {};
    var trackMap = {};

    // Refusals first: nothing below runs against a payload that cannot work.
    var spatial = this._spatialPlan(meta);
    var mainWidth = spatial ? spatial.mainWidth : BUS_CHANNELS;
    function widthOf(name) {
      if (!spatial) return BUS_CHANNELS;
      var w = spatial.widths[name];
      return (typeof w === 'number') ? w : BUS_CHANNELS;
    }

    for (var t = 0; t < trackNames.length; t++) {
      var nm = trackNames[t];
      var nmWidth = widthOf(nm);
      var parentGid = sonic.nextNodeId();
      var srcGid = sonic.nextNodeId();
      var fxGid = sonic.nextNodeId();
      // One bus CHANNEL per speaker. A stereo track is the width-2 case of
      // the same call, so both draw from the one page-global cursor.
      var srcBus = this._allocAudioBusN(nmWidth);
      var fxBus = this._allocAudioBusN(nmWidth);

      sonic.send('/g_new', parentGid, 1, scoreGroupId);
      sonic.send('/g_new', srcGid, 0, parentGid);
      sonic.send('/g_new', fxGid, 3, srcGid);

      trackMap[nm] = {
        parentGroup: parentGid,
        srcGroup: srcGid,
        fxGroup: fxGid,
        srcBus: srcBus,
        fxBus: fxBus,
        width: nmWidth,
        insertNodes: {}
      };
    }

    var mainParentGid = sonic.nextNodeId();
    var mainSrcGid = sonic.nextNodeId();
    var mainFxGid = sonic.nextNodeId();
    var mainSrcBus = this._allocAudioBusN(mainWidth);
    var mainFxBus = this._allocAudioBusN(mainWidth);

    sonic.send('/g_new', mainParentGid, 1, scoreGroupId);
    sonic.send('/g_new', mainSrcGid, 0, mainParentGid);
    sonic.send('/g_new', mainFxGid, 3, mainSrcGid);

    trackMap["main"] = {
      parentGroup: mainParentGid,
      srcGroup: mainSrcGid,
      fxGroup: mainFxGid,
      srcBus: mainSrcBus,
      fxBus: mainFxBus,
      width: mainWidth,
      insertNodes: {}
    };

    // Score.track() checks an insert's channel count against the track's
    // speaker count -- but only for a track that DECLARES speakers. main
    // here declares none and was widened by a sub-track, so its inserts were
    // accepted as stereo and are about to be placed on a wide chain, where
    // they read two lanes and write two: every lane above the first pair
    // reaches main's post-FX bus unwritten, and those speakers go silent.
    // Nothing downstream would say so, hence this.
    if (spatial && mainWidth > BUS_CHANNELS
        && spatial.widths['main'] == null
        && insertSpecs['main'] && insertSpecs['main'].length > 0) {
      console.warn('[Klotho] the master chain has inserts and main was '
        + 'widened to ' + mainWidth + ' channels by a spatial track, but main '
        + 'declares no speakers of its own -- so those inserts were only ever '
        + 'checked as STEREO. A stereo insert on a ' + mainWidth
        + '-channel chain reads and writes two lanes and leaves the other '
        + (mainWidth - BUS_CHANNELS) + ' unwritten: those speakers will be '
        + 'SILENT. Declare the master with its array too -- '
        + "score.track('main', speakers=..., inserts=[...]) -- so the widths "
        + 'are checked, or take the inserts off main.');
    }

    // The unguarded SIBLING of the warning above, and the reason it needed
    // one: main DECLARING an array does not make the widths agree, it only
    // makes the test above false. A main declared at two speakers while
    // another track declares twenty-four is still built at twenty-four --
    // main's own array then describes lanes 0..1 of a bus that is 24 wide,
    // its inserts were width-checked against 2 and bridge lanes 0..1 alone
    // (measured on the shipped defs: kl_reverb writes fxBus 120-121 while
    // __spatialDecode24 reads 120-143), and main is not in the decoder
    // tie-break at all, so the fold silently uses another track's geometry.
    //
    // Klotho refuses this at lowering now, in Python, where the composer can
    // read it -- converters._build_spatial_meta. This stays for the payloads
    // Python did not build: a saved output from an older release, or a
    // hand-written meta.
    var declaredMain = spatial ? spatial.widths['main'] : null;
    if (spatial && declaredMain != null && declaredMain < mainWidth) {
      var mainSpecs = insertSpecs['main'] || [];
      // The widener is usually another track, but it can be the stereo
      // FLOOR: mainWidth starts at BUS_CHANNELS, so a lone speakers=[1] on
      // main is narrower than its own chain with no track to blame.
      var widener = null;
      for (var wn in spatial.widths) {
        if (wn !== 'main' && spatial.widths[wn] === mainWidth) {
          widener = wn;
          break;
        }
      }
      console.warn('[Klotho] main declares ' + declaredMain + ' speakers but '
        + (widener !== null
            ? 'track ' + JSON.stringify(widener) + ' declares ' + mainWidth
              + ', and every track sums into main'
            : 'a master chain is never narrower than a stereo pair')
        + ' -- so main\'s chain is built ' + mainWidth + ' channels '
        + 'wide and the ' + declaredMain + '-speaker array declared on it '
        + 'describes only lanes 0..' + (declaredMain - 1) + ' of it. '
        + (mainSpecs.length > 0
            ? 'Main\'s ' + mainSpecs.length + ' insert(s) were checked '
              + 'against ' + declaredMain + ' channels and leave the other '
              + (mainWidth - declaredMain) + ' lanes of main\'s post-FX bus '
              + 'unwritten: those speakers will be SILENT. '
            : widener !== null
              ? 'Main is also out of the decoder tie-break, so the headphone '
                + 'fold uses ' + JSON.stringify(widener) + '\'s geometry and '
                + 'not the one declared here -- SILENT about the '
                + 'substitution. '
              : 'Nothing is as wide as the chain main is built at, so the '
                + 'decoder tie-break selects no track at all and this score '
                + 'gets NO headphone fold -- reported below as "labels but '
                + 'no positions", which is not what happened. ')
        + "Declare main at the full array (score.track('main', "
        + 'speakers=<the widest array>, ...)), or leave speakers= off main '
        + 'entirely (score.track(\'main\', speakers=[]) to un-declare) so it '
        + 'is widened to fit.');
    }

    var allTracks = trackNames.concat(["main"]);
    for (var ti = 0; ti < allTracks.length; ti++) {
      var tName = allTracks[ti];
      var track = trackMap[tName];
      var specs = insertSpecs[tName];
      var chainWidth = track.width;
      var chainRouter = routerDefName(chainWidth);

      if (!specs || specs.length === 0) {
        var bypassId = sonic.nextNodeId();
        sonic.send('/s_new', chainRouter, bypassId, 0, track.fxGroup,
          'inBus', track.srcBus, 'outBus', track.fxBus, 'gain', 1.0);
        track.insertNodes['__bypass'] = bypassId;
      } else {
        var prevBus = track.srcBus;
        for (var fi = 0; fi < specs.length; fi++) {
          var spec = specs[fi];
          // Intermediate buses are as wide as the chain. Score.track()
          // already refused any insert that does not read and write exactly
          // this many channels, so the width is wired, not re-checked.
          var nextBus = (fi < specs.length - 1)
            ? this._allocAudioBusN(chainWidth) : track.fxBus;
          var fxDefName = spec.defName;
          var fxUid = spec.uid;
          var fxArgs = spec.args || {};

          var inParam = 'inBus';
          var outParam = 'outBus';

          var fxNodeId = sonic.nextNodeId();
          var fxArgList = [fxDefName, fxNodeId, 1, track.fxGroup,
            inParam, prevBus, outParam, nextBus];
          var argKeys = Object.keys(fxArgs);
          for (var ai = 0; ai < argKeys.length; ai++) {
            fxArgList.push(argKeys[ai], fxArgs[argKeys[ai]]);
          }
          sonic.send.apply(sonic, ['/s_new'].concat(fxArgList));

          track.insertNodes[fxUid] = fxNodeId;
          this.nodeMap.set(fxUid, fxNodeId);
          this._defNames.set(fxUid, fxDefName);

          prevBus = nextBus;
        }
      }
    }

    // Each track sums into main at ITS OWN width, starting at main's lane 0.
    // For a spatial track that is speaker-for-speaker, because main's lanes
    // ARE the speakers. For a stereo track in a spatial score it means the
    // first two speakers of the array: a stereo signal names no speaker, the
    // room has no other place to put it, and every lane of main reaches the
    // listener through the fold, so the material stays audible instead of
    // being dropped for want of a speaker assignment.
    var narrow = [];
    for (var ri = 0; ri < trackNames.length; ri++) {
      var rName = trackNames[ri];
      var rTrack = trackMap[rName];
      var routerId = sonic.nextNodeId();
      sonic.send('/s_new', routerDefName(rTrack.width), routerId, 1,
        rTrack.parentGroup,
        'inBus', rTrack.fxBus, 'outBus', mainSrcBus, 'gain', 1.0);
      rTrack.routerNode = routerId;
      if (rTrack.width < mainWidth) narrow.push(rName);
    }
    if (narrow.length > 0) {
      console.warn('[Klotho] no speakers are declared for: ' + narrow.join(', ')
        + '. Those tracks play through the first ' + BUS_CHANNELS
        + ' speakers of the array (lanes 0 and 1), because a stereo signal '
        + 'names no speaker and the room has nowhere else to put it. Declare '
        + 'the track with speakers= to place it anywhere else.');
    }

    if (spatial && spatial.decoder) {
      // The headphone fold: N lanes in, hardware 0/1 out, so a 24-speaker
      // score auditions on a stereo interface. addToTail of main's parent
      // group puts it after main's own source and FX groups -- and main's
      // group is the last child of the score group, so every track router
      // has already written the array by the time this reads it.
      await this._preloadSpatialGeometry(spatial);
      var decId = sonic.nextNodeId();
      sonic.send('/s_new', decoderDefName(mainWidth), decId, 1,
        trackMap["main"].parentGroup,
        'inBus', mainFxBus, 'outBus', 0,
        'bufnum', this._geomPreload.bufnum, 'gain', 1.0);
      trackMap["main"].decoderNode = decId;
      trackMap["main"].routerNode = decId;
    } else {
      // No geometry, no fold. The stock STEREO router is still the right
      // output stage even for a wide main: an N-wide router onto hardware
      // bus 0 would spray lanes 2..N-1 across the output channels the stem
      // taps live on. Lanes 0/1 monitored, everything else inaudible --
      // said out loud, because an unheard speaker is the failure nobody
      // notices.
      var mainRouterId = sonic.nextNodeId();
      sonic.send('/s_new', '__busRouter', mainRouterId, 1,
        trackMap["main"].parentGroup,
        'inBus', mainFxBus, 'outBus', 0, 'gain', 1.0);
      trackMap["main"].routerNode = mainRouterId;
      if (spatial) {
        console.warn('[Klotho] the speaker array on this score carries labels '
          + 'but no positions, so there is no geometry to fold with. Only '
          + 'speakers 1 and 2 reach the output; the rest are routed but '
          + 'inaudible here. Declare the track with a SpeakerArray (which '
          + 'carries positions) for a headphone audition.');
      }
    }

    if (!trackMap["default"]) {
      trackMap["default"] = trackMap["main"];
    }

    // No sync round-trip on the ordinary path: OSC messages are processed
    // in order, so the group/insert /s_new burst above always lands before
    // the timestamped note bundles sent afterwards, and the scheduler's
    // startup cushion covers engine-side processing. In postMessage mode
    // (Colab/Jupyter) a sync costs ~300ms of press-to-sound latency. A
    // spatial score pays exactly one, on its FIRST play only -- see
    // _preloadSpatialGeometry, where /b_alloc makes it unavoidable.
    this._trackMap = trackMap;
    this._trackOrder = trackNames.slice();
  };

  // Upload one array's geometry table, once per widget.
  //
  // Same /b_alloc -> /sync -> /b_setn fence as preloadControlBuffer, for the
  // same reason: /b_alloc is an ASYNC scsynth command, so fills sent straight
  // after it land on a buffer that does not exist yet and are dropped. The
  // decoder would then read a buffer of zeros -- and a zero shadow cutoff is
  // a one-pole coefficient of exactly 1.0, which mutes the lane. Every
  // speaker silent, no error anywhere.
  //
  // Cached on the scheduler, not in _activeBuffers: the table is fixed for
  // the widget's lifetime, so a replay reuses it and pays no fence. Freed by
  // releaseControlPreload, the bridge's teardown hook.
  proto._preloadSpatialGeometry = function(plan) {
    if (this._geomPreload && this._geomPreload.key === plan.geomKey) {
      return this._geomPreload.ready;
    }
    var sonic = this.sonic;
    var coeffs = plan.decoder.coefficients;
    var width = plan.mainWidth;

    var bufnum = this._allocBufnum();

    // N frames of SIX channels. The same floats in an "N*6 frames of 1"
    // buffer are read as six consecutive lanes' worth of numbers by
    // BufRd.kr(6, buf, lane) -- every speaker in the wrong place, silently.
    sonic.send('/b_alloc', bufnum, width, BINAURAL_STRIDE);

    var ready = (async function() {
      try { await sonic.sync(); } catch (e) {}
      for (var off = 0; off < coeffs.length; off += CTRL_ENVELOPE_CHUNK) {
        var end = Math.min(off + CTRL_ENVELOPE_CHUNK, coeffs.length);
        var chunk = [];
        for (var ci = off; ci < end; ci++) chunk.push(coeffs[ci]);
        sonic.send.apply(sonic, ['/b_setn', bufnum, off, chunk.length].concat(chunk));
      }
    })();

    this._geomPreload = {
      bufnum: bufnum, key: plan.geomKey, width: width,
      stride: BINAURAL_STRIDE, ready: ready
    };
    return ready;
  };

  proto.releaseSpatialGeometry = function() {
    if (!this._geomPreload) return;
    try { this.sonic.send('/b_free', this._geomPreload.bufnum); } catch (e) {}
    this._geomPreload = null;
  };

  // Stems recording: one extra __busRouter per non-main track, placed
  // AFTER that track's summing router so it reads the post-fader signal
  // off the track's fxBus (the router's ReplaceOut has already run) and
  // sums it onto a dedicated hardware output pair for the capture node.
  // The master pair (out 0/1) needs no tap. Taps live inside the track
  // groups, so the normal /g_freeAll teardown frees them.
  proto.setupStemTaps = function() {
    if (!this._trackMap || !this._trackOrder) return null;
    var STEM_OUT_BASE = 2;
    var MAX_STEMS = 15; // output channels 2..31
    var sonic = this.sonic;
    var names = this._trackOrder;
    if (names.length > MAX_STEMS) {
      console.warn('[Klotho] stems: only the first ' + MAX_STEMS + ' of '
        + names.length + ' tracks get separate stems (output-channel limit).');
      names = names.slice(0, MAX_STEMS);
    }
    var layout = [];
    var folded = [];
    for (var i = 0; i < names.length; i++) {
      var track = this._trackMap[names[i]];
      if (!track || track.routerNode == null) continue;
      // A stem pair is two hardware channels wide and the next track's pair
      // starts two channels later, so a spatial track's stem carries its
      // first two speakers and no more. Said out loud rather than quietly
      // handing back a stem that is missing most of the music.
      if (track.width > 2) folded.push(names[i]);
      var outCh = STEM_OUT_BASE + 2 * i;
      var tapId = sonic.nextNodeId();
      sonic.send('/s_new', '__busRouter', tapId, 3, track.routerNode,
        'inBus', track.fxBus, 'outBus', outCh, 'gain', 1.0);
      layout.push({ name: names[i], ch: [outCh, outCh + 1] });
    }
    if (folded.length > 0) {
      console.warn('[Klotho] stems: ' + folded.join(', ') + ' have more than '
        + 'two speakers, and a stem is a stereo pair -- those stems carry '
        + 'speakers 1 and 2 only. Record the full mix for the headphone fold '
        + 'of the whole array.');
    }
    return layout;
  };

  // Upload the control-envelope buffer once per widget. Called from the
  // widget's ensureReady so the /b_alloc + /b_setn cost is paid at init,
  // not on press-to-play, and replays reuse the same buffer. /b_alloc is
  // an ASYNC scsynth command (completes on the NRT thread after later
  // messages have already been processed), so the /b_setn fills must
  // wait behind a /sync round-trip — sent immediately they land on the
  // not-yet-allocated buffer and are dropped, leaving every envelope
  // reading zeros (mapped params pinned to 0 = silent voices). Returns
  // the fill-completion promise; setupControlEnvelopes awaits it before
  // any __klEnvCtrl can read the buffer.
  proto.preloadControlBuffer = function(controlData) {
    if (this._ctrlPreload) return this._ctrlPreload.ready;
    if (!controlData || !controlData.bufferB64 || !controlData.descriptors || controlData.descriptors.length === 0) {
      return;
    }

    var sonic = this.sonic;

    var raw = atob(controlData.bufferB64);
    var ab = new ArrayBuffer(raw.length);
    var u8 = new Uint8Array(ab);
    for (var i = 0; i < raw.length; i++) u8[i] = raw.charCodeAt(i);
    var floats = new Float32Array(ab);

    var bufnum = this._allocBufnum();

    sonic.send('/b_alloc', bufnum, controlData.numFrames, 1);

    var ready = (async function() {
      try { await sonic.sync(); } catch (e) {}
      for (var off = 0; off < floats.length; off += CTRL_ENVELOPE_CHUNK) {
        var end = Math.min(off + CTRL_ENVELOPE_CHUNK, floats.length);
        var chunk = [];
        for (var ci = off; ci < end; ci++) chunk.push(floats[ci]);
        sonic.send.apply(sonic, ['/b_setn', bufnum, off, chunk.length].concat(chunk));
      }
    })();

    // The buffer lives for the widget's lifetime (NOT in _activeBuffers,
    // which is freed on ring-out); the widget's orphan cleanup calls
    // releaseControlPreload.
    this._ctrlPreload = { bufnum: bufnum, floats: floats, ready: ready };
    return ready;
  };

  proto.releaseControlPreload = function() {
    // The bridge's orphan cleanup is the only widget-teardown hook the
    // scheduler is given, and the geometry buffer has exactly the same
    // per-widget lifetime for exactly the same reason, so it is freed here
    // too rather than being left to leak a bufnum per widget.
    this.releaseSpatialGeometry();
    if (!this._ctrlPreload) return;
    try { this.sonic.send('/b_free', this._ctrlPreload.bufnum); } catch (e) {}
    this._ctrlPreload = null;
  };

  proto.setupControlEnvelopes = async function(controlData, scoreGroupId) {
    if (!controlData || !controlData.descriptors || controlData.descriptors.length === 0) {
      this._controlBusMap = [];
      return;
    }

    var preloadReady = this.preloadControlBuffer(controlData);
    if (!this._ctrlPreload) {
      this._controlBusMap = [];
      return;
    }
    if (preloadReady) await preloadReady;

    var sonic = this.sonic;
    var bufnum = this._ctrlPreload.bufnum;
    var floats = this._ctrlPreload.floats;

    var ctrlGid = sonic.nextNodeId();
    sonic.send('/g_new', ctrlGid, 0, scoreGroupId);
    this._controlGroupId = ctrlGid;

    var descs = controlData.descriptors;
    var blockSize = controlData.blockSize || 512;
    this._controlBusMap = [];

    for (var di = 0; di < descs.length; di++) {
      var desc = descs[di];
      var ctrlBus = this._allocControlBus();
      var startFrame = desc.blockIndex * blockSize;
      // Preset the (possibly recycled) bus to the envelope's first value
      // so a mapped param can never read a stale level in the gap before
      // its __klEnvCtrl synth starts writing.
      var firstValue = (startFrame < floats.length) ? floats[startFrame] : 0;
      sonic.send('/c_set', ctrlBus, firstValue);
      // AUD-75: the WHOLE pfield list, not just the first one.
      //
      // ``apply_envelope(env, ['amp', 'pan'], node, control=True)`` is a
      // single ordinary call and it produces ONE descriptor carrying both
      // names. Keeping only ``pfields[0]`` mapped ``amp`` to the envelope
      // bus and left ``pan`` on the staircase baked at lowering time --
      // while ``uc.events`` reported both as enveloped. No error, no
      // warning: the second parameter simply did not move.
      this._controlBusMap.push({
        bus: ctrlBus,
        params: (desc.pfields && desc.pfields.length > 0)
          ? desc.pfields.slice()
          : ['amp'],
        targets: desc.targets || [],
        start: desc.start,
        dur: desc.dur,
        bufnum: bufnum,
        startFrame: startFrame,
        numFrames: blockSize,
        controlGroupId: ctrlGid
      });
    }
  };

  // Control-envelope synths join the core's unified send plan as 'ctrl'
  // items (due at each envelope's start) instead of being sent all at once
  // at play start — front-loading them would occupy engine scheduler-queue
  // slots for the whole piece. The batch planner calls _sendControlItem
  // when a ctrl item's stretch of the timeline comes up.
  proto._controlStreamItems = function() {
    if (!this._controlBusMap || this._controlBusMap.length === 0) return [];
    var items = [];
    for (var i = 0; i < this._controlBusMap.length; i++) {
      var cm = this._controlBusMap[i];
      items.push({ kind: 'ctrl', start: cm.start, cm: cm });
    }
    return items;
  };

  proto._sendControlItem = function(cm, ntp) {
    var ctrlNodeId = this.sonic.nextNodeId();
    var args = ['__klEnvCtrl', ctrlNodeId, 0, cm.controlGroupId,
      'bufnum', cm.bufnum, 'bus', cm.bus, 'dur', cm.dur,
      'startFrame', cm.startFrame, 'numFrames', cm.numFrames];
    var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/s_new', args);
    this._sendScheduled(ntp, bundle);
    cm.nodeId = ctrlNodeId;
  };

  proto._getControlMappingsForEvent = function(evId, evStart) {
    if (!this._controlBusMap || this._controlBusMap.length === 0) return null;
    var mappings = null;
    for (var i = 0; i < this._controlBusMap.length; i++) {
      var cm = this._controlBusMap[i];
      if (!cm.targets) continue;
      for (var j = 0; j < cm.targets.length; j++) {
        var tgt = cm.targets[j];
        if (tgt && tgt.id === evId) {
          if (!mappings) mappings = [];
          var deferred = (evStart != null) && (tgt.startTime > evStart + 1e-9);
          // One mapping per declared pfield (AUD-75). Both /n_map emitters
          // in scheduler_core.js already loop over whatever this returns,
          // so widening the list here is the whole fix.
          var params = cm.params || [];
          for (var pi = 0; pi < params.length; pi++) {
            mappings.push({
              param: params[pi],
              bus: cm.bus,
              startTime: tgt.startTime,
              deferred: deferred
            });
          }
          break;
        }
      }
    }
    return mappings;
  };

  proto.__klothoScoreExtV2 = true;
})();
