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

  var proto = globalThis.BrowserScheduler.prototype;

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

  proto.setupTracks = async function(meta, scoreGroupId) {
    if (!meta || (!meta.groups && !meta.inserts)) {
      this._trackMap = null;
      return;
    }

    var sonic = this.sonic;
    var trackNames = (meta.groups || []).slice();
    var insertSpecs = meta.inserts || {};
    var trackMap = {};

    for (var t = 0; t < trackNames.length; t++) {
      var nm = trackNames[t];
      var parentGid = sonic.nextNodeId();
      var srcGid = sonic.nextNodeId();
      var fxGid = sonic.nextNodeId();
      var srcBus = this._allocAudioBus();
      var fxBus = this._allocAudioBus();

      sonic.send('/g_new', parentGid, 1, scoreGroupId);
      sonic.send('/g_new', srcGid, 0, parentGid);
      sonic.send('/g_new', fxGid, 3, srcGid);

      trackMap[nm] = {
        parentGroup: parentGid,
        srcGroup: srcGid,
        fxGroup: fxGid,
        srcBus: srcBus,
        fxBus: fxBus,
        insertNodes: {}
      };
    }

    var mainParentGid = sonic.nextNodeId();
    var mainSrcGid = sonic.nextNodeId();
    var mainFxGid = sonic.nextNodeId();
    var mainSrcBus = this._allocAudioBus();
    var mainFxBus = this._allocAudioBus();

    sonic.send('/g_new', mainParentGid, 1, scoreGroupId);
    sonic.send('/g_new', mainSrcGid, 0, mainParentGid);
    sonic.send('/g_new', mainFxGid, 3, mainSrcGid);

    trackMap["main"] = {
      parentGroup: mainParentGid,
      srcGroup: mainSrcGid,
      fxGroup: mainFxGid,
      srcBus: mainSrcBus,
      fxBus: mainFxBus,
      insertNodes: {}
    };

    var allTracks = trackNames.concat(["main"]);
    for (var ti = 0; ti < allTracks.length; ti++) {
      var tName = allTracks[ti];
      var track = trackMap[tName];
      var specs = insertSpecs[tName];

      if (!specs || specs.length === 0) {
        var bypassId = sonic.nextNodeId();
        sonic.send('/s_new', '__busRouter', bypassId, 0, track.fxGroup,
          'inBus', track.srcBus, 'outBus', track.fxBus, 'gain', 1.0);
        track.insertNodes['__bypass'] = bypassId;
      } else {
        var prevBus = track.srcBus;
        for (var fi = 0; fi < specs.length; fi++) {
          var spec = specs[fi];
          var nextBus = (fi < specs.length - 1) ? this._allocAudioBus() : track.fxBus;
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

    for (var ri = 0; ri < trackNames.length; ri++) {
      var rName = trackNames[ri];
      var rTrack = trackMap[rName];
      var routerId = sonic.nextNodeId();
      sonic.send('/s_new', '__busRouter', routerId, 1, rTrack.parentGroup,
        'inBus', rTrack.fxBus, 'outBus', mainSrcBus, 'gain', 1.0);
      rTrack.routerNode = routerId;
    }

    var mainRouterId = sonic.nextNodeId();
    sonic.send('/s_new', '__busRouter', mainRouterId, 1, trackMap["main"].parentGroup,
      'inBus', mainFxBus, 'outBus', 0, 'gain', 1.0);
    trackMap["main"].routerNode = mainRouterId;

    if (!trackMap["default"]) {
      trackMap["default"] = trackMap["main"];
    }

    // No sync round-trip here: OSC messages are processed in order, so
    // the group/insert /s_new burst above always lands before the
    // timestamped note bundles sent afterwards, and the scheduler's
    // startup cushion covers engine-side processing. In postMessage mode
    // (Colab/Jupyter) a sync costs ~300ms of press-to-sound latency.
    this._trackMap = trackMap;
    this._trackOrder = trackNames.slice();
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
    for (var i = 0; i < names.length; i++) {
      var track = this._trackMap[names[i]];
      if (!track || track.routerNode == null) continue;
      var outCh = STEM_OUT_BASE + 2 * i;
      var tapId = sonic.nextNodeId();
      sonic.send('/s_new', '__busRouter', tapId, 3, track.routerNode,
        'inBus', track.fxBus, 'outBus', outCh, 'gain', 1.0);
      layout.push({ name: names[i], ch: [outCh, outCh + 1] });
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

    var bufnum = 0;
    var sharedState = globalThis.__klothoSonic;
    if (sharedState && sharedState._nextBufnum != null) {
      bufnum = sharedState._nextBufnum++;
    } else if (sharedState) {
      sharedState._nextBufnum = 1;
      bufnum = 0;
    }

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
      this._controlBusMap.push({
        bus: ctrlBus,
        param: (desc.pfields && desc.pfields.length > 0) ? desc.pfields[0] : 'amp',
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
          mappings.push({
            param: cm.param,
            bus: cm.bus,
            startTime: tgt.startTime,
            deferred: deferred
          });
          break;
        }
      }
    }
    return mappings;
  };

  proto.__klothoScoreExtV2 = true;
})();
