# slrun - SLURM Tools

## Why slrun?

Working with SLURM clusters can be frustrating. You write a script, create a job file, submit it with `sbatch`, then repeatedly check `squeue` for status, and finally dig through output files when it's done. It's a tedious process that interrupts your workflow and focuses on cluster mechanics rather than your actual work.

**slrun** transforms this experience by letting you work with SLURM as if you were running commands locally:

```bash
# Instead of creating batch files and using sbatch:
slrun launch python train_model.py --epochs 100
```

Your code runs on the cluster, but you see the output streaming in real-time. If you need to disconnect, just press `Ctrl+Z` and reconnect later with `slrun attach`. It's that simple.

### Pain Points Solved

- **No more job script files** - Run commands directly with minimal syntax changes
- **Real-time feedback** - See output as it happens, not just when jobs complete
- **Seamless workflow** - Start, monitor, detach, and reconnect without context switching
- **Resource templates** - Define profiles for different job types (small, large, debug)
- **Simplified monitoring** - One command to see all your detached jobs

### Perfect For

- **ML researchers** testing models on GPU clusters who need to iterate quickly
- **Data scientists** who want to run resource-intensive tasks without changing their workflow
- **Academic users** who need to submit jobs but don't want to learn SLURM's complexities
- **Teams sharing clusters** who want standardized resource configurations
- **Anyone** running long jobs who needs to disconnect and reconnect later

## Features

- **Seamless job submission**: Run commands on SLURM with minimal syntax changes
- **Real-time output streaming**: See stdout/stderr as if running locally
- **Detach/reattach capability**: Start a job, detach, and reconnect later
- **Job management**: List all detached jobs and their statuses
- **Configuration profiles**: Store different resource configurations in config file
- **Automatic cleanup**: Temporary files are removed when jobs complete

## Installation

### Using UV (recommended)

```bash
uv add slrun
```

### Directly from GitHub

```bash
uv pip install git+https://github.com/yashsavani/slrun.git
```

### Using pip

```bash
pip install slrun
```

## Quick Start

### Launch a job

```bash
slrun launch python train_model.py --epochs 100
```

### With custom SLURM resources

```bash
slrun launch --mem 128GB --time 2-00:00:00 --gres gpu:A100:2 python train_model.py
```

### Using a configuration profile

```bash
slrun launch --profile large python train_model.py
```

### Handling argument conflicts

When your command uses arguments that might conflict with `slrun`, use the `--` separator:

```bash
slrun launch --timeout 7200 -- python script.py --timeout 3600
```

### List all detached jobs

```bash
slrun list
```

### Reattach to a job

```bash
slrun attach 12345  # Replace with your job ID
```

## Configuration

You can customize default settings by creating a configuration file:

```bash
# Edit your configuration file
slrun config edit

# View your current configuration
slrun config show
```

Example configuration (`~/.slrun/config.toml`):

```toml
[defaults]
time = "2-00:00:00"
mem = "128GB"
gres = "gpu:A100:1"

[profiles.large]
time = "7-00:00:00"
mem = "256GB"
gres = "gpu:A100:4"

[profiles.debug]
time = "0-01:00:00"
mem = "16GB"
gres = "gpu:K80:1"
```

## Development

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/yashsavani/slrun.git
cd slurm-tools

# Install in development mode
uv pip install -e .
```

### Building the Package

```bash
uv build
```

## Documentation

For complete usage instructions, see the [detailed documentation](docs/usage.md).

## Requirements

- Python 3.6+
- Access to a SLURM cluster with `sbatch`, `squeue`, and `sacct` commands

## License

MIT
