#!/usr/bin/env python3
"""Run commands on SLURM as if local with slrun.py launch <command>"""

import argparse
import json
import os
import subprocess
import sys
import time
import toml
import uuid
import signal
import shutil
from pathlib import Path

# Directory to store job information
SLRUN_DIR = Path.home() / ".slrun"

def load_config():
    """Load configuration from global and local config files."""
    config = {
        "defaults": {
            "time": "1-00:00:00",
            "mem": "64GB",
            "gres": "gpu:A6000:1",
            # Other defaults...
        },
        "profiles": {}
    }
    
    # Try global config
    global_config_path = Path.home() / ".slrun" / "config.toml"
    if global_config_path.exists():
        try:
            global_config = toml.load(str(global_config_path))
            # Merge with defaults
            config.update(global_config)
        except Exception as e:
            print(f"Warning: Could not load global config: {e}", file=sys.stderr)
    
    # Try local config (optional, would override global)
    local_config_path = Path(".slrun.toml")
    if local_config_path.exists():
        try:
            local_config = toml.load(str(local_config_path))
            # Merge with current config
            config.update(local_config)
        except Exception as e:
            print(f"Warning: Could not load local config: {e}", file=sys.stderr)
    
    return config

def show_config():
    """Display the current configuration."""
    global_config_path = Path.home() / ".slrun" / "config.toml"
    local_config_path = Path(".slrun.toml")
    
    print(f"\nslrun Configuration:")
    print(f"{'-' * 50}")
    
    # Show global configuration
    if global_config_path.exists():
        try:
            global_config = toml.load(str(global_config_path))
            print(f"\nGlobal config ({global_config_path}):")
            print_config(global_config)
        except Exception as e:
            print(f"Error reading global config: {e}")
    else:
        print(f"\nNo global configuration found at {global_config_path}")
        print(f"You can create one with 'slrun config edit'")
    
    # Show local configuration if it exists
    if local_config_path.exists():
        try:
            local_config = toml.load(str(local_config_path))
            print(f"\nLocal config ({local_config_path}):")
            print_config(local_config)
        except Exception as e:
            print(f"Error reading local config: {e}")
    
    # Show effective configuration (the result of merging global and local)
    config = load_config()
    print(f"\nEffective configuration (merged):")
    print_config(config)
    
    return 0

def print_config(config):
    """Helper function to print a configuration in a readable format."""
    if "defaults" in config:
        print("  [defaults]")
        for key, value in sorted(config["defaults"].items()):
            print(f"    {key} = {repr(value)}")
    
    if "profiles" in config:
        print("  [profiles]")
        for profile_name, profile in sorted(config["profiles"].items()):
            print(f"    [{profile_name}]")
            for key, value in sorted(profile.items()):
                print(f"      {key} = {repr(value)}")
    
    # Print any other top-level sections that might exist
    for section, content in sorted(config.items()):
        if section not in ["defaults", "profiles"] and isinstance(content, dict):
            print(f"  [{section}]")
            for key, value in sorted(content.items()):
                print(f"    {key} = {repr(value)}")

def edit_config():
    """Open the config file in the user's editor."""
    config_path = Path.home() / ".slrun" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not config_path.exists():
        # Create a template config file
        with open(config_path, "w") as f:
            f.write("""# slrun configuration file
[defaults]
# Default values for SLURM job parameters
time = "1-00:00:00"
mem = "64GB"
gres = "gpu:A6000:1"
timeout = 86400

# Optional profiles for different job types
[profiles.small]
time = "0-01:00:00"
mem = "16GB"
gres = "gpu:A6000:1"

[profiles.large]
time = "7-00:00:00"
mem = "64GB"
gres = "gpu:A100_40GB:4"
            """)

    # Open with the user's editor
    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(config_path)])
    return 0


