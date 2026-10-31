"""Executable module entry point for python -m wayfire."""

import sys
from wayfire.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
