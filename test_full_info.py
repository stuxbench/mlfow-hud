#!/usr/bin/env python3
"""Run the full-info test task"""

import json
import subprocess
import sys

with open("tasks.json") as f:
    tasks = json.load(f)
    full_info_task = tasks[0]  # First task

with open("single_task.json", "w") as f:
    json.dump([full_info_task], f, indent=2)

print(f"Running task: {full_info_task['id']}")
print(f"Info level: {full_info_task['info_level']}")
print(f"Prompt: {full_info_task['prompt']}\n")

cmd = [
    ".venv/bin/hud-python", "eval", "single_task.json", "claude",
    "--model", "claude-opus-4-1-20250805"
]

print(f"Executing: {' '.join(cmd)}\n")
result = subprocess.run(cmd)
sys.exit(result.returncode)