def parse_args():
    # Load configuration first
    config = load_config()
    defaults = config.get("defaults", {})

    # First, handle the special case for launch subcommand
    if len(sys.argv) > 1 and sys.argv[1] == 'launch':
        # Find the -- delimiter if present
        try:
            delimiter_index = sys.argv.index('--', 2)  # Start search after 'launch'
            slrun_args = sys.argv[:delimiter_index]
            cmd_args = sys.argv[delimiter_index+1:]
            if not cmd_args:
                print("Error: No command specified after --", file=sys.stderr)
                sys.exit(1)
            use_delimiter = True
        except ValueError:
            # No -- delimiter found, process normally
            slrun_args = sys.argv
            cmd_args = []
            use_delimiter = False
    else:
        # Not a launch command or no -- delimiter
        slrun_args = sys.argv
        cmd_args = []
        use_delimiter = False

    parser = argparse.ArgumentParser(description='Run commands on SLURM as if local')
    subparsers = parser.add_subparsers(dest='command', help='Subcommand to run')
    subparsers.required = True
    
    # Launch command
    launch_parser = subparsers.add_parser('launch', help='Launch a new job')
    launch_parser.add_argument('--time', '-t', default=defaults.get('time', '1-00:00:00'), help='Wall clock time limit')
    launch_parser.add_argument('--mem', '-m', default=defaults.get('mem', '64GB'), help='Memory requirement')
    launch_parser.add_argument('--gres', '-g', default=defaults.get('gres', 'gpu:A6000:1'), help='Generic resources')
    launch_parser.add_argument('--nodelist', help='Nodes to use')
    launch_parser.add_argument('--exclude', help='Nodes to avoid')
    launch_parser.add_argument('--conda-env', '-c', default=defaults.get('conda_env'), help='Conda env (default: current)')
    launch_parser.add_argument('--timeout', default=defaults.get('timeout', 86400), type=int, help='Local timeout in seconds (default: 24h)')
    launch_parser.add_argument('--profile', '-p', help='Use a predefined configuration profile')
    if not use_delimiter:
        launch_parser.add_argument('cmd', nargs=argparse.REMAINDER, help='Command to run')

    # Add profile support
    
    # Attach command
    attach_parser = subparsers.add_parser('attach', help='Attach to an existing job')
    attach_parser.add_argument('job_id', help='Job ID to attach to')
    
    # List command
    subparsers.add_parser('list', help='List all detached jobs')

    # Config command
    config_parser = subparsers.add_parser('config', help='Edit or manage configuration')
    config_parser.add_argument('action', choices=['edit', 'show'], help='Action to perform on config')
    
    if use_delimiter:
        # Parse only slrun args and set cmd explicitly
        args = parser.parse_args(slrun_args)
        args.cmd = cmd_args
    else:
        args = parser.parse_args()
        
        # For launch, ensure we have a command
        if args.command == 'launch' and (not hasattr(args, 'cmd') or not args.cmd):
            launch_parser.error("No command specified to run")


    # Only handle profiles and node lists for the launch command
    if args.command == 'launch':
        # Apply profile if specified
        if hasattr(args, 'profile') and args.profile:
            profiles = config.get("profiles", {})
            if args.profile in profiles:
                profile = profiles[args.profile]
                # Apply profile values for regular options
                for key, value in profile.items():
                    if key not in ['nodelist', 'exclude'] and key in vars(args) and not is_arg_explicit(key, sys.argv):
                        setattr(args, key, value)
        
        # Handle special union case for nodelist and exclude
        profile_dict = {}
        if hasattr(args, 'profile') and args.profile:
            profile_dict = config.get("profiles", {}).get(args.profile, {})
        args = handle_node_lists(args, defaults, profile_dict)
    
    return args

def is_arg_explicit(key, argv):
    """Check if an argument was explicitly provided on command line."""
    arg_forms = [f'--{key}', f'-{key[0]}']
    return any(arg in argv for arg in arg_forms)

def handle_node_lists(args, defaults, profile):
    """Handle the special case of nodelist and exclude which should be combined from all sources."""
    
    # Function to parse a comma-separated list into a set of nodes
    def parse_node_list(value):
        if not value:
            return set()
        return set(node.strip() for node in value.split(',') if node.strip())
    
    # Function to convert a set back to a comma-separated list
    def format_node_list(nodes):
        return ','.join(sorted(nodes)) if nodes else None
    
    # Handle nodelist
    cmd_nodelist = parse_node_list(args.nodelist)
    config_nodelist = parse_node_list(profile.get('nodelist', defaults.get('nodelist', '')))
    
    # Union the sets of nodes
    final_nodelist = cmd_nodelist.union(config_nodelist)
    args.nodelist = format_node_list(final_nodelist)
    
    # Handle exclude
    cmd_exclude = parse_node_list(args.exclude)
    config_exclude = parse_node_list(profile.get('exclude', defaults.get('exclude', '')))
    
    # Union the sets of excluded nodes
    final_exclude = cmd_exclude.union(config_exclude)
    args.exclude = format_node_list(final_exclude)
    
    return args

