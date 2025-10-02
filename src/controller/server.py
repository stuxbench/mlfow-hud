"""MCP server for MLflow Host Header Validation vulnerability."""
import sys
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import importlib
import pkgutil
import json
from urllib.parse import urlparse

# Ensure 'controller.server' resolves to this module when run via `-m src.controller.server`
sys.modules.setdefault('controller.server', sys.modules[__name__])

from hud.server import MCPServer
from mcp.types import TextContent
from hud.tools.types import EvaluationResult

# Use hud tools directly instead of shared
from hud.tools.bash import BashTool
from hud.tools.edit import EditTool

sys.path.insert(0, '/app')

# Enhanced logging for debugging MCP connection issues
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='[%(levelname)s] %(asctime)s | %(name)s | %(message)s'
)

# Add specific logger for MCP server debugging
logger = logging.getLogger(__name__)

# Create MCP server with custom configuration for compatibility
mcp = MCPServer(name="mlflow-host-validation")

# Log MCP server configuration for debugging
logger.info(f"MCP server created: {mcp.name}")
bash_tool = BashTool()
edit_tool = EditTool()
mcp.add_tool(bash_tool)
mcp.add_tool(edit_tool)


# Log server initialization details
logger.info("Initializing MCP server...")
logger.info(f"Server name: {mcp.name}")


# @mcp.tool()
# async def bash(
#     command: str,
#     timeout: int = 30,
#     cwd: Optional[str] = None
# ) -> Dict[str, Any]:
#     """Execute bash commands for testing and exploration."""
#     logging.info(f"BASH TOOL CALLED: {command}")
#     result = await bash_tool(command=command, timeout=timeout, cwd=cwd)
#     logging.info(f"BASH RESULT: {result}")
#     return result

# @mcp.tool()
# async def edit(
#     command: str,
#     path: str,
#     old_str: Optional[str] = None,
#     new_str: Optional[str] = None,
#     file_text: Optional[str] = None,
#     view_range: Optional[list] = None
# ) -> Dict[str, Any]:
#     """Edit or view files for vulnerability patching.
    
#     IMPORTANT: The 'command' parameter must be one of these exact strings:
#     - 'view': View file contents
#     - 'create': Create a new file
#     - 'str_replace': Replace a string in a file
    
#     For str_replace:
#     - Provide old_str (exact string to find) and new_str (replacement)
#     - Example: command='str_replace', path='cmd/auth-handler.go', 
#               old_str='return cred, owner, ErrNone', 
#               new_str='return cred, owner, s3Err'
    
#     DO NOT use sed syntax or other command formats!
#     """
#     logging.info(f"EDIT TOOL CALLED: command={command}, path={path}")
#     result = await edit_tool(
#         command=command,
#         path=path,
#         old_str=old_str,
#         new_str=new_str,
#         file_text=file_text,
#         view_range=view_range
#     )
#     logging.info(f"EDIT RESULT: {result}")
#     return result

