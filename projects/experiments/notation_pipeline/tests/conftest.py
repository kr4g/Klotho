"""Test configuration for notation pipeline tests."""

import sys
from pathlib import Path

# Ensure the project root is on the path so we can import klotho
project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Ensure the experiments dir is on the path for relative imports
experiments_dir = Path(__file__).resolve().parents[2]
if str(experiments_dir) not in sys.path:
    sys.path.insert(0, str(experiments_dir))
