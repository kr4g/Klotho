"""Snapshot every CompositionalUnit and Score in each example notebook.

Used as a before/after parity check when migrating example notebooks
to the new fluent UCNodeSelector API.

Usage:
    python scripts/snapshot_examples.py <out_dir>
"""

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

NOTEBOOKS = [
    "examples/score_demo.ipynb",
    "examples/score_control_envs.ipynb",
    "examples/score_drones.ipynb",
    "examples/uc_uts_supersonic_tuple_poly_examples.ipynb",
]


def _load_capture():
    spec = importlib.util.spec_from_file_location(
        "parity_capture", REPO / "tests/fixtures/parity/capture.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snapshot(nb_path: Path, capture):
    import klotho
    klotho.play = lambda *a, **kw: None

    from klotho.thetos.composition.compositional import CompositionalUnit
    from klotho.thetos.composition.score import Score

    with open(nb_path) as f:
        nb = json.load(f)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    script = "\n\n".join("".join(c["source"]) for c in code_cells)

    ns = {"__name__": "__main__"}
    exec(script, ns)

    ucs = {n: v for n, v in ns.items()
           if not n.startswith("_") and isinstance(v, CompositionalUnit)}
    scores = {n: v for n, v in ns.items()
              if not n.startswith("_") and isinstance(v, Score)}

    id_norm = capture._IdNormalizer()
    out = {"notebook": str(nb_path.relative_to(REPO)), "ucs": {}, "ucs_assembly": {}, "scores": {}}

    for name in sorted(ucs):
        out["ucs"][name] = capture._capture_uc_ir(ucs[name], id_norm)
        try:
            out["ucs_assembly"][name] = capture._capture_uc_assembly(ucs[name], id_norm)
        except Exception as e:
            out["ucs_assembly"][name] = f"<assembly capture error: {type(e).__name__}: {e}>"

    for name in sorted(scores):
        try:
            out["scores"][name] = capture._capture_score_payload(scores[name], id_norm)
        except Exception as e:
            out["scores"][name] = f"<score capture error: {type(e).__name__}: {e}>"

    return out


def main():
    if len(sys.argv) != 2:
        print("usage: python scripts/snapshot_examples.py <out_dir>", file=sys.stderr)
        sys.exit(2)
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    capture = _load_capture()
    for nb_rel in NOTEBOOKS:
        nb_path = REPO / nb_rel
        snap = snapshot(nb_path, capture)
        out_file = out_dir / (Path(nb_rel).stem + ".json")
        with open(out_file, "w") as f:
            json.dump(snap, f, indent=2, sort_keys=True)
        n_ucs = len(snap["ucs"])
        n_scores = len(snap["scores"])
        print(f"{nb_rel}: {n_ucs} UCs, {n_scores} Scores -> {out_file}")


if __name__ == "__main__":
    main()
