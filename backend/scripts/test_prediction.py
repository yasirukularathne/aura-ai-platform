"""Run the project-level prediction smoke test from the backend folder."""

import runpy
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "test_prediction.py"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
