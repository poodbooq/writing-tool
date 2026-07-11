#!/usr/bin/env python3
"""
Read a markdown file and return structured analysis WITHOUT writing to the DB.

This is a dry-run: the LLM analyzes the text but nothing is saved.

Usage:
    analyze-file.py <file.md>

Output:
    JSON with entities and relationships found by the LLM

Exit code:
    0 on success, 1 on error
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from writing_tool.extractor import extract as llm_extract
from writing_tool.cli import _get_config
from writing_tool.config import get_model


def main() -> None:
    if not sys.argv[1:]:
        print("Usage: analyze-file.py <file.md>", file=sys.stderr)
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(json.dumps({
            "status": "error",
            "message": f"File not found: {file_path}",
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    try:
        cfg = _get_config()
        model = get_model(cfg)
    except Exception:
        model = "gpt-4o-mini"

    text = file_path.read_text(encoding="utf-8")
    result = llm_extract(text, model=model)

    output = {
        "status": "ok",
        "file": str(file_path),
        "entities": result.get("entities", []),
        "relationships": result.get("relationships", []),
        "entities_count": len(result.get("entities", [])),
        "relationships_count": len(result.get("relationships", [])),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
