"""Thin launcher for the interactive setup wizard.

Double-click launchers (setup.bat / setup.command) call this after installing
dependencies. It just imports and runs wizard.run_wizard().
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fm_copilot.wizard import run_wizard

if __name__ == "__main__":
    run_wizard()
