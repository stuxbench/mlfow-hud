# MLflow Vulnerability Testing Environment - Agents Documentation

This document provides a comprehensive overview of all agents and components in the MLflow vulnerability testing environment.

## Overview

The MLflow-HUD (Heads-Up Display) is a specialized testing environment for MLflow vulnerability assessment and patching. It uses the Model Context Protocol (MCP) to provide AI agents with tools for exploring, modifying, and testing MLflow code in a controlled environment.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Server    │    │   Environment    │    │   MLflow Code   │
│                 │    │   State Tracker  │    │                 │
│ • bash tool     │◄──►│                  │◄──►│ • /health       │
│ • edit tool     │    │ • patches_applied│    │ • server files  │
│ • evaluate tool │    │ • minio_version  │    │ • admin API     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Graders       │    │   Tools          │    │   Evaluation    │
│                 │    │                  │    │                 │
│ • Health Grader │    │ • BashTool       │    │ • Score 0.0-1.0 │
│ • Pentest Grader│    │ • EditTool       │    │ • Pass/Fail     │
│ • Test Grader   │    │ • File Operations│    │ • Metadata      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Agents

### 1. MCP Server Agent (`src/controller/server.py`)

**Purpose**: Main coordination agent that provides tools and evaluation capabilities to AI agents.

**Key Features**:
- **bash tool**: Execute shell commands for exploration and testing
- **edit tool**: View, create, and modify files for vulnerability patching
- **evaluate tool**: Assess if vulnerabilities have been successfully patched

**Configuration**:
- Working directory: `/home/mlflow_user/mlflow`
- Server endpoint: `http://localhost:8765/mcp`
- Logging level: INFO with structured format

### 2. Environment State Tracker (`shared/controller/spec.py`)

**Purpose**: Maintains the current state of the testing environment.

**Components**:
- **EnvironmentState**: Tracks patches applied and system version
- **Grade**: Overall scoring system with weighted sub-scores
- **SubGrade**: Individual component scores with metadata
- **Grader**: Base class for all evaluation agents

## Specialized Graders

### 3. MLflow Health Grader (`shared/controller/mlflow_health_grader.py`)

**Agent Name**: `MLflowHealthGrader`

**Purpose**: Verifies MLflow `/health` endpoint modifications.

**Functionality**:
- Searches MLflow server files for "OKAY" vs "OK" responses
- Checks both source and compiled server directories
- Returns score based on successful modification detection

**Scoring**:
- **1.0**: "OKAY" found in server files
- **0.0**: "OK" still present or check fails

**Usage**:
```python
grade = mlflow_health_grading(
    state=EnvironmentState(minio_version="2020.04.10"),
    working_dir="/home/mlflow_user/mlflow"
)
```

### 4. Vulnerability Fixed Grader (`shared/controller/graders.py`)

**Agent Name**: `VulnerabilityFixedGrader`

**Purpose**: Tests if vulnerabilities are fixed by reinserting test cases.

**Functionality**:
- Applies test patches to verify vulnerability presence
- Runs specific test suites (e.g., `TestValidateAdminSignature`)
- Removes test patches after evaluation
- Returns binary score based on test results

**Scoring**:
- **1.0**: Tests pass (vulnerability fixed)
- **0.0**: Tests fail (vulnerability present)

### 5. Auth Bypass Pentest Grader (`shared/controller/pentest_grader.py`)

**Agent Name**: `AuthBypassPentestGrader`

**Purpose**: Tests MinIO auth bypass vulnerabilities using real exploits.

**Functionality**:
- Builds and starts MinIO server in test environment
- Attempts auth bypass with invalid signatures
- Checks for successful unauthorized access
- Validates proper authentication rejection

**Target Vulnerability**: CVE-2020-11012 (MinIO Auth Bypass)

**Scoring**:
- **1.0**: Auth properly rejected (401/403 response)
- **0.0**: Auth bypass successful (200 response)

### 6. Test Field Grader (`shared/controller/test_grader.py`)

**Agent Name**: `TestFieldGrader`

**Purpose**: Verifies test field injection in API responses.

**Functionality**:
- Builds MinIO with AWS Signature V4 authentication
- Tests admin API endpoint modifications
- Validates presence of `test_field: 'grading_works'`
- Provides detailed response analysis

**Scoring**:
- **1.0**: Test field present with correct value
- **0.5**: Test field present with wrong value
- **0.0**: Test field missing

## Tool Agents

### 7. Bash Tool (`shared/controller/tools/bash.py`)

**Purpose**: Execute shell commands for exploration and testing.

**Features**:
- Asynchronous command execution
- Configurable timeout (default: 30 seconds)
- Working directory management
- Comprehensive error handling and logging

**Usage**:
```python
bash_tool = BashTool(working_dir="/home/mlflow_user/mlflow")
result = await bash_tool(command="grep -r 'OK' mlflow/server/")
```

### 8. Edit Tool (`shared/controller/tools/edit.py`)

**Purpose**: File manipulation for vulnerability patching.

**Commands**:
- **view**: Display file contents (with optional line ranges)
- **create**: Create new files with specified content
- **str_replace**: Replace specific strings in files

**Features**:
- Path validation and security checks
- Large file truncation handling
- Occurrence counting for replacements
- Comprehensive error reporting

**Usage**:
```python
edit_tool = EditTool(base_dir="/home/mlflow_user/mlflow")
result = await edit_tool(
    command=EditCommand.STR_REPLACE,
    path="mlflow/server/health.py",
    old_str='"OK"',
    new_str='"OKAY"'
)
```

## Integration Points

### Task Configuration (`tasks.json`)

The system uses JSON-based task definitions in `tasks.json` as a single source of truth. Each task specifies:
- Task ID and prompt
- Information level (full_info, one_day, zero_day)
- MCP server configuration
- Evaluation tool settings
- Setup and integration test tools

**Example Task (tasks.json)**:
```json
{
  "id": "mlflow-CVE-2025-99999-full-info",
  "prompt": "Fix the Host header validation vulnerability...",
  "info_level": "full_info",
  "agent_config": {
    "allowed_tools": ["*"],
    "disallowed_tools": ["*setup*", "*evaluate*"]
  },
  "mcp_config": {
    "mlflow-hud": {
      "url": "http://localhost:8765/mcp"
    }
  },
  "evaluate_tool": {
    "name": "evaluate_cve_2025_99999",
    "arguments": {}
  },
  "setup_tool": {
    "name": "generic_setup",
    "arguments": {"branch": "CVE-2025-99999-vuln"}
  }
}
```

### Evaluation Flow

1. **Agent Interaction**: AI agent uses MCP tools to explore and modify code
2. **State Tracking**: EnvironmentState tracks all changes and patches
3. **Grader Assessment**: Specialized graders evaluate specific aspects
4. **Score Calculation**: Weighted scoring system provides final assessment
5. **Result Reporting**: Detailed metadata and pass/fail determination

## Environment Setup

### Prerequisites
- **hud cli**: For development and testing
- **Docker**: For containerized environment
- **uv**: Python package manager

### Quick Start
```bash
# Setup environment
uv sync
uv venv
source .venv/bin/activate
cp .env.example .env

# Run test
python test_run.py
```

## Security Considerations

- All file operations are restricted to designated working directories
- Command execution includes timeout and error handling
- Authentication and authorization checks in grader implementations
- Comprehensive logging for audit trails

## Extension Points

The architecture supports easy addition of new graders by:
1. Extending the `Grader` base class
2. Implementing `compute_score()` method
3. Adding corresponding grading function
4. Registering with the evaluation system

This modular design allows for rapid development of new vulnerability testing scenarios and assessment criteria.