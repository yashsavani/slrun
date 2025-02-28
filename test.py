#!/usr/bin/env python3
"""
Test script for slrun.

This script:
1. Prints basic system information
2. Creates a small file with timestamp
3. Sleeps for 10 seconds (to allow time for detach/attach testing)
4. Prints completion message
"""

import os
import platform
import time
from datetime import datetime

def main():
    # Print start message
    print("=" * 50)
    print(f"Test script started at: {datetime.now()}")
    print(f"Running on node: {platform.node()}")
    print(f"Python version: {platform.python_version()}")
    print(f"Process ID: {os.getpid()}")
    print("=" * 50)
    
    # Create a test file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"slrun_test_{timestamp}.txt"
    
    with open(filename, "w") as f:
        f.write(f"Test file created by slrun test at {datetime.now()}\n")
        f.write(f"Running on node: {platform.node()}\n")
    
    print(f"Created test file: {filename}")
    
    # Sleep to allow time for detach/attach testing
    print("Sleeping for 10 seconds...")
    for i in range(10, 0, -1):
        print(f"{i}...", end=" ", flush=True)
        time.sleep(1)
    print("Done!")
    
    # Print completion message
    print("=" * 50)
    print(f"Test script completed at: {datetime.now()}")
    print(f"Test file created: {os.path.abspath(filename)}")
    print("=" * 50)

if __name__ == "__main__":
    main()
