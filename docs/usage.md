# slrun: Run Commands on SLURM as if Local

`slrun` is a utility that makes running jobs on SLURM clusters feel like running them locally. It handles job submission, monitors output in real-time, allows detaching and reattaching to running jobs, and cleans up when done.

## Command Structure

`slrun` uses a subcommand structure with these main operations:

### 1. Launch a Job

```bash
slrun launch [options] [--] <command> [args...]
```

### 2. Attach to a Running Job

```bash
slrun attach <job_id>
```

### 3. List Detached Jobs

```bash
slrun list
```

### 4. Manage Configuration

```bash
slrun config edit|show
```

## Usage Examples

### Basic Usage

Run a Python script on the cluster:

```bash
slrun launch python train_model.py --epochs 100
```

### Specify SLURM Resources

Allocate custom memory, time, and GPU resources:

```bash
slrun launch --mem 128GB --time 2-00:00:00 --gres gpu:A100:2 python train_model.py
```

### Using Configuration Profiles

Use predefined resource settings from your config:

```bash
slrun launch --profile large python train_model.py
```

### Handling Argument Conflicts

When your command uses arguments that might conflict with `slrun`, use the `--` separator:

```bash
slrun launch --timeout 7200 -- python script.py --timeout 3600
```

### Detaching and Reattaching

1. Start a job:
   ```bash
   slrun launch python long_process.py
   ```

2. Detach with `Ctrl+Z` when needed

3. See your running jobs:
   ```bash
   slrun list
   ```

4. Reattach to continue monitoring:
   ```bash
   slrun attach 12345  # Replace with your job ID
   ```

## Options

### Launch Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--time` | `-t` | `1-00:00:00` | Wall clock time limit (days-hours:minutes:seconds) |
| `--mem` | `-m` | `64GB` | Memory requirement |
| `--gres` | `-g` | `gpu:A6000:1` | Generic resources (typically GPUs) |
| `--nodelist` | | | Specific nodes to use |
| `--exclude` | | | Nodes to avoid |
| `--conda-env` | `-c` | Current env | Conda environment to activate |
| `--timeout` | | `86400` (24h) | Local timeout in seconds |
| `--profile` | `-p` | | Use a predefined configuration profile |

## Configuration

`slrun` supports configuration files to store your preferred defaults and profiles.

### Configuration File Locations

- Global: `~/.slrun/config.toml`
- Project-local: `.slrun.toml` (optional, in your project directory)

When both files exist, project-local settings take precedence over global settings.

### Managing Configuration

```bash
# Edit your configuration file
slrun config edit

# View your current configuration
slrun config show
```

### Example Configuration

```toml
# ~/.slrun/config.toml

[defaults]
# Default values used for all jobs
time = "1-00:00:00"
mem = "64GB"
gres = "gpu:A6000:1"
exclude = "broken-node1,broken-node2"
timeout = 86400

[profiles]
# Define different profiles for different types of jobs

[profiles.debug]
time = "0-01:00:00"
mem = "16GB"
gres = "gpu:K80:1"

[profiles.small]
time = "1-00:00:00"
mem = "64GB"
gres = "gpu:A6000:1"

[profiles.large]
time = "7-00:00:00"
mem = "256GB"
gres = "gpu:A100:4"
nodelist = "fast-node1,fast-node2"
```

### Configuration Precedence

When determining which values to use, `slrun` follows this precedence order:

1. Command line arguments (highest precedence)
2. Project-local config file settings
3. Global config file settings
4. Built-in defaults (lowest precedence)

For `nodelist` and `exclude`, values from all sources are combined (unioned).

## How It Works

1. **Job Submission**: Creates a temporary directory with a shell script that runs your command
2. **Real-time Monitoring**: Continuously polls the job status and streams the output
3. **Detach Capability**: When you detach, job information is saved to `~/.slrun/`
4. **Reattach Capability**: Reconnects to the job using the saved information
5. **Cleanup**: Removes temporary files when the job completes

## Key Features

### Interactive Monitoring

The script streams stdout/stderr in real-time, making it feel like you're running the command locally.

### Detaching from Jobs

Press `Ctrl+Z` to detach from a running job. The job continues running, and you'll see a message with the job ID and instructions for reattaching.

### Job Management

List all detached jobs with their status:

```bash
slrun list
```

Output shows job IDs, statuses, detach times, and commands.

### Configuration Profiles

Use different resource configurations depending on your needs:

```bash
# Quick debugging run
slrun launch --profile debug python debug_script.py

# Production run with heavy resource requirements
slrun launch --profile large python production_run.py
```

### Automatic Cleanup

Temporary files are automatically cleaned up when:
- A job completes while being monitored
- You reattach to a job and it completes
- You cancel a job with `Ctrl+C`

No cleanup occurs when you detach from a job, allowing later reattachment.

## Tips and Best Practices

### Creating Useful Profiles

Define profiles for your common job types:
- `debug` - Short-running jobs with minimal resources
- `interactive` - Medium resources with faster nodes for interactive work
- `batch` - Jobs that run overnight with standard resources
- `large` - Heavy jobs that need maximum resources

### Managing Long-Running Jobs

For jobs expected to run for days:
1. Use a profile with a generous time limit: `--profile large`
2. Detach once you confirm it's running correctly
3. Periodically check status with `slrun list`
4. Reattach as needed to check progress

### Handling Job Failures

If a job fails:
1. Reattach to view the error output: `slrun attach <job_id>`
2. After reviewing errors, the temporary files will be cleaned up

### Working with Multiple Jobs

Launch multiple jobs and manage them easily:

```bash
# Start multiple jobs
slrun launch --profile small python job1.py
# Detach with Ctrl+Z when it's running
slrun launch --profile small python job2.py
# Detach with Ctrl+Z when it's running

# Check all jobs
slrun list

# Attach to specific job
slrun attach <job_id>
```