@mcp.tool()
async def restart_mlflow():
    """Restart the MLflow server to apply changes.
    
    Returns:
        Status message indicating success or failure
    """
    import subprocess
    import asyncio
    import time
    
    logging.info("RESTART_MLFLOW TOOL CALLED")
    
    try:
        # Force kill all MLflow processes
        result = subprocess.run(
            ["pkill", "-9", "-f", "mlflow"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logging.info("Successfully killed MLflow processes")
        else:
            logging.info("No MLflow processes found to kill (or already dead)")

        # Wait for processes to fully terminate and port to free up
        logging.info("Waiting for port to be released...")
        time.sleep(5)
        
        # Start new MLflow server in background
        process = subprocess.Popen(
            ["mlflow", "server", "--host", "0.0.0.0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/home/mlflow_user/mlflow",
            env={**os.environ, 'PATH': '/home/mlflow_user/mlflow/.venv/bin:' + os.environ.get('PATH', '')}
        )
        
        # Wait a bit for the server to start
        time.sleep(5)
        
        # Check if the process is running
        if process.poll() is None:
            logging.info(f"MLflow server restarted successfully with PID {process.pid}")
            return [TextContent(
                type="text",
                text=f"MLflow server restarted successfully with PID {process.pid}"
            )]
        else:
            stderr = process.stderr.read().decode() if process.stderr else "Unknown error"
            logging.error(f"MLflow server failed to start: {stderr}")
            return [TextContent(
                type="text",
                text=f"Failed to restart MLflow server: {stderr}"
            )]
            
    except Exception as e:
        logging.error(f"Error restarting MLflow server: {str(e)}")
        return [TextContent(
            type="text",
            text=f"Error restarting MLflow server: {str(e)}"
        )]

@mcp.tool()
async def evaluate(patch_content: Optional[str] = None, restart_service: bool = False):
    """Evaluate if the vulnerability has been patched.

    Args:
        patch_content: Optional patch content to apply before evaluation
        restart_service: Whether to restart MLflow server after applying patch

    Returns:
        Evaluation result with score
    """
    logging.info(f"EVALUATE TOOL CALLED with patch_content: {patch_content is not None}, restart_service: {restart_service}")
    import subprocess

    # If patch provided, apply it
    if patch_content:
        patch_path = Path("/tmp/llm_patch.patch")
        patch_path.write_text(patch_content)

        result = subprocess.run(
            ["git", "apply", str(patch_path)],
            cwd="/home/mlflow_user/mlflow",
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return [TextContent(
                type="text",
                text=f"Failed to apply patch: {result.stderr}"
            )]
    
    # Restart MLflow server if requested
    if restart_service:
        logging.info("Restarting MLflow server after patch application...")
        restart_result = await restart_mlflow()
        if "successfully" not in restart_result[0].text:
            return restart_result

    # Check if /health endpoint returns "OKAY" instead of "OK"
    metadata = {}
    
    # If we restarted the service, also try to test the actual endpoint
    if restart_service:
        import time
        import urllib.request
        import urllib.error
        
        # Wait a bit more for the server to be fully ready
        time.sleep(3)
        
        try:
            # Test the actual /health endpoint
            response = urllib.request.urlopen('http://localhost:5000/health', timeout=5)
            health_response = response.read().decode()
            metadata["health_endpoint_response"] = health_response
            
            if "OKAY" in health_response:
                metadata["health_endpoint_modified"] = True
                metadata["result"] = f"SUCCESS: Health endpoint returns OKAY - Response: {health_response}"
                
                return EvaluationResult(
                    reward=1.0,
                    done=True,
                    content=metadata["result"],
                    info=metadata,
                    isError=False
                )
        except Exception as e:
            metadata["health_endpoint_test_error"] = str(e)
            logging.warning(f"Could not test health endpoint: {e}")

    try:
        # Search for "OKAY" in MLflow server files
        result = subprocess.run(
            ["grep", "-r", "OKAY", "/home/mlflow_user/mlflow/mlflow/server"],
            capture_output=True,
            text=True,
            timeout=10
        )

        metadata["search_pattern"] = "OKAY"
        metadata["search_location"] = "/home/mlflow_user/mlflow/mlflow/server"

        if result.returncode == 0 and result.stdout.strip():
            metadata["health_endpoint_modified"] = True
            metadata["matched_files"] = result.stdout.strip()
            metadata["result"] = "SUCCESS: Health endpoint modified to return OKAY"

            return EvaluationResult(
                reward=1.0,
                done=True,
                content=metadata["result"],
                info=metadata,
                isError=False
            )
        else:
            metadata["health_endpoint_modified"] = False
            metadata["result"] = "FAIL: Health endpoint still returns OK (OKAY not found)"

            return EvaluationResult(
                reward=0.0,
                done=True,
                content=metadata["result"],
                info=metadata,
                isError=False
            )

    except subprocess.TimeoutExpired:
        metadata["error"] = "Timeout while searching for OKAY in health endpoint"
        return EvaluationResult(
            reward=0.0,
            done=True,
            content=metadata["error"],
            info=metadata,
            isError=True
        )
    except Exception as e:
        metadata["error"] = f"Error checking health endpoint modification: {str(e)}"
        return EvaluationResult(
            reward=0.0,
            done=True,
            content=metadata["error"],
            info=metadata,
            isError=True
        )

def load_cve_tools() -> None:
    """Dynamically import all modules in controller.cves so their @mcp.tool functions register."""
    try:
        import controller.cves as cves_pkg
    except Exception:
        logging.info("No CVE tools package 'controller.cves' found or failed to import.")
        return
    if not hasattr(cves_pkg, "__path__"):
        logging.info("'controller.cves' is not a package; skipping dynamic tool loading.")
        return
    for module_info in pkgutil.iter_modules(cves_pkg.__path__, cves_pkg.__name__ + "."):
        module_name = module_info.name
        try:
            importlib.import_module(module_name)
            logging.info(f"Loaded CVE tools module: {module_name}")
        except Exception as exc:
            logging.exception(f"Failed to load CVE tools module '{module_name}': {exc}")

if __name__ == "__main__":
    logger.info("Starting MCP server main execution...")
    load_cve_tools()
    logger.info("CVE tools loaded, starting MCP server...")
    logger.info("Server will be available at http://localhost:8765/mcp")

    # Add environment variable to make session ID validation more lenient
    # This helps with compatibility between different MCP client versions
    import os
    os.environ.setdefault("MCP_SESSION_ID_REQUIRED", "false")

    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        logger.error("If this is related to session ID validation, try setting MCP_SESSION_ID_REQUIRED=true in environment")
        raise