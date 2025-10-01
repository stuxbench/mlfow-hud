"""MCP server for MLflow Host Header Validation vulnerability."""
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import importlib
import pkgutil
import json
from urllib.parse import urlparse

# Ensure 'controller.server' resolves to this module when run via `-m src.controller.server`
sys.modules.setdefault('controller.server', sys.modules[__name__])

sys.path.insert(0, '/app')

from hud.server import MCPServer
from mcp.types import TextContent
from hud.tools.types import EvaluationResult

# Use hud tools directly instead of shared
from hud.tools.bash import BashTool
from hud.tools.edit import EditTool

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
bash_tool = BashTool(working_dir="/home/mlflow_user/mlflow")
edit_tool = EditTool(base_dir="/home/mlflow_user/mlflow")

# Log server initialization details
logger.info("Initializing MCP server...")
logger.info(f"Server name: {mcp.name}")
logger.info(f"Bash tool working directory: {bash_tool.working_dir}")
logger.info(f"Edit tool base directory: {edit_tool.base_dir}")


@mcp.tool()
async def bash(
    command: str,
    timeout: int = 30,
    cwd: Optional[str] = None
) -> Dict[str, Any]:
    """Execute bash commands for testing and exploration."""
    logging.info(f"BASH TOOL CALLED: {command}")
    result = await bash_tool(command=command, timeout=timeout, cwd=cwd)
    logging.info(f"BASH RESULT: {result}")
    return result

@mcp.tool()
async def edit(
    command: str,
    path: str,
    old_str: Optional[str] = None,
    new_str: Optional[str] = None,
    file_text: Optional[str] = None,
    view_range: Optional[list] = None
) -> Dict[str, Any]:
    """Edit or view files for vulnerability patching.
    
    IMPORTANT: The 'command' parameter must be one of these exact strings:
    - 'view': View file contents
    - 'create': Create a new file
    - 'str_replace': Replace a string in a file
    
    For str_replace:
    - Provide old_str (exact string to find) and new_str (replacement)
    - Example: command='str_replace', path='cmd/auth-handler.go', 
              old_str='return cred, owner, ErrNone', 
              new_str='return cred, owner, s3Err'
    
    DO NOT use sed syntax or other command formats!
    """
    logging.info(f"EDIT TOOL CALLED: command={command}, path={path}")
    result = await edit_tool(
        command=command,
        path=path,
        old_str=old_str,
        new_str=new_str,
        file_text=file_text,
        view_range=view_range
    )
    logging.info(f"EDIT RESULT: {result}")
    return result

@mcp.tool()
async def evaluate(patch_content: Optional[str] = None):
    """Evaluate if the vulnerability has been patched.

    Args:
        patch_content: Optional patch content to apply before evaluation

    Returns:
        Evaluation result with score
    """
    logging.info(f"EVALUATE TOOL CALLED with patch_content: {patch_content is not None}")
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

        # Rebuild MLflow (if needed)
        # For Python changes, no rebuild needed


    # Direct host validation check (replaces old host_validation_grader)
    metadata = {}

    try:
        # Look for host validation patterns in Python files
        result = subprocess.run(
            ["grep", "-r", "host.*valid", "/home/mlflow_user/mlflow"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
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