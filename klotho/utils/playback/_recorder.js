(() => {
  // Version-skew guard, same pattern as the playback bridge: install keys
  // on the versioned name; the public name is overwritten unconditionally
  // so widgets rendered after stale saved outputs get this build.
  if (typeof globalThis.__klothoRecorderV1 !== "undefined") return;

  // ---------------------------------------------------------------------
  // Capture worklet. Runs in the AudioWorkletGlobalScope: accumulates the
  // engine node's raw float32 blocks per channel while recording. The node
  // declares one (never-written, i.e. silent) output that the caller wires
  // to the destination — a worklet node unreachable from the destination
  // is never pulled by the graph, so a pure sink would record nothing.
  // ---------------------------------------------------------------------
  var CAPTURE_WORKLET_SOURCE = [
    'class KlothoCaptureProcessor extends AudioWorkletProcessor {',
    '  constructor() {',
    '    super();',
    '    this._recording = false;',
    '    this._channels = 0;',
    '    this._chunks = [];',
    '    this._frames = 0;',
    '    this._maxFrames = Infinity;',
    '    this._limitHit = false;',
    '    this.port.onmessage = (e) => {',
    '      var msg = e.data || {};',
    '      if (msg.cmd === "start") {',
    '        this._channels = msg.channels | 0;',
    '        this._chunks = [];',
    '        for (var c = 0; c < this._channels; c++) this._chunks.push([]);',
    '        this._frames = 0;',
    '        this._maxFrames = (msg.maxFrames > 0) ? msg.maxFrames : Infinity;',
    '        this._limitHit = false;',
    '        this._recording = true;',
    '        this.port.postMessage({ type: "started", contextFrame: currentFrame });',
    '      } else if (msg.cmd === "stop") {',
    '        this._recording = false;',
    '        var buffers = [];',
    '        var transfer = [];',
    '        for (var c = 0; c < this._channels; c++) {',
    '          var total = new Float32Array(this._frames);',
    '          var off = 0;',
    '          var list = this._chunks[c];',
    '          for (var i = 0; i < list.length; i++) { total.set(list[i], off); off += list[i].length; }',
    '          buffers.push(total.buffer);',
    '          transfer.push(total.buffer);',
    '        }',
    '        this._chunks = [];',
    '        this.port.postMessage({ type: "data", frames: this._frames, channels: this._channels,',
    '                                limitHit: this._limitHit, buffers: buffers }, transfer);',
    '        this._frames = 0;',
    '      }',
    '    };',
    '  }',
    '  process(inputs) {',
    '    if (!this._recording) return true;',
    '    var input = inputs[0] || [];',
    '    var blockLen = (input[0] && input[0].length) || 128;',
    '    if (this._frames + blockLen > this._maxFrames) {',
    '      if (!this._limitHit) {',
    '        this._limitHit = true;',
    '        this._recording = false;',
    '        this.port.postMessage({ type: "limit", frames: this._frames });',
    '      }',
    '      return true;',
    '    }',
    '    for (var c = 0; c < this._channels; c++) {',
    '      var src = input[c];',
    '      this._chunks[c].push(src ? src.slice(0) : new Float32Array(blockLen));',
    '    }',
    '    this._frames += blockLen;',
    '    return true;',
    '  }',
    '}',
    'registerProcessor("klotho-capture", KlothoCaptureProcessor);',
  ].join('\n');

  var _state = {
    moduleReady: null,     // per-page: one AudioContext, one addModule
    active: false,         // one recording at a time (the engine is shared)
    lastUrls: [],          // object URLs of the previous delivery (revoked on next)
  };

  async function _ensureWorkletModule(audioContext) {
    if (_state.moduleReady) return _state.moduleReady;
    var blob = new Blob([CAPTURE_WORKLET_SOURCE], { type: "application/javascript" });
    var url = URL.createObjectURL(blob);
    _state.moduleReady = audioContext.audioWorklet.addModule(url).then(function() {
      URL.revokeObjectURL(url);
      return true;
    }, function(err) {
      URL.revokeObjectURL(url);
      _state.moduleReady = null;
      throw err;
    });
    return _state.moduleReady;
  }

  // Start capturing `channels` channels from the engine's worklet node.
  // Returns a session: { startedPerfMs, sampleRate, stop() -> Promise<
  //   {channels: Float32Array[], frames, sampleRate, limitHit}>, abort() }.
  async function start(sonic, channels, maxSeconds) {
    if (_state.active) {
      console.warn("[Klotho] a recording is already in progress on this page");
      return null;
    }
    var ctx = sonic.audioContext;
    var engineNode = sonic.node;
    if (!ctx || !engineNode) {
      console.warn("[Klotho] recorder: engine audio node unavailable");
      return null;
    }
    await _ensureWorkletModule(ctx);

    var captureNode = new AudioWorkletNode(ctx, "klotho-capture", {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      outputChannelCount: [1],
      channelCount: channels,
      channelCountMode: "explicit",
      channelInterpretation: "discrete",
    });

    _state.active = true;
    var finished = false;
    var dataResolvers = [];
    var startedPerfMs = null;
    var startedResolve;
    var startedPromise = new Promise(function(res) { startedResolve = res; });

    captureNode.port.onmessage = function(e) {
      var msg = e.data || {};
      if (msg.type === "started") {
        startedPerfMs = performance.now();
        startedResolve();
      } else if (msg.type === "limit") {
        console.warn("[Klotho] recording length limit reached ("
          + Math.round(msg.frames / ctx.sampleRate) + "s); capture truncated");
      } else if (msg.type === "data") {
        var chans = [];
        for (var i = 0; i < msg.buffers.length; i++) chans.push(new Float32Array(msg.buffers[i]));
        var result = {
          channels: chans,
          frames: msg.frames,
          sampleRate: ctx.sampleRate,
          limitHit: !!msg.limitHit,
        };
        for (var r = 0; r < dataResolvers.length; r++) dataResolvers[r](result);
        dataResolvers = [];
      }
    };

    // Parallel tap: the engine node stays connected to the destination, and
    // the capture node's silent output keeps it pulled by the graph.
    engineNode.connect(captureNode);
    captureNode.connect(ctx.destination);

    var maxFrames = Math.round((maxSeconds > 0 ? maxSeconds : 600) * ctx.sampleRate);
    captureNode.port.postMessage({ cmd: "start", channels: channels, maxFrames: maxFrames });
    await startedPromise;

    function teardown() {
      try { engineNode.disconnect(captureNode); } catch (e) {}
      try { captureNode.disconnect(); } catch (e) {}
      _state.active = false;
    }

    return {
      get startedPerfMs() { return startedPerfMs; },
      sampleRate: ctx.sampleRate,
      audioContext: ctx,
      stop: function() {
        if (finished) return Promise.resolve(null);
        finished = true;
        var p = new Promise(function(res) { dataResolvers.push(res); });
        captureNode.port.postMessage({ cmd: "stop" });
        return p.then(function(result) { teardown(); return result; });
      },
      abort: function() {
        if (finished) return;
        finished = true;
        teardown();
      },
    };
  }

  // ---------------------------------------------------------------------
  // 24-bit PCM WAV encoder (little-endian, plain fmt chunk).
  // ---------------------------------------------------------------------
  function _writeStr(dv, off, s) {
    for (var i = 0; i < s.length; i++) dv.setUint8(off + i, s.charCodeAt(i));
  }

  function encodeWav24(channelData, sampleRate) {
    var nCh = channelData.length;
    var frames = nCh > 0 ? channelData[0].length : 0;
    var blockAlign = nCh * 3;
    var dataSize = frames * blockAlign;
    var buf = new ArrayBuffer(44 + dataSize);
    var dv = new DataView(buf);
    _writeStr(dv, 0, "RIFF");
    dv.setUint32(4, 36 + dataSize, true);
    _writeStr(dv, 8, "WAVE");
    _writeStr(dv, 12, "fmt ");
    dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true);                       // PCM
    dv.setUint16(22, nCh, true);
    dv.setUint32(24, sampleRate, true);
    dv.setUint32(28, sampleRate * blockAlign, true); // byte rate
    dv.setUint16(32, blockAlign, true);
    dv.setUint16(34, 24, true);
    _writeStr(dv, 36, "data");
    dv.setUint32(40, dataSize, true);
    var bytes = new Uint8Array(buf);
    var off = 44;
    for (var i = 0; i < frames; i++) {
      for (var c = 0; c < nCh; c++) {
        var s = channelData[c][i];
        if (s > 1) s = 1; else if (s < -1) s = -1;
        var v = Math.round(s * 8388607) | 0;
        bytes[off] = v & 0xFF;
        bytes[off + 1] = (v >> 8) & 0xFF;
        bytes[off + 2] = (v >> 16) & 0xFF;
        off += 3;
      }
    }
    return bytes;
  }

  // ---------------------------------------------------------------------
  // STORE-only ZIP writer (wav data doesn't compress; a container is all
  // we need to hand a "folder" of stems to the browser as one download).
  // ---------------------------------------------------------------------
  var _crcTable = null;
  function _crc32(bytes) {
    if (!_crcTable) {
      _crcTable = new Int32Array(256);
      for (var n = 0; n < 256; n++) {
        var c = n;
        for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
        _crcTable[n] = c;
      }
    }
    var crc = -1;
    for (var i = 0; i < bytes.length; i++) {
      crc = (crc >>> 8) ^ _crcTable[(crc ^ bytes[i]) & 0xFF];
    }
    return (crc ^ -1) >>> 0;
  }

  function _dosDateTime(d) {
    var time = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
    var date = (((d.getFullYear() - 1980) & 0x7F) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    return { time: time, date: date };
  }

  // entries: [{name: "main.wav", data: Uint8Array}] -> Uint8Array (zip bytes)
  function zipStore(entries) {
    var now = _dosDateTime(new Date());
    var parts = [];
    var central = [];
    var offset = 0;
    for (var i = 0; i < entries.length; i++) {
      var name = entries[i].name;
      var data = entries[i].data;
      var nameBytes = new TextEncoder().encode(name);
      var crc = _crc32(data);

      var lfh = new DataView(new ArrayBuffer(30));
      lfh.setUint32(0, 0x04034b50, true);
      lfh.setUint16(4, 20, true);            // version needed
      lfh.setUint16(6, 0, true);             // flags
      lfh.setUint16(8, 0, true);             // method: STORE
      lfh.setUint16(10, now.time, true);
      lfh.setUint16(12, now.date, true);
      lfh.setUint32(14, crc, true);
      lfh.setUint32(18, data.length, true);  // compressed
      lfh.setUint32(22, data.length, true);  // uncompressed
      lfh.setUint16(26, nameBytes.length, true);
      lfh.setUint16(28, 0, true);            // extra len
      parts.push(new Uint8Array(lfh.buffer), nameBytes, data);

      var cdh = new DataView(new ArrayBuffer(46));
      cdh.setUint32(0, 0x02014b50, true);
      cdh.setUint16(4, 20, true);            // made by
      cdh.setUint16(6, 20, true);            // needed
      cdh.setUint16(8, 0, true);
      cdh.setUint16(10, 0, true);
      cdh.setUint16(12, now.time, true);
      cdh.setUint16(14, now.date, true);
      cdh.setUint32(16, crc, true);
      cdh.setUint32(20, data.length, true);
      cdh.setUint32(24, data.length, true);
      cdh.setUint16(28, nameBytes.length, true);
      // extra/comment/disk/attrs all zero
      cdh.setUint32(42, offset, true);       // local header offset
      central.push(new Uint8Array(cdh.buffer), nameBytes);

      offset += 30 + nameBytes.length + data.length;
    }
    var centralSize = 0;
    for (var c1 = 0; c1 < central.length; c1++) centralSize += central[c1].length;
    var eocd = new DataView(new ArrayBuffer(22));
    eocd.setUint32(0, 0x06054b50, true);
    eocd.setUint16(8, entries.length, true);
    eocd.setUint16(10, entries.length, true);
    eocd.setUint32(12, centralSize, true);
    eocd.setUint32(16, offset, true);
    var totalSize = offset + centralSize + 22;
    var out = new Uint8Array(totalSize);
    var pos = 0;
    for (var p = 0; p < parts.length; p++) { out.set(parts[p], pos); pos += parts[p].length; }
    for (var c2 = 0; c2 < central.length; c2++) { out.set(central[c2], pos); pos += central[c2].length; }
    out.set(new Uint8Array(eocd.buffer), pos);
    return out;
  }

  // ---------------------------------------------------------------------
  // Delivery: attempt an automatic download AND leave a persistent link in
  // the widget bar — the programmatic click can be gesture-blocked
  // (notably in Colab's sandboxed output iframes), the link never is.
  // ---------------------------------------------------------------------
  function _fmtSize(bytes) {
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB";
    if (bytes >= 1024) return Math.round(bytes / 1024) + " KB";
    return bytes + " B";
  }

  // files: [{name, blob}]
  function deliver(files, containerEl) {
    for (var u = 0; u < _state.lastUrls.length; u++) {
      try { URL.revokeObjectURL(_state.lastUrls[u]); } catch (e) {}
    }
    _state.lastUrls = [];
    if (containerEl) containerEl.innerHTML = "";
    for (var i = 0; i < files.length; i++) {
      var url = URL.createObjectURL(files[i].blob);
      _state.lastUrls.push(url);
      var a = document.createElement("a");
      a.href = url;
      a.download = files[i].name;
      a.textContent = "⬇ " + files[i].name + " (" + _fmtSize(files[i].blob.size) + ")";
      a.style.cssText = "color:#4ade80;font-size:11px;text-decoration:none;"
        + "margin-left:4px;white-space:nowrap;";
      if (containerEl) {
        containerEl.appendChild(a);
        containerEl.style.display = "inline-flex";
      }
      try { a.click(); } catch (e) {}
    }
  }

  function defaultBaseName() {
    var d = new Date();
    function p2(n) { return (n < 10 ? "0" : "") + n; }
    return "klotho_" + d.getFullYear() + p2(d.getMonth() + 1) + p2(d.getDate())
      + "-" + p2(d.getHours()) + p2(d.getMinutes()) + p2(d.getSeconds());
  }

  var KlothoRecorder = {
    start: start,
    encodeWav24: encodeWav24,
    zipStore: zipStore,
    deliver: deliver,
    defaultBaseName: defaultBaseName,
    isActive: function() { return _state.active; },
  };

  globalThis.KlothoRecorder = KlothoRecorder;
  globalThis.__klothoRecorderV1 = KlothoRecorder;
})();
