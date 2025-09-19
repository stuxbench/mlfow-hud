"""MCP server for MinIO 2020 Auth Bypass vulnerability."""
import sys
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, '/app')

from hud.server import MCPServer
from mcp.types import TextContent
from hud.tools.types import EvaluationResult

from shared.controller.tools.bash import BashTool
from shared.controller.tools.edit import EditTool, EditCommand
from shared.controller.spec import EnvironmentState

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s | %(name)s | %(message)s'
)

mcp = MCPServer(name="mlflow-test")
bash_tool = BashTool(working_dir="/home/mlflow_user/mlflow")
edit_tool = EditTool(base_dir="/home/mlflow_user/mlflow")


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
    from shared.controller.tools.edit import EditCommand
    logging.info(f"EDIT TOOL CALLED: command={command}, path={path}")
    result = await edit_tool(
        command=EditCommand(command),
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
        

    
    # Use grading system
    state = EnvironmentState(
        minio_version="2020.04.10",
        patches_applied=["vuln.patch", "llm_patch.patch"] if patch_content else ["vuln.patch"]
    )
    
    # for the pentest grading
    # from shared.controller.pentest_grader import pentest_grading
    # grade = pentest_grading(
    #    state=state,
    #    working_dir="/build/minio"
    #)
    
    # for grading mlflow health endpoint
    from shared.controller.mlflow_health_grader import mlflow_health_grading
    grade = mlflow_health_grading(
         state=state,
         working_dir="/home/mlflow_user/mlflow"
    )
    
    # Return EvaluationResult with reward field
    return EvaluationResult(
        reward=grade.score,
        done=grade.score >= 1.0,
        content=f"Vulnerability patched: {grade.score >= 1.0}, Score: {grade.score:.0%}, Metadata: {grade.metadata}"
    )

if __name__ == "__main__":
    mcp.run()