"""Shared paths and helpers for the renderer tests."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "skills" / "explain" / "engine"
EXAMPLES = REPO / "skills" / "explain" / "examples"
sys.path.insert(0, str(ENGINE))


def render(json_path, out, root=EXAMPLES):
    """Run render.py as the skill does; return the CompletedProcess."""
    return subprocess.run([sys.executable, str(ENGINE / "render.py"), str(json_path),
                           "--root", str(root), "--out", str(out)],
                          capture_output=True, text=True)
