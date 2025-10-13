#!/usr/bin/env python3
"""
Alternative test runner that uses docker exec to call the run_unit_tests function directly.

This bypasses the MCP HTTP layer and calls the Python function inside the container directly.
Use this if the HTTP/MCP approach has issues with SSE or content negotiation.
"""

import subprocess
import json
import sys


def get_container_name():
    """Find the running mlfow-hud container."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=mlfow-hud:0.1.0", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        containers = result.stdout.strip().split('\n')
        if containers and containers[0]:
            return containers[0]

        # Fallback: try to find any container with mlfow-hud in the name
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        for name in result.stdout.strip().split('\n'):
            if "mlfow-hud" in name:
                return name

        return None
    except subprocess.CalledProcessError:
        return None


def run_unit_tests_docker(container_name):
    """Execute run_unit_tests inside the Docker container."""

    print("="*80)
    print(f"RUNNING UNIT TESTS IN CONTAINER: {container_name}")
    print("="*80)
    print("This may take 30+ minutes to complete...")
    print()

    # Python code to execute inside the container
    python_code = """
import sys
sys.path.insert(0, '/donotaccess')
from src.controller.cves.cve_2025_99999 import run_unit_tests
import json

result = run_unit_tests()
print(json.dumps(result, indent=2))
"""

    try:
        result = subprocess.run(
            [
                "docker", "exec", container_name,
                "python3", "-c", python_code
            ],
            capture_output=True,
            text=True,
            timeout=2000  # 30+ minutes
        )

        if result.returncode != 0:
            print("ERROR: Command failed with non-zero exit code")
            print("\nSTDERR:")
            print(result.stderr)
            print("\nSTDOUT:")
            print(result.stdout)
            return None

        # Parse the JSON output
        try:
            test_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON output: {e}")
            print("\nRaw output:")
            print(result.stdout)
            return None

        # Pretty print the results
        print("\n" + "="*80)
        print("TEST RESULTS")
        print("="*80)

        print(f"\nSummary: {test_data.get('summary', 'No summary available')}")
        print(f"Overall Success: {test_data.get('overall_success', False)}")
        print()

        # Print each stage
        if "stages" in test_data:
            for i, stage in enumerate(test_data["stages"], 1):
                print(f"\n{'-'*80}")
                print(f"Stage {i}: {stage.get('name', 'Unknown')}")
                print(f"{'-'*80}")
                print(f"Command: {stage.get('command', 'N/A')}")
                print(f"Success: {stage.get('success', False)}")
                print(f"Return Code: {stage.get('returncode', 'N/A')}")

                if "error" in stage:
                    print(f"\nError: {stage['error']}")

                if stage.get("stdout"):
                    print(f"\nStdout (last 500 chars):")
                    print(stage["stdout"][-500:])

                if stage.get("stderr"):
                    print(f"\nStderr (last 500 chars):")
                    print(stage["stderr"][-500:])

        print(f"\n{'='*80}")
        print("FULL RESULT JSON")
        print(f"{'='*80}")
        print(json.dumps(test_data, indent=2))

        return test_data

    except subprocess.TimeoutExpired:
        print("\nERROR: Command timed out after 2000 seconds")
        print("The tests may still be running in the container.")
        return None
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    print("MLflow Unit Test Runner (Docker Exec Method)")
    print("="*80)
    print()

    # Find the container
    print("Looking for mlfow-hud container...")
    container_name = get_container_name()

    if not container_name:
        print("ERROR: Could not find running mlfow-hud container")
        print("\nPlease ensure the container is running with: hud dev --docker")
        print("\nOr specify container name manually:")
        print("  docker ps  # to list containers")
        print(f"  docker exec <container-name> python3 -c '<python code>'")
        sys.exit(1)

    print(f"Found container: {container_name}")
    print()

    # Run the tests
    result = run_unit_tests_docker(container_name)

    if result is None:
        print("\n✗ Test execution failed.")
        sys.exit(1)

    # Check if tests passed
    if result.get("overall_success"):
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
