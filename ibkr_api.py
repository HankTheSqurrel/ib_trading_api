#!/usr/bin/env python3
"""
Convenient entry point for the IBKR trading tool.
Running this script will immediately launch the GUI (gui.py).
"""
import os
import sys

# Ensure the package directory is on the import path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Import the GUI – the script starts the Tkinter mainloop on import
try:
    from ib_trading_api import gui  # noqa: F401 – imported for side‑effects
except Exception as e:
    # If the import fails, give a helpful message
    sys.stderr.write(f"Failed to launch GUI: {e}\n")
    sys.exit(1)
