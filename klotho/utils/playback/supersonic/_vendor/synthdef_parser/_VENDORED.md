# Vendored: synthdef_parser

This directory contains a verbatim copy of the `synthdef_parser` package
(MIT-licensed) used by Klotho to extract argument names and default values
from compiled SuperCollider `.scsyndef` files for the SuperSonic manifest
regeneration pipeline.

## Upstream

- Repository: https://github.com/rexmalebka/synthdef_parser
- Commit: `ff512d9ae4cf8571a42534f3f238ce7bb5e994b8`
- Files vendored: `synthdef_parser/__init__.py`, `synthdef_parser/parser.py`,
  `LICENSE`.

## Why vendored

The package is not published on PyPI (the README's `pip install
synthdef-parser` 404s), it is pure-Python with no dependencies beyond
`struct` / `json` from the stdlib, and it is small (~310 lines). Vendoring
keeps `klotho` build / install free of an additional clone step or a
private package dependency.

## Updating

To pull a newer version, replace `__init__.py` and `parser.py` from the
upstream repository at the new commit, update the SHA above, and re-run
`klotho/utils/playback/supersonic/scripts/regenerate_manifest.py --dry-run`
to verify nothing has changed in the binary parsing semantics.
