"""Migrate example notebooks to the new fluent UCNodeSelector API.

Applies a series of regex transformations to each code cell:
- ``list(uc._rt.leaf_nodes)`` / ``list(uc.rt.leaf_nodes)`` -> ``uc.leaves``
- ``list(uc.leaves)`` -> ``uc.leaves`` (when used as iterable arg)
- ``uc.set_pfields(uc.[_]rt.root, ...)`` -> ``uc.root.set_pfields(...)``
- ``uc.set_pfields(uc.root, ...)`` -> ``uc.root.set_pfields(...)``
- ``uc.set_pfields(uc.leaves, ...)`` -> ``uc.leaves.set_pfields(...)``
- ``uc.set_mfields(...)`` -> same patterns
- ``uc.set_instrument(uc.[_]rt.root, X)`` -> ``uc.root.set_instrument(X)``
- ``uc.set_instrument(uc.root, X)`` -> ``uc.root.set_instrument(X)``
- ``uc.apply_envelope(..., node=uc.[_]rt.root, ...)`` -> ``uc.root.apply_envelope(...)``
- ``uc.apply_envelope(..., node=uc.root, ...)`` -> ``uc.root.apply_envelope(...)``
- ``uc.apply_slur(..., node=uc.root, ...)`` -> ``uc.root.apply_slur(...)``
- normalises ``node=uc._rt.root``/``uc.rt.root`` -> ``node=uc.root`` everywhere
- drops ``list()`` wrap around ``uc.successors(...)`` and ``uc.at_depth(...)``
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

NOTEBOOKS = [
    "examples/score_demo.ipynb",
    "examples/score_control_envs.ipynb",
    "examples/score_drones.ipynb",
    "examples/uc_uts_supersonic_tuple_poly_examples.ipynb",
]


def migrate_text(text: str) -> str:
    # Step 1: drop list() around .leaves / .leaf_nodes, normalize to .leaves
    text = re.sub(r'list\((\w+)\._rt\.leaf_nodes\)', r'\1.leaves', text)
    text = re.sub(r'list\((\w+)\.rt\.leaf_nodes\)', r'\1.leaves', text)
    text = re.sub(r'list\((\w+)\.leaves\)', r'\1.leaves', text)

    # Drop list() around uc.successors(X) and uc.at_depth(X) where they're
    # used as iterable args (selector is iterable).
    text = re.sub(r'list\((\w+)\.successors\(([^)]+)\)\)', r'\1.successors(\2)', text)
    text = re.sub(r'list\((\w+)\.at_depth\(([^)]+)\)\)', r'\1.at_depth(\2)', text)

    # Step 2: normalize `node=uc._rt.root` / `uc.rt.root` to `node=uc.root`
    text = re.sub(r'\bnode=(\w+)\._rt\.root\b', r'node=\1.root', text)
    text = re.sub(r'\bnode=(\w+)\.rt\.root\b', r'node=\1.root', text)

    # Step 3: simple verb migrations (single-line)
    for verb in ('set_pfields', 'set_mfields'):
        # uc.set_pfields(uc.[_]rt.root, kwargs...) -> uc.root.set_pfields(kwargs...)
        text = re.sub(
            rf'\b(\w+)\.{verb}\(\1\._rt\.root,\s*',
            rf'\1.root.{verb}(',
            text,
        )
        text = re.sub(
            rf'\b(\w+)\.{verb}\(\1\.rt\.root,\s*',
            rf'\1.root.{verb}(',
            text,
        )
        text = re.sub(
            rf'\b(\w+)\.{verb}\(\1\.root,\s*',
            rf'\1.root.{verb}(',
            text,
        )
        text = re.sub(
            rf'\b(\w+)\.{verb}\(\1\.leaves,\s*',
            rf'\1.leaves.{verb}(',
            text,
        )

    # set_instrument(uc.X, Y)
    for prefix in ('_rt.', 'rt.', ''):
        text = re.sub(
            rf'\b(\w+)\.set_instrument\(\1\.{prefix}root,\s*([^)]+)\)',
            rf'\1.root.set_instrument(\2)',
            text,
        )
    text = re.sub(
        r'\b(\w+)\.set_instrument\(\1\.leaves,\s*([^)]+)\)',
        r'\1.leaves.set_instrument(\2)',
        text,
    )

    # Step 4: apply_envelope / apply_slur with node=uc.root somewhere in args.
    # Operates on the multi-line form and removes node=uc.root, hoisting the
    # call to uc.root.apply_envelope(...).
    def _hoist_root_envelope(verb: str):
        def repl(m: re.Match) -> str:
            uc_name = m.group(1)
            args = m.group(2)
            node_pat = rf'\bnode={re.escape(uc_name)}\.root\b'
            if not re.search(node_pat, args):
                return m.group(0)
            # Strip the `node=uc.root` argument and any surrounding comma/whitespace
            new_args = re.sub(
                rf',\s*node={re.escape(uc_name)}\.root\b',
                '',
                args,
            )
            new_args = re.sub(
                rf'\bnode={re.escape(uc_name)}\.root\b\s*,?\s*',
                '',
                new_args,
            )
            # Tidy any leading whitespace from removing first arg
            new_args = re.sub(r'\(\s*,', '(', new_args)
            return f'{uc_name}.root.{verb}({new_args})'

        return repl

    text = re.sub(
        r'\b(\w+)\.apply_envelope\((.+?)\)\s*$',
        _hoist_root_envelope('apply_envelope'),
        text,
        flags=re.DOTALL | re.MULTILINE,
    )
    text = re.sub(
        r'\b(\w+)\.apply_slur\((.+?)\)\s*$',
        _hoist_root_envelope('apply_slur'),
        text,
        flags=re.DOTALL | re.MULTILINE,
    )

    return text


def migrate_notebook(path: Path) -> int:
    nb = json.loads(path.read_text())
    n_changed = 0
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        new_source = migrate_text(source)
        if new_source != source:
            # Preserve line breaks: nbformat stores source as list of strings
            # with trailing newlines (except possibly the last).
            lines = new_source.splitlines(keepends=True)
            cell["source"] = lines
            n_changed += 1
    if n_changed:
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    return n_changed


def main():
    for nb_rel in NOTEBOOKS:
        path = REPO / nb_rel
        n = migrate_notebook(path)
        print(f"{nb_rel}: {n} cell(s) changed")


if __name__ == "__main__":
    main()
