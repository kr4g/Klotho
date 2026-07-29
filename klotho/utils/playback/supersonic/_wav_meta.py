"""Minimal RIFF/WAVE header parser (stdlib-only).

The browser engine decodes sample audio itself (SuperSonic's
``loadSample``); Python only needs header metadata — most importantly the
channel count, which decides between the mono and stereo sampler
SynthDefs at instrument-construction time. A hand-rolled chunk walk
covers what :mod:`wave` cannot: float32 WAVs and WAVE_FORMAT_EXTENSIBLE
files, both common exports from DAWs and phone recorders.
"""

import struct

_FMT_PCM = 0x0001
_FMT_FLOAT = 0x0003
_FMT_EXTENSIBLE = 0xFFFE

_FORMAT_NAMES = {
    0x0002: "ADPCM",
    0x0006: "A-law",
    0x0007: "mu-law",
    0x0011: "IMA ADPCM",
    0x0055: "MP3",
}


def _reject_non_wav(data):
    """Raise a friendly ValueError for recognizable non-WAV audio files."""
    if len(data) >= 12 and data[:4] == b"FORM" and data[8:12] in (b"AIFF", b"AIFC"):
        raise ValueError(
            "This is an AIFF file, not a WAV. Convert it to WAV "
            "(e.g. with Audacity, ffmpeg, or your DAW's export) and try again."
        )
    if len(data) >= 4 and data[:4] == b"fLaC":
        raise ValueError("This is a FLAC file, not a WAV. Convert it to WAV first.")
    if len(data) >= 4 and data[:4] == b"OggS":
        raise ValueError("This is an Ogg file, not a WAV. Convert it to WAV first.")
    if len(data) >= 3 and (data[:3] == b"ID3"
                           or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)):
        raise ValueError("This looks like an MP3 file, not a WAV. Convert it to WAV first.")
    raise ValueError(
        "Not a WAV file (missing RIFF/WAVE header). "
        "Samples must be .wav files."
    )


def wav_metadata(data):
    """Parse a WAV file's header.

    Parameters
    ----------
    data : bytes
        The complete file contents (only the header chunks are read).

    Returns
    -------
    dict
        ``{"channels", "sampleRate", "frames", "duration",
        "bitsPerSample", "formatTag"}`` — key names match the bundled
        ``samples.json`` manifest entries where they overlap.

    Raises
    ------
    ValueError
        For non-WAV data (with format-specific hints for AIFF/FLAC/
        Ogg/MP3) or compressed WAV encodings the engine cannot load.
    """
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        _reject_non_wav(data)

    fmt = None
    data_size = None
    pos = 12
    n = len(data)
    while pos + 8 <= n:
        chunk_id = data[pos:pos + 4]
        (chunk_size,) = struct.unpack_from("<I", data, pos + 4)
        body = pos + 8
        if chunk_id == b"fmt " and chunk_size >= 16:
            fmt_tag, channels, sample_rate, _byte_rate, block_align, bits = (
                struct.unpack_from("<HHIIHH", data, body))
            if fmt_tag == _FMT_EXTENSIBLE and chunk_size >= 40:
                # The real format is the first 2 bytes of the SubFormat
                # GUID (after cbSize + validBits + channelMask).
                (fmt_tag,) = struct.unpack_from("<H", data, body + 24)
            fmt = {
                "formatTag": fmt_tag,
                "channels": channels,
                "sampleRate": sample_rate,
                "blockAlign": block_align,
                "bitsPerSample": bits,
            }
        elif chunk_id == b"data":
            data_size = min(chunk_size, n - body)
        # Chunks are word-aligned: odd sizes carry a pad byte.
        pos = body + chunk_size + (chunk_size & 1)

    if fmt is None:
        raise ValueError("Malformed WAV file: no fmt chunk found.")
    if data_size is None:
        raise ValueError("Malformed WAV file: no data chunk found.")
    if fmt["formatTag"] not in (_FMT_PCM, _FMT_FLOAT):
        name = _FORMAT_NAMES.get(fmt["formatTag"],
                                 f"format 0x{fmt['formatTag']:04X}")
        raise ValueError(
            f"Unsupported WAV encoding ({name}). Use uncompressed PCM "
            "or float WAV files."
        )
    if fmt["channels"] < 1:
        raise ValueError("Malformed WAV file: zero channels.")

    block_align = fmt["blockAlign"]
    if not block_align:
        block_align = fmt["channels"] * max(1, fmt["bitsPerSample"] // 8)
    frames = data_size // block_align if block_align else 0
    sample_rate = fmt["sampleRate"] or 1
    return {
        "channels": fmt["channels"],
        "sampleRate": fmt["sampleRate"],
        "frames": frames,
        "duration": frames / sample_rate,
        "bitsPerSample": fmt["bitsPerSample"],
        "formatTag": fmt["formatTag"],
    }
