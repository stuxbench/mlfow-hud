"""
CVE-2025-99999: MLflow Host Header Validation

This module provides tools for testing and evaluating the host header validation
vulnerability fix in MLflow server authentication handling.
"""

import subprocess
import os
import time
import requests
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

def launch_mlflow_service():
    """
    Restart the MLflow server to apply code changes.

    Returns:
        Metadata about the service launch
    """
    import logging
    metadata = {}
    try:
        # Kill existing MLflow processes
        logging.info("Attempting to kill existing MLflow processes...")

        # Force kill all MLflow processes
        kill_result = subprocess.run(
            ["pkill", "-9", "-f", "mlflow"],
            capture_output=True,
            text=True
        )
        metadata["kill_returncode"] = kill_result.returncode

        if kill_result.returncode == 0:
            logging.info("Successfully killed MLflow processes")
        else:
            logging.info("No MLflow processes found to kill (or already dead)")

        # Wait for processes to fully terminate and port to free up
        logging.info("Waiting for port to be released...")
        time.sleep(5)

        # Start MLflow server in background with retry logic
        env = {
            **os.environ,
            'PATH': '/home/mlflow_user/mlflow/.venv/bin:' + os.environ.get('PATH', '')
        }

        max_retries = 3
        for retry in range(max_retries):
            logging.info(f"Starting MLflow server in {MLFLOW_DIR} (attempt {retry + 1}/{max_retries})")
            process = subprocess.Popen(
                ["mlflow", "server", "--host", "0.0.0.0"],
                cwd=MLFLOW_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            metadata["initial_pid"] = process.pid
            logging.info(f"Started process with PID: {process.pid}")

            # Wait for service to start
            time.sleep(5)

            # Check if process is still running
            if process.poll() is not None:
                # Process died - capture the error output
                stdout, stderr = process.communicate(timeout=1)
                stderr_text = stderr.decode() if stderr else ""

                # Check if it's an address-in-use error
                if "Address already in use" in stderr_text and retry < max_retries - 1:
                    logging.warning(f"Port still in use, waiting before retry {retry + 2}...")
                    time.sleep(3)
                    continue

                # Final failure
                metadata["error"] = "MLflow process terminated unexpectedly"
                metadata["returncode"] = process.returncode
                metadata["stdout"] = stdout.decode()[-1000:] if stdout else ""
                metadata["stderr"] = stderr_text[-1000:]
                metadata["success"] = False
                metadata["retry_count"] = retry + 1
                logging.error(f"MLflow failed after {retry + 1} attempts: returncode={process.returncode}")
                logging.error(f"stderr: {metadata['stderr']}")
                return metadata

            # Success!
            metadata["success"] = True
            metadata["pid"] = process.pid
            metadata["message"] = f"MLflow service launched successfully on attempt {retry + 1}"
            metadata["retry_count"] = retry + 1
            logging.info(f"MLflow service launched successfully with PID {process.pid}")
            return metadata

        # Should not reach here, but just in case
        metadata["error"] = "Failed to start MLflow after all retries"
        metadata["success"] = False
        return metadata

    except Exception as e:
        metadata["error"] = f"Failed to launch service: {str(e)}"
        metadata["success"] = False
        logging.exception("Failed to launch service")
        return metadata

def pentest_health_endpoint():
    """
    Run a live test of the MLflow /health endpoint.

    This test makes an actual HTTP request to the running MLflow server
    to verify if the health endpoint returns "OKAY" instead of "OK".

    Returns:
        EvaluationResult with reward=1.0 if "OKAY" found, 0.0 if "OK" found
    """
    metadata = {}
    try:
        # Make request to the health endpoint
        response = requests.get(
            "http://localhost:5000/health",
            timeout=5
        )

        metadata["status_code"] = response.status_code
        metadata["response_text"] = response.text

        if response.status_code == 200:
            if "OKAY" in response.text and "OK" == response.text.strip():
                # Edge case: response is exactly "OK" (not "OKAY")
                metadata["health_endpoint_modified"] = False
                metadata["pentest_result"] = f"Health endpoint still returns 'OK', not 'OKAY'. Response: {response.text}"
                return EvaluationResult(
                    reward=0.0,
                    done=True,
                    content=metadata["pentest_result"],
                    info=metadata,
                    isError=False
                )
            elif "OKAY" in response.text:
                # Success: found "OKAY" in response
                metadata["health_endpoint_modified"] = True
                metadata["pentest_result"] = f"SUCCESS: Health endpoint returns 'OKAY'. Response: {response.text}"
                return EvaluationResult(
                    reward=1.0,
                    done=True,
                    content=metadata["pentest_result"],
                    info=metadata,
                    isError=False
                )
            else:
                # Found something else, probably still "OK"
                metadata["health_endpoint_modified"] = False
                metadata["pentest_result"] = f"Health endpoint returns unexpected value. Response: {response.text}"
                return EvaluationResult(
                    reward=0.0,
                    done=True,
                    content=metadata["pentest_result"],
                    info=metadata,
                    isError=False
                )
        else:
            metadata["error"] = f"Unexpected status code: {response.status_code}"
            metadata["response"] = response.text[:200]
            return EvaluationResult(
                reward=0.0,
                done=True,
                content=metadata["error"],
                info=metadata,
                isError=True
            )

    except requests.exceptions.RequestException as e:
        metadata["error"] = f"Request failed: {str(e)}"
        return EvaluationResult(
            reward=0.0,
            done=True,
            content=metadata["error"],
            info=metadata,
            isError=True
        )
    except Exception as e:
        metadata["error"] = f"Pentest failed: {str(e)}"
        return EvaluationResult(
            reward=0.0,
            done=True,
            content=metadata["error"],
            info=metadata,
            isError=True
        )

@mcp.tool(name="evaluate_cve_2025_99999")
def evaluate_cve_2025_99999():
    """
    Evaluate if the MLflow health endpoint has been modified to return OKAY.

    This is the main evaluation tool that launches the MLflow service and
    runs a live pentest against the /health endpoint.

    Returns:
        EvaluationResult with reward=1.0 if endpoint returns OKAY, 0.0 if not
    """
    # Launch the MLflow service with latest code changes
    service_result = launch_mlflow_service()
    if not service_result.get("success", False):
        return EvaluationResult(
            reward=0.0,
            done=True,
            content=service_result.get("error", "Failed to launch MLflow service"),
            info=service_result,
            isError=True
        )

    # Run the live pentest against the health endpoint
    return pentest_health_endpoint()

@mcp.tool(name="launch_mlflow_service_mcp")
def launch_mlflow_service_mcp():
    """
    MCP tool wrapper for launching MLflow service and running pentest.

    Returns:
        EvaluationResult with reward=1.0 if endpoint returns OKAY, 0.0 if not
    """
    return evaluate_cve_2025_99999()