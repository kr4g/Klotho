(function() {
  if (globalThis.BrowserScheduler) return;

  var MAX_EVENTS_PER_BATCH = 500;
  var BATCH_OVERLAP_RATIO = 0.8;
  var NTP_EPOCH_OFFSET = 2208988800;
  var STARTUP_DELAY = 0.1;
  var DEFAULT_RING_TIME = 5;
  var FIRST_PRIVATE_BUS = 16;
  var BUS_CHANNELS = 2;
  var CTRL_ENVELOPE_CHUNK = 200;

  function getNTP() {
    return (performance.timeOrigin + performance.now()) / 1000 + NTP_EPOCH_OFFSET;
  }

  globalThis.BrowserScheduler = class {
    constructor(config) {
      this.sonic = config.sonic;
      this.manifest = config.manifest || { synths: {}, inserts: {} };
      this.ringTime = (config.ringTime != null) ? config.ringTime : DEFAULT_RING_TIME;

      this.isPlaying = false;
      this.stopToken = 0;
      this.nodeMap = new Map();
      this._defNames = new Map();

      this._scoreGroupId = null;
      this._groupId = null;
      this._trackMap = null;
      this._controlGroupId = null;
      this._controlBusMap = [];
      this._nextAudioBus = FIRST_PRIVATE_BUS;
      this._nextControlBus = 0;
      this._activeBuffers = [];

      this._playStartNTP = 0;
      this._playStartPerfMs = 0;
      this._batchTimeoutId = null;
      this._finishTimeoutId = null;
      this._loopTickId = null;
      this._deferredRings = [];

      this.drawScheduler = new DrawScheduler();
      this.onEvent = null;
      this.onFinish = null;
    }

    _allocAudioBus() {
      var idx = this._nextAudioBus;
      this._nextAudioBus += BUS_CHANNELS;
      return idx;
    }

    _allocControlBus() {
      return this._nextControlBus++;
    }

    _createScoreGroup() {
      var gid = this.sonic.nextNodeId();
      this.sonic.send('/g_new', gid, 0, 0);
      this._scoreGroupId = gid;
      this._groupId = gid;
      return gid;
    }

    _createGroup() {
      var gid = this.sonic.nextNodeId();
      this.sonic.send('/g_new', gid, 0, 0);
      this._groupId = gid;
    }

    _freeGroup() {
      var gid = this._scoreGroupId || this._groupId;
      if (gid == null) return;
      try { this.sonic.send('/g_freeAll', gid); } catch(e) {}
      try { this.sonic.send('/n_free', gid); } catch(e) {}
      this._scoreGroupId = null;
      this._groupId = null;
      this._freeBuffers();
    }

    _freeGroupDeferred(groupId) {
      var sonic = this.sonic;
      var self = this;
      var ringMs = this.ringTime * 1000;
      var bufs = this._activeBuffers.slice();
      var tid = setTimeout(function() {
        try { sonic.send('/g_freeAll', groupId); } catch(e) {}
        try { sonic.send('/n_free', groupId); } catch(e) {}
        for (var i = 0; i < bufs.length; i++) {
          try { sonic.send('/b_free', bufs[i]); } catch(e) {}
        }
      }, ringMs);
      this._deferredRings.push({ tid: tid, gid: groupId });
      this._activeBuffers = [];
    }

    _freeBuffers() {
      for (var i = 0; i < this._activeBuffers.length; i++) {
        try { this.sonic.send('/b_free', this._activeBuffers[i]); } catch(e) {}
      }
      this._activeBuffers = [];
    }

    _cancelAllDeferredRings() {
      for (var i = 0; i < this._deferredRings.length; i++) {
        clearTimeout(this._deferredRings[i].tid);
        var gid = this._deferredRings[i].gid;
        try { this.sonic.send('/g_freeAll', gid); } catch(e) {}
        try { this.sonic.send('/n_free', gid); } catch(e) {}
      }
      this._deferredRings = [];
    }

    async setupTracks(meta, scoreGroupId) {
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
    }

    async setupControlEnvelopes(controlData, scoreGroupId) {
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
          targetIds: desc.targetIds || [],
          start: desc.start,
          dur: desc.dur,
          bufnum: bufnum,
          startFrame: desc.blockIndex * blockSize,
          numFrames: blockSize,
          controlGroupId: ctrlGid
        });
      }
    }

    _scheduleControlSynths(token) {
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
    }

    _getControlMappingsForEvent(evId) {
      if (!this._controlBusMap || this._controlBusMap.length === 0) return null;
      var mappings = null;
      for (var i = 0; i < this._controlBusMap.length; i++) {
        var cm = this._controlBusMap[i];
        if (!cm.targetIds) continue;
        for (var j = 0; j < cm.targetIds.length; j++) {
          if (cm.targetIds[j] === evId) {
            if (!mappings) mappings = [];
            mappings.push({ param: cm.param, bus: cm.bus });
            break;
          }
        }
      }
      return mappings;
    }

    _bundleNew(ev, ntp) {
      if (ev.defName === "__rest__") return;
      var defName = this._resolveDefName(ev.defName);
      var nodeId = this.sonic.nextNodeId();

      var target;
      var pf = this._resolveDefPfields(defName, ev.pfields || {});

      if (this._trackMap) {
        var group = ev.group || "default";
        var trackInfo = this._trackMap[group] || this._trackMap["default"] || this._trackMap["main"];
        target = trackInfo ? trackInfo.srcGroup : (this._scoreGroupId || this._groupId || 0);
        if (trackInfo) {
          pf.out = trackInfo.srcBus;
        }
      } else {
        target = this._groupId != null ? this._groupId : 0;
      }

      var args = [defName, nodeId, 0, target];
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        var v = pf[key];
        if (v === undefined || v === null || typeof v === 'object') continue;
        args.push(key, v);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/s_new', args);
      this.sonic.sendOSC(bundle);
      this.nodeMap.set(ev.id, nodeId);
      this._defNames.set(ev.id, defName);

      var mappings = this._getControlMappingsForEvent(ev.id);
      if (mappings) {
        for (var mi = 0; mi < mappings.length; mi++) {
          var mapArgs = [nodeId, mappings[mi].param, mappings[mi].bus];
          var mapBundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_map', mapArgs);
          this.sonic.sendOSC(mapBundle);
        }
      }
    }

    _bundleSet(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var args = [intId];
      var defName = this._defNames.get(ev.id);
      var pf = this._resolveDefPfields(defName, ev.pfields || {});
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        var v = pf[key];
        if (v === undefined || v === null || typeof v === 'object') continue;
        args.push(key, v);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this.sonic.sendOSC(bundle);
    }

    _getByPath(obj, path) {
      if (!obj || !path) return undefined;
      var parts = path.split('.');
      var cur = obj;
      for (var i = 0; i < parts.length; i++) {
        var key = parts[i];
        if (cur == null || typeof cur !== 'object' || !(key in cur)) return undefined;
        cur = cur[key];
      }
      return cur;
    }

    _resolveDefPfields(defName, pfields) {
      var out = {};
      for (var key in pfields) {
        if (!pfields.hasOwnProperty(key)) continue;
        var val = pfields[key];
        if (val === null || val === undefined) continue;
        if (typeof val === 'object') continue;
        out[key] = val;
      }
      var meta = (this.manifest.synths || {})[defName] || {};
      var paths = meta.paths || {};
      for (var srcPath in paths) {
        if (!paths.hasOwnProperty(srcPath)) continue;
        var dstKey = paths[srcPath];
        var mapped = this._getByPath(pfields, srcPath);
        if (mapped === undefined || mapped === null) continue;
        if (typeof mapped === 'object') continue;
        out[dstKey] = mapped;
      }
      return out;
    }

    _resolveDefName(name) {
      if (name === "__rest__") return "__rest__";
      if (!name || name === "sonic-pi-beep") return "kl_tri";
      return name;
    }

    _bundleRelease(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var defName = this._defNames.get(ev.id);
      var meta = (this.manifest.synths || {})[defName];
      if (meta && meta.releaseMode === "free") return;
      var gateParam = (meta && meta.gateParam) || 'gate';
      var args = [intId, gateParam, 0];
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this.sonic.sendOSC(bundle);
    }

    _computePieceDur(evts) {
      var dur = 0;
      for (var i = 0; i < evts.length; i++) {
        var ev = evts[i];
        var evEnd = ev.start;
        if (ev.type === "new") {
          var pf = ev.pfields || {};
          if (pf.dur != null) evEnd += pf.dur;
        }
        if (ev.type === "release") {
          evEnd = ev.start;
        }
        if (evEnd > dur) dur = evEnd;
      }
      return dur;
    }

    _scheduleBatch(evts, startIdx, pieceDur, token, relOffset, suppressFinish, idPrefix) {
      if (token !== this.stopToken) return;

      var now = getNTP();
      var idx = startIdx;
      var batchStart = -1;
      var batchEnd = 0;
      var count = 0;
      var self = this;

      relOffset = relOffset || 0;
      suppressFinish = !!suppressFinish;

      while (idx < evts.length && count < MAX_EVENTS_PER_BATCH) {
        var ev = evts[idx];
        var evSched = ev;
        if (idPrefix != null) {
          evSched = {};
          for (var kCopy in ev) evSched[kCopy] = ev[kCopy];
          evSched.id = String(idPrefix) + ":" + ev.id;
        }
        if (batchStart < 0) batchStart = ev.start;
        batchEnd = ev.start;

        var ntp = this._playStartNTP + relOffset + ev.start;

        if (evSched.type === "new") {
          this._bundleNew(evSched, ntp);
        } else if (evSched.type === "set") {
          this._bundleSet(evSched, ntp);
        } else if (evSched.type === "release") {
          this._bundleRelease(evSched, ntp);
        }

        if (ev.type === "new" && ev._stepIndex != null && this.onEvent) {
          (function(ds, cb, si, ms) {
            ds.schedule(function() { cb(si); }, ms);
          })(self.drawScheduler, self.onEvent, ev._stepIndex,
             self._playStartPerfMs + (relOffset + ev.start) * 1000);
        }

        idx++;
        count++;
      }

      if (idx < evts.length) {
        var batchDuration = batchEnd - batchStart;
        var overlapTime = batchDuration * BATCH_OVERLAP_RATIO;
        var nextBatchNTP = this._playStartNTP + relOffset + batchStart + overlapTime;
        var delay = (nextBatchNTP - now) * 1000;
        this._batchTimeoutId = setTimeout(function() {
          self._scheduleBatch(evts, idx, pieceDur, token, relOffset, suppressFinish, idPrefix);
        }, Math.max(1, delay));
      } else {
        if (!suppressFinish) {
          var freeGid = this._scoreGroupId || this._groupId;
          var endNTP = this._playStartNTP + relOffset + pieceDur;
          var remaining = (endNTP - now) * 1000;
          this._finishTimeoutId = setTimeout(function() {
            if (token !== self.stopToken) return;
            self.isPlaying = false;
            if (self.onFinish) self.onFinish();
            if (freeGid != null) {
              self._freeGroupDeferred(freeGid);
              self._scoreGroupId = null;
              self._groupId = null;
            }
          }, Math.max(1, remaining));
        }
      }
    }

    async play(events, options) {
      options = options || {};
      this.stopToken++;
      var token = this.stopToken;

      this.isPlaying = false;
      clearInterval(this._loopTickId);
      this._loopTickId = null;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;

      var prevGid = this._scoreGroupId || this._groupId;
      if (options._skipStop && prevGid != null) {
        this._freeGroupDeferred(prevGid);
        this._scoreGroupId = null;
        this._groupId = null;
      } else if (prevGid != null) {
        this._freeGroup();
      }

      this.nodeMap.clear();
      this._defNames.clear();
      this.drawScheduler.clear();
      this._trackMap = null;
      this._controlBusMap = [];
      this._nextAudioBus = FIRST_PRIVATE_BUS;
      this._nextControlBus = 0;

      if (token !== this.stopToken) return;

      var evts = events || [];
      this.onEvent = options.onEvent || null;
      this.onFinish = options.onFinish || null;

      if (evts.length === 0) {
        if (this.onFinish) this.onFinish();
        return;
      }

      var now = getNTP();
      var nowPerf = performance.now();
      if (!options._skipStop) {
        this._playStartNTP = now + STARTUP_DELAY;
        this._playStartPerfMs = nowPerf + STARTUP_DELAY * 1000;
      } else {
        this._playStartNTP = now;
        this._playStartPerfMs = nowPerf;
      }

      var scoreMeta = options.meta || null;
      var scoreControlData = options.controlData || null;

      if (scoreMeta && (scoreMeta.groups || scoreMeta.inserts)) {
        this._createScoreGroup();
        await this.setupTracks(scoreMeta, this._scoreGroupId);
        if (scoreControlData && scoreControlData.bufferB64) {
          await this.setupControlEnvelopes(scoreControlData, this._scoreGroupId);
        }
      } else {
        this._createGroup();
      }

      this.isPlaying = true;

      this._scheduleControlSynths(token);

      var pieceDur = this._computePieceDur(evts) + Math.max(0, options.tailPause || 0);
      var loopFinite = (typeof options.loop === "number" && Number.isFinite(options.loop) && options.loop > 1)
        ? Math.floor(options.loop)
        : 0;
      if (options.loop || loopFinite > 0) {
        this.playLoop(evts, {
          onEvent: this.onEvent,
          onFinish: this.onFinish,
          tailPause: options.tailPause != null ? options.tailPause : 0,
          finiteCycles: options.finiteCycles != null ? options.finiteCycles : (loopFinite > 0 ? loopFinite : null),
          lookaheadSec: options.lookaheadSec,
          tickMs: options.tickMs,
        });
        return;
      }

      this._scheduleBatch(evts, 0, pieceDur, token, 0, false, null);
    }

    playLoop(events, options) {
      options = options || {};
      this.stopToken++;
      var token = this.stopToken;

      this.isPlaying = false;
      clearInterval(this._loopTickId);
      this._loopTickId = null;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;

      if (token !== this.stopToken) return;

      var evts = events || [];
      this.onEvent = options.onEvent || null;
      this.onFinish = options.onFinish || null;
      if (evts.length === 0) {
        if (this.onFinish) this.onFinish();
        return;
      }

      var basePieceDur = this._computePieceDur(evts);
      var tailPause = Math.max(0, options.tailPause || 0);
      var cycleDur = basePieceDur + tailPause;
      if (cycleDur <= 0) cycleDur = basePieceDur > 0 ? basePieceDur : 0.001;

      var lookaheadSec = options.lookaheadSec != null ? Math.max(0.1, options.lookaheadSec) : Math.max(0.8, Math.min(2.0, cycleDur));
      var tickMs = options.tickMs != null ? Math.max(10, options.tickMs) : 40;
      var finiteCycles = (typeof options.finiteCycles === "number" && Number.isFinite(options.finiteCycles) && options.finiteCycles > 0)
        ? Math.floor(options.finiteCycles)
        : 0;

      this.isPlaying = true;

      if (finiteCycles > 0) {
        var freeGid = this._scoreGroupId || this._groupId;
        var endNTP = this._playStartNTP + (cycleDur * finiteCycles);
        var selfFinish = this;
        var finishToken = token;
        var finishRemaining = (endNTP - getNTP()) * 1000;
        this._finishTimeoutId = setTimeout(function() {
          if (finishToken !== selfFinish.stopToken) return;
          selfFinish.stopToken++;
          selfFinish.isPlaying = false;
          clearInterval(selfFinish._loopTickId);
          selfFinish._loopTickId = null;
          clearTimeout(selfFinish._batchTimeoutId);
          selfFinish._batchTimeoutId = null;
          if (selfFinish.onFinish) selfFinish.onFinish();
          if (freeGid != null) {
            selfFinish._freeGroupDeferred(freeGid);
            selfFinish._scoreGroupId = null;
            selfFinish._groupId = null;
          }
        }, Math.max(1, finishRemaining));
      }

      var self = this;
      var nextCycleIndex = 0;

      function enqueueReadyCycles() {
        if (token !== self.stopToken || !self.isPlaying) return;
        var nowRel = getNTP() - self._playStartNTP;
        var horizonRel = nowRel + lookaheadSec;
        while ((nextCycleIndex * cycleDur) <= horizonRel) {
          if (finiteCycles > 0 && nextCycleIndex >= finiteCycles) break;
          var relOffset = nextCycleIndex * cycleDur;
          self._scheduleBatch(
            evts,
            0,
            basePieceDur,
            token,
            relOffset,
            true,
            "loop" + nextCycleIndex
          );
          nextCycleIndex += 1;
        }
      }

      enqueueReadyCycles();
      this._loopTickId = setInterval(enqueueReadyCycles, tickMs);
    }

    async stop() {
      this.stopToken++;
      this.isPlaying = false;
      clearInterval(this._loopTickId);
      this._loopTickId = null;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;
      this._cancelAllDeferredRings();
      this._freeGroup();
      this.nodeMap.clear();
      this._defNames.clear();
      this._trackMap = null;
      this._controlBusMap = [];
      this.drawScheduler.clear();
    }
  };
})();
