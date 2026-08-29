"""Regenerate ``manifest.json`` and ``kinds.json`` from compiled ``.scsyndef`` blobs.

Walks ``klotho/utils/playback/supersonic/assets/synthdefs/**/*.scsyndef``
(recursively), parses each via the vendored ``synthdef_parser``, and writes:

- ``manifest.json`` — flat ``{synth_name: {control_name: default_value}}``
  (shape frozen: the widget consumes it as ``__klothoManifest``).
- ``kinds.json`` — sidecar ``{synth_name: "inst" | "fx" | "infra"}`` derived
  from the containing subfolder (``instruments/`` → inst, ``effects/`` → fx,
  ``infra/`` → infra; anything else defaults to inst).

Defaults are rounded with ``float(f"{v:.7g}")`` to undo float32 round-off
(``0.07999999... -> 0.08``). Top-level keys are sorted: ``__*`` infra
synths first, then ``kl_*``, then ``fd_*``, then anything else.

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


def build_manifest(synthdefs_dir: Path = _SYNTHDEFS_DIR) -> tuple[dict, dict]:
    """Return ``(manifest, kinds)`` parsed from *synthdefs_dir*."""
    manifest: dict[str, dict[str, float]] = {}
    kinds: dict[str, str] = {}
    for path in _iter_scsyndef(synthdefs_dir):
        kind = _kind_for_path(path)
        parsed = parse_synthdef_file(str(path))
        for synth_name, synth in parsed["synths"].items():
            manifest[synth_name] = {
                k: _round_default(v) for k, v in synth["named_parameters"].items()
            }
            kinds[synth_name] = kind
    manifest = dict(sorted(manifest.items(), key=lambda kv: _def_sort_key(kv[0])))
    kinds = dict(sorted(kinds.items(), key=lambda kv: _def_sort_key(kv[0])))
    return manifest, kinds


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


def write_manifest(manifest: dict, manifest_path: Path = _MANIFEST_PATH) -> None:
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def write_kinds(kinds: dict, kinds_path: Path = _KINDS_PATH) -> None:
    kinds_path.write_text(json.dumps(kinds, indent=2) + "\n")


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
    manifest, kinds = build_manifest(args.synthdefs_dir)

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

    if args.dry_run:
        json.dump(manifest, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    write_manifest(manifest, args.out)
    print(f"Wrote {args.out}", file=sys.stderr)
    kinds_path = args.out.parent / "kinds.json"
    write_kinds(kinds, kinds_path)
    print(f"Wrote {kinds_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
