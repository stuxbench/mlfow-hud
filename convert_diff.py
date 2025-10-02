with open("golden_diff.txt", "r") as f:
    diff = f.read()

import json
escaped = json.dumps(diff.strip() + "\n")   # includes final newline
print(escaped[1:-1])  # drop the surrounding quotes if you need a bare string
