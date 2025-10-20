#!/usr/bin/env python3
"""Run the zero-day test task"""

import json
import subprocess
import sys

with open("tasks.json") as f:
    tasks = json.load(f)
    zero_day_task = tasks[2]  # Third task

with open("single_task.json", "w") as f:
    json.dump([zero_day_task], f, indent=2)

print(f"Running task: {zero_day_task['id']}")
print(f"Info level: {zero_day_task['info_level']}")
print(f"Prompt: {zero_day_task['prompt']}\n")

cmd = [
    ".venv/bin/hud-python", "eval", "single_task.json", "claude",
    "--model", "claude-opus-4-1-20250805",
    "--max-steps", "10"
]

print(f"Executing: {' '.join(cmd)}\n")
result = subprocess.run(cmd)
sys.exit(result.returncode)
