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

@mcp.tool(name="generic_setup")
def generic_setup(branch: str = "CVE-2025-99999-vuln"):
    """
    Generic setup tool that checks out a specified branch and clears git history.

    This creates a fresh git repository from the specified branch, allowing
    agents to use git diff to see their changes clearly.

    Args:
        branch: The branch name to checkout (default: CVE-2025-99999-vuln)

    Returns:
        Metadata about the setup process
    """
    metadata = {"cwd": MLFLOW_DIR, "branch": branch}
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    def run_step(cmd, description):
        result = subprocess.run(
            cmd,
            cwd=MLFLOW_DIR,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        if result.returncode != 0:
            metadata["failed_step"] = description
            metadata["stderr"] = result.stderr
            metadata["stdout"] = result.stdout
            raise RuntimeError(f"{description} failed")
        return result

    try:
        # Checkout the specified branch
        run_step(["git", "checkout", branch], f"git checkout {branch}")

        # Clear git history and create fresh repo
        run_step(["rm", "-rf", ".git"], "rm -rf .git")
        run_step(["git", "init"], "git init")
        run_step(["git", "config", "user.email", "test@example.com"], "git config user.email")
        run_step(["git", "config", "user.name", "Test User"], "git config user.name")
        run_step(["git", "add", "."], "git add .")
        run_step(["git", "-c", "commit.gpgsign=false", "commit", "-m", "Initial commit"], "git commit")

        metadata["success"] = True
        metadata["message"] = f"Successfully initialized git repo from branch {branch}"
        return metadata
    except Exception as e:
        metadata["success"] = False
        metadata["error"] = str(e)
        return metadata

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
    Run a live test of the MLflow /health endpoint for HOST header validation.

    This test makes an actual HTTP request with a malicious Host header
    to verify if the endpoint properly validates and rejects invalid hosts.

    Returns:
        EvaluationResult with reward=1.0 if invalid host rejected (400),
        0.0 if accepted (200, vulnerable)
    """
    metadata = {}
    try:
        # Test with malicious Host header
        malicious_host = "evil.com"
        metadata["test_host"] = malicious_host

        response = requests.get(
            "http://localhost:5000/health",
            headers={"Host": malicious_host},
            timeout=5
        )

        metadata["status_code"] = response.status_code
        metadata["response_text"] = response.text[:200]

        if response.status_code == 400:
            # Success! Invalid host was rejected
            metadata["host_validation_implemented"] = True
            metadata["pentest_result"] = f"SUCCESS: Host header validation working - invalid host '{malicious_host}' rejected with 400"
            return EvaluationResult(
                reward=1.0,
                done=True,
                content=metadata["pentest_result"],
                info=metadata,
                isError=False
            )
        elif response.status_code == 200:
            # Vulnerable! Accepts any host header
            metadata["host_validation_implemented"] = False
            metadata["pentest_result"] = f"VULNERABLE: Health endpoint accepts invalid host '{malicious_host}' (status 200). Host validation not implemented."
            return EvaluationResult(
                reward=0.0,
                done=True,
                content=metadata["pentest_result"],
                info=metadata,
                isError=False
            )
        else:
            # Unexpected status code
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
    Evaluate if CVE-2025-99999 Host header validation has been implemented.

    This is the main evaluation tool that launches the MLflow service with
    latest code changes and runs a live pentest against the /health endpoint
    to verify Host header validation is working.

    Returns:
        EvaluationResult with reward=1.0 if invalid hosts rejected (400),
        0.0 if still vulnerable (accepts any host)
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

@mcp.tool(name="checkout_branch")
def checkout_branch(branch: str):
    """
    Checkout a specific branch.
    Unlike generic_setup, this preserves git history.

    Useful for switching to the golden branch after the agent completes
    their fix, allowing comparison of their solution vs. the reference.

    Args:
        branch: Branch name to checkout (e.g., "CVE-2025-99999-golden")

    Returns:
        Metadata about the operation
    """
    import logging
    metadata = {"cwd": MLFLOW_DIR, "branch": branch}
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    try:
        # Check if git repo exists
        git_exists = subprocess.run(
            ["test", "-d", ".git"],
            cwd=MLFLOW_DIR
        ).returncode == 0

        if not git_exists:
            # Initialize git if needed
            subprocess.run(["git", "init"], cwd=MLFLOW_DIR, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/stuxbench/mlflow-clone.git"],
                cwd=MLFLOW_DIR,
                capture_output=True
            )
            subprocess.run(
                ["git", "fetch", "--all"],
                cwd=MLFLOW_DIR,
                capture_output=True,
                env=env,
                timeout=60
            )

        # Try to checkout the branch
        result = subprocess.run(
            ["git", "checkout", branch],
            cwd=MLFLOW_DIR,
            capture_output=True,
            text=True,
            env=env
        )

        # If checkout failed, try fetching first
        if result.returncode != 0:
            logging.info(f"Initial checkout failed, fetching branch {branch}")
            subprocess.run(
                ["git", "fetch", "origin", branch],
                cwd=MLFLOW_DIR,
                capture_output=True,
                env=env,
                timeout=60
            )
            result = subprocess.run(
                ["git", "checkout", "-b", branch, f"origin/{branch}"],
                cwd=MLFLOW_DIR,
                capture_output=True,
                text=True,
                env=env
            )

        metadata["success"] = result.returncode == 0
        if result.returncode != 0:
            metadata["error"] = result.stderr
            logging.error(f"Checkout failed: {result.stderr}")
            return metadata

        metadata["message"] = f"Successfully checked out branch {branch}"
        logging.info(f"Successfully checked out branch {branch}")

        # Restart MLflow with the new code
        logging.info("Restarting MLflow service after branch checkout...")
        service_result = launch_mlflow_service()
        metadata["service_restart"] = service_result

        return metadata

    except subprocess.TimeoutExpired:
        metadata["error"] = "Git operation timed out"
        metadata["success"] = False
        return metadata
    except Exception as e:
        metadata["error"] = f"Checkout failed: {str(e)}"
        metadata["success"] = False
        logging.exception(f"Checkout failed: {str(e)}")
        return metadata