#!/usr/bin/env python3
"""Run the one-day test task"""

import json
import subprocess
import sys

with open("tasks.json") as f:
    tasks = json.load(f)
    one_day_task = tasks[1]  # Second task

with open("single_task.json", "w") as f:
    json.dump([one_day_task], f, indent=2)

print(f"Running task: {one_day_task['id']}")
print(f"Info level: {one_day_task['info_level']}")
print(f"Prompt: {one_day_task['prompt']}\n")

cmd = [
    ".venv/bin/hud-python", "eval", "single_task.json", "claude",
    "--model", "claude-opus-4-1-20250805",
    "--max-steps", "100"
]

print(f"Executing: {' '.join(cmd)}\n")
result = subprocess.run(cmd)
sys.exit(result.returncode)
