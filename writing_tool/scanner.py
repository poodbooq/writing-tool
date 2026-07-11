from __future__ import annotations

from pathlib import Path


def _should_skip(entry: Path, root: Path, ignore_dirs: set[str]) -> bool:
    try:
        rel = entry.relative_to(root)
    except ValueError:
        return True
    parts = rel.parts
    return any(p in ignore_dirs for p in parts)


def scan_md_files(
    root: str | Path,
    extensions: set[str] | None = None,
    ignore_dirs: set[str] | None = None,
) -> list[dict[str, object]]:
    if extensions is None:
        extensions = {".md", ".mdx"}
    if ignore_dirs is None:
        ignore_dirs = {".wt", ".agents"}
    root = Path(root)
    if not root.is_dir():
        return []
    results: list[dict[str, object]] = []
    for entry in root.rglob("*"):
        if _should_skip(entry, root, ignore_dirs):
            continue
        if entry.suffix.lower() in extensions:
            stat = entry.stat()
            results.append({
                "path": str(entry.relative_to(root)),
                "abspath": str(entry.resolve()),
                "mtime": stat.st_mtime,
            })
    results.sort(key=lambda r: r["path"])  # type: ignore[return-value, arg-type]
    return results
