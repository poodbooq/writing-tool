#!/usr/bin/env python3
"""
Show an entity's properties and relationships as JSON.

Usage:
    show-entity.py <label> [--depth N]

Options:
    --depth N    Graph traversal depth (default: 1)

Output:
    JSON with root entity + graph of related entities and edges

Exit code:
    0 on success, 1 on error or not found
"""

import json
import subprocess
import sys


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--depth")]
    depth = 1

    for i, a in enumerate(sys.argv[1:]):
        if a == "--depth" and i + 2 < len(sys.argv):
            try:
                depth = int(sys.argv[i + 2])
            except ValueError:
                pass

    if not args:
        print("Usage: show-entity.py <label> [--depth N]", file=sys.stderr)
        sys.exit(1)

    label = args[0]
    cmd = ["wt", "show", label, "--json", "--depth", str(depth)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(json.dumps({
            "status": "not_found",
            "label": label,
            "error": result.stderr.strip(),
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    try:
        data = json.loads(result.stdout)
        data["status"] = "ok"
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(json.dumps({
            "status": "error",
            "label": label,
            "message": "Failed to parse wt output",
        }, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
