#!/usr/bin/env python3
"""Run the mock test task using hud-python eval"""

import json
import subprocess
import sys

with open("test_task.json") as f:
    test_task = json.load(f)[0]

print(f"Running task: {test_task['id']}")
print(f"Info level: {test_task['info_level']}") 
print(f"Prompt: {test_task['prompt']}\n")

cmd = [
    ".venv/bin/hud-python", "eval", "test_task.json", "claude",
    "--model", "claude-opus-4-1-20250805"
]

print(f"Executing: {' '.join(cmd)}\n")
result = subprocess.run(cmd)
sys.exit(result.returncode)