#!/usr/bin/env python3
"""
Analyze a markdown file via wt CLI: extract entities and relationships.

Usage:
    extract.py <file.md> [--yes]

Options:
    --yes    Auto-approve all extractions (skip $EDITOR)

Output:
    JSON with keys: file, entities_count, relationships_count, status

Exit code:
    0 on success, 1 on error
"""

import json
import subprocess
import sys
from typing import Any


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--yes"]
    yes_flag = "--yes" in sys.argv

    if not args:
        print("Usage: extract.py <file.md> [--yes]", file=sys.stderr)
        sys.exit(1)

    file_path = args[0]
    cmd = ["wt", "extract", file_path]
    if yes_flag:
        cmd.append("--yes")

    result = subprocess.run(cmd, capture_output=True, text=True)

    output: dict[str, Any] = {
        "file": file_path,
        "status": "ok" if result.returncode == 0 else "error",
        "message": result.stdout.strip().split("\n")[-1] if result.stdout else "",
        "stderr": result.stderr.strip(),
    }

    # Parse entity/relationship counts from output
    for line in result.stdout.split("\n"):
        if "Found" in line and "entities" in line:
            parts = line.strip().split()
            try:
                output["entities_count"] = int(parts[1])
                output["relationships_count"] = int(parts[3])
            except (IndexError, ValueError):
                pass

    print(json.dumps(output, indent=2, ensure_ascii=False))
    sys.exit(0 if result.returncode == 0 else 1)


if __name__ == "__main__":
    main()