def get_job_details(job_id):
    """Get detailed information about a SLURM job."""
    scontrol_cmd = ['scontrol', 'show', 'job', job_id]
    result = subprocess.run(scontrol_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return None
        
    job_info = {}
    current_section = job_info
    
    # Parse scontrol output
    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        parts = line.split()
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                current_section[key] = value
    
    return job_info

def format_job_status(job_info):
    """Format job status information for display."""
    if not job_info:
        return "Job information not available"
        
    job_state = job_info.get('JobState', 'UNKNOWN')
    
    # Format common information
    status_lines = [
        f"Job ID: {job_info.get('JobId', 'Unknown')}",
        f"State: {job_state}"
    ]
    
    # Format state-specific information
    if job_state == 'PENDING':
        reason = job_info.get('Reason', 'Unknown')
        status_lines.append(f"Reason: {reason}")
        
        if 'StartTime' in job_info and job_info['StartTime'] != 'N/A':
            status_lines.append(f"Estimated start: {job_info['StartTime']}")
            
        if 'Priority' in job_info:
            status_lines.append(f"Priority: {job_info['Priority']}")
            
    elif job_state == 'RUNNING':
        # Add node information
        if 'NodeList' in job_info:
            status_lines.append(f"Running on: {job_info['NodeList']}")
            
        # Add timing information
        if 'RunTime' in job_info:
            status_lines.append(f"Runtime: {job_info['RunTime']}")
            
        if 'StartTime' in job_info:
            status_lines.append(f"Started at: {job_info['StartTime']}")
            
        # Add resource allocation
        if 'NumNodes' in job_info and 'NumCPUs' in job_info:
            status_lines.append(f"Resources: {job_info['NumNodes']} node(s), {job_info['NumCPUs']} CPU(s)")
            
        if 'TRES' in job_info:
            # Parse TRES to extract GPU information
            tres = job_info['TRES']
            if 'gres/gpu=' in tres:
                gpu_info = tres.split('gres/gpu=')[1].split(',')[0]
                status_lines.append(f"GPUs: {gpu_info}")
    
    return "\n".join(status_lines)

def save_job_info(job_id, temp_dir, output_log, error_log, command):
    """Save job information to ~/.slrun directory"""
    # Create SLRUN_DIR if it doesn't exist
    SLRUN_DIR.mkdir(parents=True, exist_ok=True)
    
    job_info = {
        'job_id': job_id,
        'temp_dir': str(temp_dir.absolute()),
        'output_log': str(output_log.absolute()),
        'error_log': str(error_log.absolute()),
        'command': command,
        'detach_time': time.time()
    }
    
    job_file = SLRUN_DIR / f"{job_id}.json"
    with job_file.open('w') as f:
        json.dump(job_info, f, indent=2)
    
    return job_file

def load_job_info(job_id):
    """Load job information from ~/.slrun directory"""
    job_file = SLRUN_DIR / f"{job_id}.json"
    
    if not job_file.exists():
        print(f"No information found for job {job_id}", file=sys.stderr)
        return None
    
    try:
        with job_file.open('r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Invalid job information file for job {job_id}", file=sys.stderr)
        return None

def remove_job_info(job_id):
    """Remove job information file"""
    job_file = SLRUN_DIR / f"{job_id}.json"
    if job_file.exists():
        job_file.unlink()

def list_jobs():
    """List all detached jobs"""
    # Create SLRUN_DIR if it doesn't exist
    SLRUN_DIR.mkdir(parents=True, exist_ok=True)
    
    job_files = list(SLRUN_DIR.glob("*.json"))
    if not job_files:
        print("No detached jobs found.")
        return 0
    
    print(f"{'JOB ID':<10} {'STATUS':<12} {'DETACHED':<20} {'COMMAND':<40}")
    print("-" * 82)
    
    for job_file in job_files:
        try:
            with job_file.open('r') as f:
                job_info = json.load(f)
            
            job_id = job_info.get('job_id', 'Unknown')
            
            # Check job status
            status_cmd = ['sacct', '-j', job_id, '--format=State', '--noheader', '--parsable2']
            result = subprocess.run(status_cmd, capture_output=True, text=True)
            status = result.stdout.strip().split('\n')[0] if result.stdout else ""
            
            # Try squeue as fallback
            if not status:
                status_cmd = ['squeue', '-j', job_id, '--noheader', '--format=%T']
                result = subprocess.run(status_cmd, capture_output=True, text=True)
                status = result.stdout.strip() or "UNKNOWN"
            
            # Format detach time
            detach_time = job_info.get('detach_time', 0)
            detach_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(detach_time))
            
            # Format command (truncate if too long)
            command = ' '.join(job_info.get('command', []))
            if len(command) > 40:
                command = command[:37] + "..."
            
            print(f"{job_id:<10} {status:<12} {detach_str:<20} {command:<40}")
        
        except (json.JSONDecodeError, KeyError) as e:
            job_id = job_file.stem
            print(f"{job_id:<10} ERROR reading job info")
    
    return 0

def attach_to_job(job_id):
    """Attach to an existing job"""
    job_info = load_job_info(job_id)
    if not job_info:
        return 1
    
    # Extract job information
    temp_dir = Path(job_info['temp_dir'])
    output_log = Path(job_info['output_log'])
    error_log = Path(job_info['error_log'])
    
    # Validate directories and logs exist
    if not temp_dir.exists():
        print(f"Error: Temporary directory {temp_dir} not found", file=sys.stderr)
        remove_job_info(job_id)
        return 1
    
    # Check if log files exist
    if not output_log.exists() or not error_log.exists():
        print(f"Error: Log files not found", file=sys.stderr)
        remove_job_info(job_id)
        return 1
    
    print(f"Attaching to job {job_id}, streaming output...", file=sys.stderr)
    
    # Flag to track if we detached
    detached = False
    
    # Set up cleanup handler
    def cleanup(signum=None, frame=None):
        if signum:
            print(f"\nInterrupted, cleaning up...", file=sys.stderr)
        if not detached:  # Only clean up if we didn't detach
            # First cancel the SLURM job
            print(f"Canceling job {job_id}...", file=sys.stderr)
            subprocess.run(['scancel', job_id], stderr=subprocess.DEVNULL)
            
            # Wait a moment for SLURM to process the cancellation
            time.sleep(1)
            
            # Then clean up files
            shutil.rmtree(temp_dir, ignore_errors=True)
            remove_job_info(job_id)
        if signum:
            sys.exit(128 + signum)
    
    # Set up detach handler (Ctrl+Z)
    def detach_handler(signum, frame):
        nonlocal detached
        detached = True
        print(f"\n\nDetached from job {job_id}. Job will continue running.", file=sys.stderr)
        print(f"Output logs: {output_log}", file=sys.stderr)
        print(f"Error logs: {error_log}", file=sys.stderr)
        print(f"Check status with: squeue -j {job_id}", file=sys.stderr)
        print(f"Reattach with: slrun attach {job_id}", file=sys.stderr)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGTSTP, detach_handler)
    
    try:
        # Stream output and monitor job
        output_pos = error_pos = 0
        
        def read_output(file_path, stream, pos):
            """Read new content from the file and return the new position.
            Returns the original position if no new content was read."""
            if not file_path.exists():
                return pos
            try:
                with file_path.open('r') as f:
                    f.seek(pos)
                    content = f.read()
                    if content:
                        print(content, end='', file=stream, flush=True)
                        return f.tell()
                    return pos  # No new content
            except (IOError, OSError):
                # Silent fail on file issues, will retry next iteration
                return pos
        
        # Read all existing output first
        output_pos = read_output(output_log, sys.stdout, output_pos)
        error_pos = read_output(error_log, sys.stderr, error_pos)
        
        dots_count = 0
        last_state = None  # Initialize last_state here
        # Monitor job status and stream output
        while True:
            # Get detailed job information
            job_details = get_job_details(job_id)
            if job_details:
                current_state = job_details.get('JobState', 'UNKNOWN')
                
                # Show job details when state changes
                if current_state != last_state:
                    print(f"\n{'-' * 40}", file=sys.stderr)
                    print(format_job_status(job_details), file=sys.stderr)
                    print(f"{'-' * 40}\n", file=sys.stderr)
                    last_state = current_state
            else:
                current_state = None
            
            # Read new output
            new_output = read_output(output_log, sys.stdout, output_pos)
            new_error = read_output(error_log, sys.stderr, error_pos)

            # Only print a dot if in PENDING state and no new output was displayed
            if (current_state == 'PENDING' and 
                new_output == output_pos and new_error == error_pos):
                dots_count += 1
                if dots_count % 80 == 0:  # Start new line every 80 dots
                    print(".", file=sys.stderr)
                else:
                    print(".", end="", file=sys.stderr, flush=True)

            output_pos = new_output
            error_pos = new_error
            
            # Check if job completed or failed
            if current_state in ['COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT'] or not current_state:
                # Final read to get remaining output
                output_pos = read_output(output_log, sys.stdout, output_pos)
                error_pos = read_output(error_log, sys.stderr, error_pos)
                if dots_count > 0:  # Add a newline if we were printing dots
                    print(file=sys.stderr)
                print(f"\nJob {job_id} has {current_state.lower() if current_state else 'completed'}", file=sys.stderr)
                break
            
            time.sleep(0.5)
        
        # Get exit code
        exit_cmd = ['sacct', '-j', job_id, '--format=ExitCode', '--noheader', '--parsable2']
        result = subprocess.run(exit_cmd, capture_output=True, text=True)
        exit_code = result.stdout.strip().split('\n')[0] if result.stdout else "0:0"
        
        # Cleanup job information and temporary directory
        cleanup()
        
        return int(exit_code.split(':')[0])
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    finally:
        if not detached:  # Skip cleanup if detached
            cleanup()

