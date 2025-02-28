#!/usr/bin/env python3
"""CLI entry point for srun command."""

import sys
from slrun.slrun import main as slrun_main

def main():
    """Entry point for the srun command."""
    return slrun_main()

if __name__ == "__main__":
    sys.exit(main())
