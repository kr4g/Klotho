import json
import os

_EXPECTED_TREES = None


def get_expected_trees():
    global _EXPECTED_TREES
    if _EXPECTED_TREES is None:
        path = os.path.join(os.path.dirname(__file__), "expected_trees.json")
        with open(path) as f:
            _EXPECTED_TREES = json.load(f)
    return _EXPECTED_TREES
