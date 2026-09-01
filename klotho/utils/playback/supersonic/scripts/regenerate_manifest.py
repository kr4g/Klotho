"""Regenerate ``manifest.json``, ``kinds.json`` and ``io.json`` from compiled ``.scsyndef`` blobs.

Walks ``klotho/utils/playback/supersonic/assets/synthdefs/**/*.scsyndef``
(recursively), parses each via the vendored ``synthdef_parser``, and writes:

- ``manifest.json`` — flat ``{synth_name: {control_name: default_value}}``
  (shape frozen: the widget consumes it as ``__klothoManifest``).
- ``kinds.json`` — sidecar ``{synth_name: "inst" | "fx" | "infra"}`` derived
  from the containing subfolder (``instruments/`` → inst, ``effects/`` → fx,
  ``infra/`` → infra; anything else defaults to inst).
- ``io.json`` — sidecar recording each def's *bus* I/O widths, so a caller
  can tell a 2-channel insert from a 24-channel one without booting an
  audio engine.  ``manifest.json`` records neither channel count nor rate,
  and its shape is frozen, so the widths go in a sidecar rather than into
  it (same reasoning that produced ``kinds.json``).

Defaults are rounded with ``float(f"{v:.7g}")`` to undo float32 round-off
(``0.07999999... -> 0.08``). Top-level keys of all three files are sorted
the same way: ``__*`` infra synths first, then ``kl_*``, then ``fd_*``,
then anything else.

``io.json``
----------

One record per synth, keys in a fixed order::

    "kl_saw":      {"ins": 0, "outs": 2,
                    "reads": [],
                    "writes": [{"ugen": "Out", "rate": "audio", "channels": 2}]}

    "kl_reverb":   {"ins": 2, "outs": 2,
                    "reads":  [{"ugen": "In", "rate": "audio", "channels": 2}],
                    "writes": [{"ugen": "ReplaceOut", "rate": "audio", "channels": 2}]}

    "__busRouter": {"ins": 2, "outs": 2,
                    "reads":  [{"ugen": "In", "rate": "audio", "channels": 2}],
                    "writes": [{"ugen": "ReplaceOut", "rate": "audio", "channels": 2},
                               {"ugen": "Out", "rate": "audio", "channels": 2}]}

The two derivations, both read straight off the parsed UGen graph:

- a writer's channel count is ``len(ugen["inputs"]) - 1`` — the first input
  is the bus, every remaining input is one channel;
- a reader's channel count is ``len(ugen["outputs"])`` — one output per
  channel read.

Design decisions, each of which had a plausible alternative:

*Several writers, or none.*  ``outs`` is the **widest single write**, not
their sum: it answers "how many consecutive bus channels does this def
occupy", which is the question lane/width validation asks.  Six bundled
defs write twice.  Three (``fd_glass``, ``fd_longsaw``, ``fd_quin``) are
sclang multichannel-expanding one ``Out.ar`` into two 2-channel writes to
the *same* bus, which sum; three (``__busRouter``, ``__busRouterMonitor``,
``__chainLimiter``) write 2 channels to two *different* buses.  Both are
2 channels wide, and the per-writer ``writes`` list keeps the difference
legible instead of flattening it away.  A def with no bus writer at all
records ``"outs": 0`` with ``"writes": []`` — it writes nothing, which is
a fact, not an absence of information.

*``Out`` vs ``ReplaceOut``.*  Recorded, per writer, because the difference
is real for chain wiring: an insert ends ``ReplaceOut(outBus)`` (it owns
its output bus), while ``__busRouter`` ends ``ReplaceOut(inBus)`` **plus**
``Out(outBus)`` — the ``ReplaceOut`` there clears the source bus rather
than producing the output.  A validator distinguishes the two by the
writer set: ``["ReplaceOut"]`` is a processor, ``["ReplaceOut", "Out"]``
is a router.  The bus *control name* behind each writer is deliberately
**not** recorded: the vendored parser drops the named-parameter index, so
recovering "which control is this bus" would mean assuming the named
parameters appear in declaration order — and ``inBus``/``outBus`` share
the default ``0.0``, so a wrong assumption there is undetectable.  That is
a guess, so it is refused rather than made (Ruling Nine).

*Rate.*  Recorded per reader/writer, not once per def, because a def may
legitimately write at both rates.  It is what separates ``__klEnvCtrl``
(``Out.kr``, 1 control channel, the only non-audio writer in the tree)
from every audio def; an audio chain must not accept a control-rate def.

*Unknown widths.*  Every ``manifest.json`` key gets an ``io.json`` record,
always — a missing key means the sidecar is stale and a validator must
refuse, so it must never be how a widthless def is spelled.  Three states
are kept distinct: ``0`` (reads/writes no bus — determinate), ``null``
(a reader/writer exists but its width could not be derived — refuse, do
not fall back to 2), and *key absent* (stale sidecar).  ``null`` arises
when a writer carries a packed input, for which ``len(inputs) - 1`` is not
the channel count; no bundled def does today, and ``main`` shouts if one
ever appears.

Usage::

    python -m klotho.utils.playback.supersonic.scripts.regenerate_manifest
    python -m klotho.utils.playback.supersonic.scripts.regenerate_manifest --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from klotho.utils.playback.supersonic.registry import _FOLDER_TO_KIND, _round_default
from klotho.utils.playback.supersonic._vendor.synthdef_parser import (
    parse_synthdef_file,
)

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_SYNTHDEFS_DIR = _ASSETS_DIR / "synthdefs"
_MANIFEST_PATH = _ASSETS_DIR / "manifest.json"
_KINDS_PATH = _ASSETS_DIR / "kinds.json"
_IO_PATH = _ASSETS_DIR / "io.json"

#: UGens that write a signal to a bus. First input is the bus; the rest are
#: one input per channel.
_WRITER_UGENS = ("Out", "OffsetOut", "ReplaceOut", "XOut")

#: UGens that read a signal from a bus. One output per channel.
_READER_UGENS = ("In", "InFeedback")


def _def_sort_key(def_name: str) -> tuple:
    if def_name.startswith("__"):
        return (0, def_name)
    if def_name.startswith("kl_"):
        return (1, def_name)
    if def_name.startswith("fd_"):
        return (2, def_name)
    if def_name.startswith(("edm_", "lofi_", "chip_")):
        return (3, def_name)
    return (4, def_name)


def _iter_scsyndef(synthdefs_dir: Path) -> Iterable[Path]:
    return sorted(synthdefs_dir.rglob("*.scsyndef"))


def _kind_for_path(path: Path) -> str:
    return _FOLDER_TO_KIND.get(path.parent.name, "inst")


def _writer_channels(ugen: dict) -> int | None:
    """Channels written by a bus-writer *ugen*, or ``None`` if underivable.

    ``len(inputs) - 1`` (bus, then one input per channel) — but a packed
    input stands for an unknown number of inputs, so the arithmetic does
    not hold and the width is refused rather than guessed.
    """
    if any("packed" in inp for inp in ugen["inputs"]):
        return None
    return len(ugen["inputs"]) - 1


def _io_for_synth(synth: dict) -> dict:
    """Return the ``io.json`` record for one parsed synth.

    ``reads``/``writes`` are in UGen-graph order (stable for given bytes,
    and it is also execution order, which is what makes ``__busRouter``'s
    clear-then-emit pair readable).
    """
    reads = [
        {"ugen": u["name"], "rate": u["calculation_rate"],
         "channels": len(u["outputs"])}
        for u in synth["ugens"] if u["name"] in _READER_UGENS
    ]
    writes = [
        {"ugen": u["name"], "rate": u["calculation_rate"],
         "channels": _writer_channels(u)}
        for u in synth["ugens"] if u["name"] in _WRITER_UGENS
    ]
    return {
        "ins": _aggregate_width(reads),
        "outs": _aggregate_width(writes),
        "reads": reads,
        "writes": writes,
    }


def _aggregate_width(entries: list[dict]) -> int | None:
    """Widest single entry: ``0`` for none, ``None`` if any is underivable.

    One underivable width poisons the aggregate — reporting the max of the
    rest would understate the def and read as a determinate answer.
    """
    if any(e["channels"] is None for e in entries):
        return None
    return max((e["channels"] for e in entries), default=0)


def build_manifest(synthdefs_dir: Path = _SYNTHDEFS_DIR) -> tuple[dict, dict, dict]:
    """Return ``(manifest, kinds, io)`` parsed from *synthdefs_dir*."""
    manifest: dict[str, dict[str, float]] = {}
    kinds: dict[str, str] = {}
    io: dict[str, dict] = {}
    for path in _iter_scsyndef(synthdefs_dir):
        kind = _kind_for_path(path)
        parsed = parse_synthdef_file(str(path))
        for synth_name, synth in parsed["synths"].items():
            manifest[synth_name] = {
                k: _round_default(v) for k, v in synth["named_parameters"].items()
            }
            kinds[synth_name] = kind
            io[synth_name] = _io_for_synth(synth)
    manifest = dict(sorted(manifest.items(), key=lambda kv: _def_sort_key(kv[0])))
    kinds = dict(sorted(kinds.items(), key=lambda kv: _def_sort_key(kv[0])))
    io = dict(sorted(io.items(), key=lambda kv: _def_sort_key(kv[0])))
    return manifest, kinds, io


def _diff_legacy_release_mode(new_manifest: dict, manifest_path: Path) -> list[str]:
    """Sanity check: any synth where derived ``'gate' in controls`` would
    disagree with the existing ``releaseMode`` field. Returns a list of
    human-readable mismatch messages (empty list = all consistent)."""
    if not manifest_path.exists():
        return []
    try:
        legacy = json.loads(manifest_path.read_text())
    except Exception:
        return []
    if not isinstance(legacy, dict):
        return []
    legacy_synths = {}
    if "synths" in legacy and isinstance(legacy["synths"], dict):
        legacy_synths.update(legacy["synths"])
    if "inserts" in legacy and isinstance(legacy["inserts"], dict):
        legacy_synths.update(legacy["inserts"])

    mismatches: list[str] = []
    for name, controls in new_manifest.items():
        old = legacy_synths.get(name)
        if not isinstance(old, dict):
            continue
        old_mode = (old.get("releaseMode") or "").lower()
        if old_mode not in ("gate", "free"):
            continue
        derived_has_gate = "gate" in controls
        old_has_gate = (old_mode == "gate")
        if derived_has_gate != old_has_gate:
            mismatches.append(
                f"  {name}: legacy releaseMode={old_mode!r} but derived 'gate in controls'={derived_has_gate}"
            )
    return mismatches


def _io_review_notes(io: dict) -> tuple[list[str], list[str]]:
    """Return ``(refusals, notes)`` for a human read of the derived widths.

    Refusals are defs whose width could not be derived — those reach
    ``io.json`` as ``null`` and any validator must decline them.  Notes are
    the shapes that are derivable but unusual enough to be worth an eye:
    more than one writer, and any non-audio writer.
    """
    refusals: list[str] = []
    notes: list[str] = []
    for name, rec in io.items():
        if rec["ins"] is None or rec["outs"] is None:
            refusals.append(
                f"  {name}: width underivable (packed inputs?) -> recorded as null"
            )
        if len(rec["writes"]) > 1:
            shape = ", ".join(
                f"{w['ugen']}.{w['rate'][0]}r x{w['channels']}" for w in rec["writes"]
            )
            notes.append(f"  {name}: {len(rec['writes'])} writers ({shape})")
        for w in rec["writes"]:
            if w["rate"] != "audio":
                notes.append(f"  {name}: {w['rate']}-rate writer {w['ugen']}")
    return refusals, notes


def _io_shape_counts(io: dict) -> dict:
    """``{(ins, outs): count}`` over *io*, for the regeneration summary."""
    counts: dict = {}
    for rec in io.values():
        key = (rec["ins"], rec["outs"])
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0]))))


def write_manifest(manifest: dict, manifest_path: Path = _MANIFEST_PATH) -> None:
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def write_kinds(kinds: dict, kinds_path: Path = _KINDS_PATH) -> None:
    kinds_path.write_text(json.dumps(kinds, indent=2) + "\n")


def write_io(io: dict, io_path: Path = _IO_PATH) -> None:
    io_path.write_text(json.dumps(io, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed manifest to stdout and report releaseMode disagreements; do not write.",
    )
    parser.add_argument(
        "--synthdefs-dir",
        type=Path,
        default=_SYNTHDEFS_DIR,
        help="Directory containing .scsyndef files (default: %(default)s).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_MANIFEST_PATH,
        help="Output manifest.json path (default: %(default)s).",
    )
    args = parser.parse_args(argv)

    files = list(_iter_scsyndef(args.synthdefs_dir))
    manifest, kinds, io = build_manifest(args.synthdefs_dir)

    kind_counts = {}
    for k in kinds.values():
        kind_counts[k] = kind_counts.get(k, 0) + 1
    print(
        f"Parsed {len(files)} .scsyndef files; {len(manifest)} synth entries "
        f"({kind_counts}).",
        file=sys.stderr,
    )

    mismatches = _diff_legacy_release_mode(manifest, args.out)
    if mismatches:
        print(
            "WARNING: releaseMode disagreements between legacy manifest and derived 'gate in controls':",
            file=sys.stderr,
        )
        for line in mismatches:
            print(line, file=sys.stderr)
    else:
        print(
            "OK: derived 'gate in controls' agrees with every legacy releaseMode entry.",
            file=sys.stderr,
        )

    shapes = ", ".join(
        f"{ins}-in/{outs}-out x{n}" for (ins, outs), n in _io_shape_counts(io).items()
    )
    print(f"Bus I/O shapes: {shapes}.", file=sys.stderr)
    refusals, notes = _io_review_notes(io)
    if refusals:
        print(
            "WARNING: widths could not be derived for these defs; they are "
            "recorded as null and every validator must refuse them:",
            file=sys.stderr,
        )
        for line in refusals:
            print(line, file=sys.stderr)
    for line in notes:
        print(f"note:{line}", file=sys.stderr)

    if args.dry_run:
        json.dump(manifest, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    write_manifest(manifest, args.out)
    print(f"Wrote {args.out}", file=sys.stderr)
    kinds_path = args.out.parent / "kinds.json"
    write_kinds(kinds, kinds_path)
    print(f"Wrote {kinds_path}", file=sys.stderr)
    io_path = args.out.parent / "io.json"
    write_io(io, io_path)
    print(f"Wrote {io_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
