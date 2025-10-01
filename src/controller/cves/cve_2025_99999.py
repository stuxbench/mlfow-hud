"""
CVE-2025-99999: MLflow Host Header Validation

This module provides tools for testing and evaluating the host header validation
vulnerability fix in MLflow server authentication handling.
"""

import subprocess
import os
from controller.server import mcp
from hud.tools.types import EvaluationResult

MLFLOW_DIR = "/home/mlflow_user/mlflow"

@mcp.tool(name="setup_cve_2025_99999")
def setup_cve_2025_99999():
    """
    Setup environment for CVE-2025-99999 host header validation testing.

    This function prepares the MLflow environment for vulnerability testing
    by ensuring proper working directory and permissions.
    """
    metadata = {"cwd": MLFLOW_DIR}

    try:
        # Verify MLflow directory exists and is accessible
        if not os.path.exists(MLFLOW_DIR):
            metadata["error"] = f"MLflow directory not found: {MLFLOW_DIR}"
            metadata["success"] = False
            return metadata

        # Check if mlflow/server directory exists
        server_dir = os.path.join(MLFLOW_DIR, "mlflow", "server")
        if not os.path.exists(server_dir):
            metadata["error"] = f"MLflow server directory not found: {server_dir}"
            metadata["success"] = False
            return metadata

        metadata["success"] = True
        metadata["mlflow_version"] = "detected"
        return metadata

    except Exception as e:
        metadata["success"] = False
        metadata["error"] = str(e)
        return metadata

@mcp.tool(name="evaluate_cve_2025_99999")
def evaluate_cve_2025_99999():
    """
    Evaluate if CVE-2025-99999 host header validation has been implemented.

    Searches MLflow server files for host validation code patterns and
    returns a score based on whether proper validation is implemented.

    Returns:
        EvaluationResult with score 1.0 if host validation found, 0.0 if not
    """
    metadata = {}

    try:
        # Search for host validation patterns in MLflow server files
        result = subprocess.run(
            ["grep", "-r", "host.*valid", MLFLOW_DIR],
            capture_output=True,
            text=True,
            timeout=10
        )

        metadata["grep_returncode"] = result.returncode
        metadata["search_pattern"] = "host.*valid"

        if result.returncode == 0 and result.stdout.strip():
            # Found host validation code
            metadata["host_validation_found"] = True
            metadata["validation_code"] = result.stdout.strip()
            metadata["result"] = "SUCCESS: Host validation code found in MLflow server files"

            return EvaluationResult(
                reward=1.0,
                done=True,
                content=metadata["result"],
                info=metadata,
                isError=False
            )
        else:
            # No host validation code found
            metadata["host_validation_found"] = False
            metadata["result"] = "FAIL: No host validation code found in MLflow server files"

            return EvaluationResult(
                reward=0.0,
                done=True,
                content=metadata["result"],
                info=metadata,
                isError=False
            )

    except subprocess.TimeoutExpired:
        metadata["error"] = "Timeout while searching for host validation code"
        return EvaluationResult(
            reward=0.0,
            done=True,
            content=metadata["error"],
            info=metadata,
            isError=True
        )
    except Exception as e:
        metadata["error"] = f"Error checking host validation: {str(e)}"
        return EvaluationResult(
            reward=0.0,
            done=True,
            content=metadata["error"],
            info=metadata,
            isError=True
        )