#!/usr/bin/env python3
"""
Ask a natural language question about the story graph.

Usage:
    query-graph.py <question>

The question can be anything like "Who is Maxim?" or
"What relationships does the forest have?".

Output:
    Plain text answer from the LLM

Exit code:
    0 on success, 1 on error
"""

import subprocess
import sys


def main() -> None:
    if not sys.argv[1:]:
        print("Usage: query-graph.py <question>", file=sys.stderr)
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    cmd = ["wt", "query", question]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)

    sys.exit(0 if result.returncode == 0 else 1)


if __name__ == "__main__":
    main()
