#!/usr/bin/env python3
"""CLI entry point for srun command."""

import sys
from slrun.srun import main as srun_main

def main():
    """Entry point for the srun command."""
    return srun_main()

if __name__ == "__main__":
    sys.exit(main())
