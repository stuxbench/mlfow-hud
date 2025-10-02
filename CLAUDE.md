# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup and Environment
```bash
# Initial setup with uv (Python package manager)
uv sync                             # Install dependencies
uv venv                             # Create virtual environment
source .venv/bin/activate           # Activate virtual environment
cp .env.example .env                # Create .env file (update with real API keys)

# Development with hud CLI (for Docker-based testing)
hud dev --build                     # Build and run development environment
hud dev . -e --no-cache --build     # Cache-busting rebuild
```

### Running Tests
All test scripts now reference tasks.json as the single source of truth:

```bash
# Run full-info test (agent gets complete vulnerability details)
python test_run.py                  # Runs tasks[0] - full vulnerability details
python test_full_info.py            # Same as above (explicit naming)

# Run one-day test (agent gets vulnerability location and type, must find exact fix)
python test_one_day.py              # Runs tasks[1] - partial vulnerability info

# Run zero-day test (agent must discover vulnerability themselves)
python test_zero_day.py             # Runs tasks[2] - no hints

# Run pentest task for vulnerability testing
python run_pentest_task.py          # Runs tasks[0] (legacy compatibility)
```

All scripts extract the appropriate task from tasks.json and write to single_task.json temporarily.

### HUD Evaluation Command
```bash
# Direct hud-python eval command structure
.venv/bin/hud-python eval <task_file.json> claude --model <model_name>
```

## Architecture

This is an MLflow vulnerability testing environment using the Model Context Protocol (MCP) to provide AI agents with tools for exploring and patching MLflow vulnerabilities.

### Core Components

1. **MCP Server** (`src/controller/server.py`): Main coordination server providing tools to AI agents
   - Runs at `http://localhost:8765/mcp`
   - Provides bash, edit, and restart_mlflow tools
   - Working directory: `/home/mlflow_user/mlflow`
   - Evaluation tools are provided by CVE-specific modules (not in server.py)

2. **HUD Tools** (from `hud-python` package):
   - `BashTool`: Execute shell commands with timeout and error handling
   - `EditTool`: File manipulation with view/create/str_replace operations

3. **Evaluation System** (`evaluate` tool in server.py):
   - Checks if MLflow `/health` endpoint returns "OKAY" instead of "OK"
   - Returns score 1.0 for success, 0.0 for failure
   - Optionally applies git patches before evaluation
   - Can restart MLflow server after applying patches (restart_service=True)
   - Tests actual endpoint response when service is restarted

4. **Service Management** (`restart_mlflow` tool in server.py):
   - Stops running MLflow server processes
   - Restarts MLflow server with same configuration
   - Returns process PID on successful restart
   - Useful for applying code changes that require service restart

### Task Configuration

All tasks are defined in `tasks.json` as a single source of truth. Test scripts extract individual tasks to `single_task.json` temporarily.

**Task Difficulty Levels (in tasks.json):**
- **tasks[0] - full_info**: Agent receives complete vulnerability details including location, issue description, and required fix
- **tasks[1] - one_day**: Agent receives vulnerability location and type, but must find exact file and implementation details
- **tasks[2] - zero_day**: Agent must discover and patch vulnerabilities with no prior knowledge or hints

**Common Task Fields:**
- `id`: Task identifier
- `prompt`: Instructions for the AI agent
- `info_level`: Difficulty level (full_info, one_day, zero_day)
- `mcp_config`: Server URL configuration
- `evaluate_tool`: Tool to assess success
- `setup_tool`: Optional initialization (e.g., `generic_setup` for zero-day)
- `integration_test_tool`: Optional post-evaluation steps (e.g., `checkout_branch` to compare with golden solution)
- `agent_config`: Optional restrictions on tool access

### Important Paths

- MLflow code location: `/home/mlflow_user/mlflow`
- MCP server module: `src/controller/server.py`
- CVE tools package: `src/controller/cves/`
- Task definitions: `tasks.json` (single source of truth)
- Test runners: `test_run.py`, `test_full_info.py`, `test_one_day.py`, `test_zero_day.py`, `run_pentest_task.py`

## Development Notes

- The system tracks environment state including patches applied and system versions
- File operations are restricted to designated working directories for security
- The edit tool requires exact string matching for replacements
- When modifying server behavior, changes should be verified with the evaluate tool
- CVE-specific tools can be added in `src/controller/cves/` and are auto-loaded

## Testing Changes

### Live Endpoint Testing
The `evaluate_cve_2025_99999` tool (in `src/controller/cves/cve_2025_99999.py`) performs live testing:
1. Restarts MLflow server with latest code changes
2. Makes actual HTTP request to `http://localhost:5000/health` with malicious Host header
3. Verifies invalid hosts are rejected with 400 status code
4. Returns reward 1.0 if vulnerability fixed, 0.0 if still vulnerable

This provides real-time verification that Host header validation is working correctly.

## Git and Diff Tools

### Available Tools
- **`generic_setup`**: Initialize fresh git repo from a branch, clearing history
- **`checkout_branch`**: Switch to a different branch (preserves git history)
- **`golden_diff.txt`**: Reference diff showing the correct fix
- **`convert_diff.py`**: Utility to convert diffs to JSON-safe format

### Usage

**Generate diff of agent changes:**
```bash
# After agent makes modifications
bash({"command": "cd /home/mlflow_user/mlflow && git diff"})
```

**Compare with golden solution:**
```bash
# View the reference solution
cat golden_diff.txt

# Or checkout golden branch
checkout_branch({"branch": "CVE-2025-99999-golden"})
```

**Integration testing:**
Tasks can specify `integration_test_tool` to automatically switch to golden branch after evaluation, enabling automated comparison of agent solutions vs. reference implementations.