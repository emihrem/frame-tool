"""PyInstaller entry point for the GUI bundle."""

import sys

from frame_tool.gui.app import launch_gui

if __name__ == "__main__":
    sys.exit(launch_gui())
