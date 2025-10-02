#!/usr/bin/env python3
"""Test script to verify MLflow restart functionality."""

import asyncio
import sys
sys.path.insert(0, '/home/evan/projects/spar/mlfow-hud/src')

# Mock the MCP server components for testing
from unittest.mock import MagicMock
from mcp.types import TextContent

# Mock the MCPServer class
class MockMCPServer:
    def __init__(self, name):
        self.name = name
        self.tools = {}
    
    def tool(self, name=None):
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            return func
        return decorator
    
    def add_tool(self, tool):
        pass

# Create mock server instance
mcp = MockMCPServer(name="test-server")

# Import and test the restart function
import logging
import os
import subprocess
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)

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
        # Find and kill existing MLflow processes
        result = subprocess.run(
            ["pkill", "-f", "mlflow server"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logging.info("Successfully killed existing MLflow server")
        else:
            logging.info("No existing MLflow server process found or failed to kill")
        
        # Give it a moment to clean up
        time.sleep(2)
        
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

async def test_restart():
    """Test the restart functionality."""
    print("Testing MLflow restart functionality...")
    print("Note: This test should be run inside the Docker container where MLflow is installed.")
    
    # Test the restart function
    result = await restart_mlflow()
    
    if result:
        print(f"Result: {result[0].text}")
        if "successfully" in result[0].text:
            print("✓ Restart test passed!")
            return True
        else:
            print("✗ Restart test failed!")
            return False
    else:
        print("✗ No result from restart function")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_restart())
    sys.exit(0 if success else 1)