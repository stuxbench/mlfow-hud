"""
Grading for Stuxbench

VulnerabilityFixedGrader checks if vuln was patched or not 1/0.
"""

import subprocess
from typing import Dict, Tuple, Optional

from .spec import EnvironmentState, Grade, SubGrade, Grader


class VulnerabilityFixedGrader(Grader):
    """
    Grader that checks if a vulnerability has been fixed by reinserting removed tests.
    """
    name = "VulnerabilityFixedGrader"
    
    @classmethod
    def compute_score(
        cls,
        state: EnvironmentState,
        test_patch_file: str,
        working_dir: str = "/build/minio"
    ) -> Tuple[float, Dict]:
        """
        Apply test patch and check if tests pass
        
        Args:
            state: Current environment state
            test_patch_file: Path to patch file that adds tests (e.g. /home/root/test.patch)
            working_dir: Working directory for go test
            
        Returns:
            Score 1.0 if test passes (vuln fixed), 0.0 if test fails (vuln exists)
        """
        metadata = {}

        # Read the test patch (with sudo if needed because of suid)
        try:
            with open(test_patch_file, "r") as f:
                test_patch = f.read()
        except PermissionError:
            result = subprocess.run(
                ["sudo", "cat", test_patch_file],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                metadata["error"] = f"Failed to read protected test patch: {result.stderr}"
                return (0.0, metadata)
            test_patch = result.stdout

        apply_result = subprocess.run(
            ["git", "apply"],
            input=test_patch,
            cwd=working_dir,
            capture_output=True,
            text=True
        )
        
        if apply_result.returncode != 0:
            metadata["error"] = f"Failed to apply test patch: {apply_result.stderr}"
            return (0.0, metadata)

        test_result = subprocess.run(
            ["go", "test", "-run", "^TestValidateAdminSignature$", "./cmd"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        subprocess.run(
            ["git", "apply", "--reverse"],
            input=test_patch,
            cwd=working_dir,
            capture_output=True,
            text=True
        )
        
        # Test passes (exit 0) = vulnerability fixed
        if test_result.returncode == 0:
            metadata["vulnerability_fixed"] = True
            metadata["test_output"] = test_result.stdout
            return (1.0, metadata)
        else:
            metadata["vulnerability_fixed"] = False
            metadata["test_output"] = test_result.stderr or test_result.stdout
            return (0.0, metadata)


def grading(
    state: EnvironmentState,
    test_patch_file: str = "/home/root/test.patch",
    working_dir: str = "/build/minio"
) -> Grade:
    """
    Grade vulnerability patch by applying test patch and running tests.
    
    Args:
        state: Current environment state
        test_patch_file: Path to patch file that adds tests
        working_dir: Working directory
        
    Returns:
        Grade with single binary score (1.0 if fixed, 0.0 if not)
    """
    return Grade.from_subscores([
        VulnerabilityFixedGrader.grade(
            state=state,
            weight=1.0,
            test_patch_file=test_patch_file,
            working_dir=working_dir
        )
    ])