def launch_job(args):
    """Launch a new job"""
    conda_env = args.conda_env or os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env == 'base':
        conda_env = None
    
    # Flag to track if we detached
    detached = False
    
    # Create temp directory in current working directory
    run_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    temp_dir = Path(f".slrun_tmp_{run_id}")
    temp_dir.mkdir(parents=True)
    log_dir = temp_dir / "logs"
    log_dir.mkdir()
    
    # Set up cleanup handler
    def cleanup(signum=None, frame=None):
        if signum:
            print(f"\nInterrupted, cleaning up...", file=sys.stderr)
        if not detached:  # Only clean up if we didn't detach
            # First cancel the SLURM job if it exists
            if 'job_id' in locals() or 'job_id' in globals():
                print(f"Canceling job {job_id}...", file=sys.stderr)
                subprocess.run(['scancel', job_id], stderr=subprocess.DEVNULL)
                # Wait a moment for SLURM to process the cancellation
                time.sleep(1)
                # Remove job info file
                remove_job_info(job_id)
            
            # Then clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
        if signum:
            sys.exit(128 + signum)
    
    # Set up detach handler (Ctrl+Z)
    def detach_handler(signum, frame):
        nonlocal detached
        detached = True
        
        # Save job information for later reattachment
        job_file = save_job_info(job_id, temp_dir, output_log, error_log, args.cmd)
        
        print(f"\n\nDetached from job {job_id}. Job will continue running.", file=sys.stderr)
        print(f"Output logs: {output_log.absolute()}", file=sys.stderr)
        print(f"Error logs: {error_log.absolute()}", file=sys.stderr)
        print(f"Check status with: squeue -j {job_id}", file=sys.stderr)
        print(f"Reattach with: slrun attach {job_id}", file=sys.stderr)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Create job script
        script_path = temp_dir / "run_job.sh"
        conda_cmd = f"conda activate {conda_env}" if conda_env else ""
        with script_path.open("w") as f:
            f.write(f"""#!/bin/bash
export USE_BASH_FOR_SBATCH=1
source $HOME/.bashrc
{conda_cmd}

{' '.join(args.cmd)}
""")
        script_path.chmod(0o755)
        
        # Submit job
        output_log = log_dir / "output.log"
        error_log = log_dir / "error.log"
        
        # Create empty log files
        output_log.touch(mode=0o644)
        error_log.touch(mode=0o644)
        
        sbatch_cmd = [
            'sbatch', '--parsable', 
            '--job-name', f"slrun_{os.getenv('USER', 'user')}",
            '--time', args.time, '--mem', args.mem, '--gres', args.gres,
            '--output', str(output_log.absolute()), '--error', str(error_log.absolute()),
            '--chdir', os.getcwd(),
        ]
        
        for opt in ['nodelist', 'exclude']:
            if getattr(args, opt):
                sbatch_cmd.extend([f'--{opt}', getattr(args, opt)])
        
        sbatch_cmd.append(str(script_path))
        
        result = subprocess.run(sbatch_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error submitting job: {result.stderr}", file=sys.stderr)
            return 1
        
        job_id = result.stdout.strip()
        print(f"Submitted job {job_id}, streaming output...", file=sys.stderr)
        print(f"Press Ctrl+Z to detach and let the job run in the background", file=sys.stderr)
        
        # Set up the detach handler now that we have the job_id
        signal.signal(signal.SIGTSTP, detach_handler)
        
        # Stream output and monitor job
        output_pos = error_pos = 0
        dots_count = 0
        start_time = time.time()
        last_state = None 
        
        def read_output(file_path, stream, pos):
            """Read new content from the file and return the new position.
            Returns the original position if no new content was read."""
            if not file_path.exists():
                return pos
            try:
                with file_path.open('r') as f:
                    f.seek(pos)
                    content = f.read()
                    if content:
                        print(content, end='', file=stream, flush=True)
                        return f.tell()
                    return pos  # No new content
            except (IOError, OSError):
                # Silent fail on file issues, will retry next iteration
                return pos
        
        # Monitor job status and stream output
        while True:
            # Check if we've exceeded the timeout
            if time.time() - start_time > args.timeout:
                print(f"\nTimeout after {args.timeout} seconds, cancelling job...", file=sys.stderr)
                subprocess.run(['scancel', job_id], stderr=subprocess.DEVNULL)
                return 124  # Standard timeout exit code

            # Get detailed job information
            job_details = get_job_details(job_id)
            if job_details:
                current_state = job_details.get('JobState', 'UNKNOWN')
                
                # Show job details when state changes
                if current_state != last_state:
                    print(f"\n{'-' * 40}", file=sys.stderr)
                    print(format_job_status(job_details), file=sys.stderr)
                    print(f"{'-' * 40}\n", file=sys.stderr)
                    last_state = current_state
            else:
                current_state = None
                
            # Read new output
            new_output = read_output(output_log, sys.stdout, output_pos)
            new_error = read_output(error_log, sys.stderr, error_pos)
            
            # Only print a dot if in PENDING state and no new output was displayed
            if (current_state in ['PENDING', 'CONFIGURING', 'REQUEUED'] and 
                new_output == output_pos and new_error == error_pos):
                dots_count += 1
                if dots_count % 80 == 0:  # Start new line every 80 dots
                    print(".", file=sys.stderr)
                else:
                    print(".", end="", file=sys.stderr, flush=True)
                    
            output_pos = new_output
            error_pos = new_error
            
            # Check if job completed or failed
            if current_state in ['COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT'] or not current_state:
                # Final read to get remaining output
                output_pos = read_output(output_log, sys.stdout, output_pos)
                error_pos = read_output(error_log, sys.stderr, error_pos)
                if dots_count > 0:  # Add a newline if we were printing dots
                    print(file=sys.stderr)
                break
            
            time.sleep(0.5)
        
        # Get exit code
        exit_cmd = ['sacct', '-j', job_id, '--format=ExitCode', '--noheader', '--parsable2']
        result = subprocess.run(exit_cmd, capture_output=True, text=True)
        exit_code = result.stdout.strip().split('\n')[0] if result.stdout else "0:0"
        return int(exit_code.split(':')[0])
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    finally:
        if not detached:  # Skip cleanup if detached
            cleanup()

def main():
    # Parse arguments
    args = parse_args()
    
    # Dispatch to appropriate function based on subcommand
    if args.command == 'list':
        return list_jobs()
    elif args.command == 'attach':
        return attach_to_job(args.job_id)
    elif args.command == 'launch':
        return launch_job(args)
    elif args.command == 'config':
        if args.action == 'edit':
            return edit_config()
        elif args.action == 'show':
            return show_config()
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
