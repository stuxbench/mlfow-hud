"""
MLflow health endpoint grader for verifying the health endpoint returns "OKAY".
Checks if the /health endpoint response has been modified from "OK" to "OKAY".
"""

import os
import subprocess
import time
import requests
import json
from typing import Dict, Tuple

from .spec import EnvironmentState, Grade, SubGrade, Grader


class MLflowHealthGrader(Grader):
    """
    Grader to check if MLflow /health endpoint returns 'OKAY' instead of 'OK'.
    """
    name = "MLflowHealthGrader"
    
    @classmethod
    def compute_score(
        cls,
        state: EnvironmentState,
        working_dir: str = "/home/mlflow_user/mlflow"
    ) -> Tuple[float, Dict]:
        """
        Check if MLflow server files contain 'OKAY' instead of 'OK' for health endpoint.
        
        Returns:
            score 1.0 if files contain 'OKAY'
            score 0.0 if files still contain 'OK' or check fails
        """
        metadata = {}
        
        try:
            # Search for "OKAY" in MLflow server files
            result = subprocess.run([
                "grep", "-r", "-l", "OKAY", 
                os.path.join(working_dir, "mlflow/server"),
                os.path.join(working_dir, "build/lib/mlflow/server")
            ], capture_output=True, text=True, timeout=10)
            
            metadata["grep_returncode"] = result.returncode
            metadata["grep_stdout"] = result.stdout.strip()
            metadata["grep_stderr"] = result.stderr.strip()
            
            if result.returncode == 0 and result.stdout.strip():
                # Found "OKAY" in files
                metadata["result"] = "SUCCESS: Found 'OKAY' in MLflow server files"
                metadata["files_with_okay"] = result.stdout.strip().split('\n')
                return (1.0, metadata)
            else:
                # Check if we can find "OK" instead
                ok_result = subprocess.run([
                    "grep", "-r", "-l", '"OK"', 
                    os.path.join(working_dir, "mlflow/server"),
                    os.path.join(working_dir, "build/lib/mlflow/server")
                ], capture_output=True, text=True, timeout=10)
                
                if ok_result.returncode == 0 and ok_result.stdout.strip():
                    metadata["result"] = "FAIL: Still found 'OK' in MLflow server files, change not made"
                    metadata["files_with_ok"] = ok_result.stdout.strip().split('\n')
                else:
                    metadata["result"] = "FAIL: Could not find health endpoint response in files"
                return (0.0, metadata)
                
        except subprocess.TimeoutExpired:
            metadata["error"] = "Grep search timeout"
            return (0.0, metadata)
        except Exception as e:
            metadata["error"] = f"File check failed: {str(e)}"
            return (0.0, metadata)


def mlflow_health_grading(
    state: EnvironmentState,
    working_dir: str = "/home/mlflow_user/mlflow"
) -> Grade:
    """
    Grade the MLflow health endpoint modification task.
    """
    return Grade.from_subscores([
        MLflowHealthGrader.grade(
            state=state,
            weight=1.0,
            working_dir=working_dir
        )
    ])
