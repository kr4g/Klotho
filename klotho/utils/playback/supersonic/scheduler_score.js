(function() {
  if (!globalThis.BrowserScheduler) return;
  if (globalThis.BrowserScheduler.prototype.setupTracks) return;

  var FIRST_PRIVATE_BUS = 16;
  var BUS_CHANNELS = 2;
  var CTRL_ENVELOPE_CHUNK = 200;

  var proto = globalThis.BrowserScheduler.prototype;

  proto._allocAudioBus = function() {
    var idx = this._nextAudioBus;
    this._nextAudioBus += BUS_CHANNELS;
    var g = globalThis.__klothoBusAlloc;
    if (this._nextAudioBus > g.nextAudio) g.nextAudio = this._nextAudioBus;
    return idx;
  };

  proto._allocControlBus = function() {
    var idx = this._nextControlBus++;
    var g = globalThis.__klothoBusAlloc;
    if (this._nextControlBus > g.nextControl) g.nextControl = this._nextControlBus;
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
    var manifestInserts = this.manifest.inserts || {};

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

          var mInsert = manifestInserts[fxDefName] || {};
          var inParam = mInsert.inParam || 'inBus';
          var outParam = mInsert.outParam || 'outBus';

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
    }

    var mainRouterId = sonic.nextNodeId();
    sonic.send('/s_new', '__busRouter', mainRouterId, 1, trackMap["main"].parentGroup,
      'inBus', mainFxBus, 'outBus', 0, 'gain', 1.0);

    if (!trackMap["default"]) {
      trackMap["default"] = trackMap["main"];
    }

    await sonic.sync();
    this._trackMap = trackMap;
  };

  proto.setupControlEnvelopes = async function(controlData, scoreGroupId) {
    if (!controlData || !controlData.bufferB64 || !controlData.descriptors || controlData.descriptors.length === 0) {
      this._controlBusMap = [];
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
    await sonic.sync();

    for (var off = 0; off < floats.length; off += CTRL_ENVELOPE_CHUNK) {
      var end = Math.min(off + CTRL_ENVELOPE_CHUNK, floats.length);
      var chunk = [];
      for (var ci = off; ci < end; ci++) chunk.push(floats[ci]);
      sonic.send.apply(sonic, ['/b_setn', bufnum, off, chunk.length].concat(chunk));
    }
    await sonic.sync();

    var ctrlGid = sonic.nextNodeId();
    sonic.send('/g_new', ctrlGid, 0, scoreGroupId);
    this._controlGroupId = ctrlGid;
    this._activeBuffers.push(bufnum);

    var descs = controlData.descriptors;
    var blockSize = controlData.blockSize || 512;
    this._controlBusMap = [];

    for (var di = 0; di < descs.length; di++) {
      var desc = descs[di];
      var ctrlBus = this._allocControlBus();
      this._controlBusMap.push({
        bus: ctrlBus,
        param: (desc.pfields && desc.pfields.length > 0) ? desc.pfields[0] : 'amp',
        targets: desc.targets || [],
        start: desc.start,
        dur: desc.dur,
        bufnum: bufnum,
        startFrame: desc.blockIndex * blockSize,
        numFrames: blockSize,
        controlGroupId: ctrlGid
      });
    }
  };

  proto._scheduleControlSynths = function(token) {
    if (!this._controlBusMap || this._controlBusMap.length === 0) return;
    var sonic = this.sonic;
    for (var i = 0; i < this._controlBusMap.length; i++) {
      var cm = this._controlBusMap[i];
      var ntp = this._playStartNTP + cm.start;
      var ctrlNodeId = sonic.nextNodeId();
      var args = ['__klEnvCtrl', ctrlNodeId, 0, cm.controlGroupId,
        'bufnum', cm.bufnum, 'bus', cm.bus, 'dur', cm.dur,
        'startFrame', cm.startFrame, 'numFrames', cm.numFrames];
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/s_new', args);
      sonic.sendOSC(bundle);
      cm.nodeId = ctrlNodeId;
    }
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
})();
