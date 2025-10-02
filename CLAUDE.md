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
```bash
# Run test task with MLflow health endpoint modification
python test_run.py                  # Runs test_task.json with claude-opus-4-1

# Run pentest task for vulnerability testing  
python run_pentest_task.py           # Runs full vulnerability assessment from tasks.json
```

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
   - Provides bash, edit, and evaluate tools
   - Working directory: `/home/mlflow_user/mlflow`

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

Tasks are defined in JSON files (`test_task.json`, `tasks.json`) with:
- `id`: Task identifier
- `prompt`: Instructions for the AI agent
- `info_level`: Level of information provided (e.g., "dummy_test")
- `mcp_config`: Server URL configuration
- `evaluate_tool`: Tool to assess success

### Important Paths

- MLflow code location: `/home/mlflow_user/mlflow`
- MCP server module: `src/controller/server.py`
- CVE tools package: `src/controller/cves/`
- Test runners: `test_run.py`, `run_pentest_task.py`

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
2. Makes actual HTTP request to `http://localhost:5000/health`
3. Verifies the response contains "OKAY" instead of "OK"
4. Returns reward 1.0 for success, 0.0 for failure

This provides real-time verification that code modifications are working in the live service.