"""Run the same installer from a source ZIP or a native plugin checkout."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from omarchy_workspaces.installer import main

if __name__ == "__main__":
    raise SystemExit(main(root))
