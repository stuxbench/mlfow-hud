"""Bash command execution tool for Stuxbench."""

import asyncio
import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BashTool:
    """Execute bash commands for security testing and code analysis."""
    
    def __init__(self, working_dir: str = "/build/minio"):
        self.working_dir = working_dir
    
    async def __call__(
        self,
        command: str,
        timeout: int = 30,
        cwd: str = None
    ) -> Dict[str, Any]:
        """
        Execute a bash command.
        
        Args:
            command: The bash command to execute
            timeout: Timeout in seconds
            cwd: Working directory (defaults to self.working_dir)
            
        Returns:
            Dictionary with stdout, stderr, and return code
        """
        working_directory = cwd or self.working_dir
        
        logger.info(f"Executing command: {command[:100]}...")
        
        try:
            # Run command asynchronously
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return {
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "returncode": -1,
                    "timed_out": True
                }
            
            return {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode,
                "timed_out": False
            }
            
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "error": True
            }