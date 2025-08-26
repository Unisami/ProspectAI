#!/usr/bin/env python3
"""
Run script for the GUI Runner application.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from gui_runner import main
    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"Error importing GUI runner: {e}")
    print("Make sure all dependencies are installed and the project structure is correct.")
    sys.exit(1)