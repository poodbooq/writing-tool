import tempfile
from pathlib import Path

from writing_tool.scanner import scan_md_files


def test_scan_empty_directory() -> None:
    with tempfile.TemporaryDirectory() as d:
        results = scan_md_files(d)
        assert results == []


def test_scan_md_files() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "a.md").write_text("hello", encoding="utf-8")
        Path(d, "sub").mkdir()
        Path(d, "sub", "b.md").write_text("world", encoding="utf-8")
        Path(d, "c.txt").write_text("no", encoding="utf-8")

        results = scan_md_files(d)
        assert len(results) == 2
        paths = [r["path"] for r in results]
        assert "a.md" in paths
        assert "sub/b.md" in paths
        assert "c.txt" not in paths


def test_scan_mdx() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "doc.mdx").write_text("", encoding="utf-8")
        results = scan_md_files(d, extensions={".mdx"})
        assert len(results) == 1


def test_scan_mtime() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d, "f.md")
        p.write_text("x", encoding="utf-8")
        stat = p.stat()
        results = scan_md_files(d)
        assert results[0]["mtime"] == stat.st_mtime


def test_scan_abspath() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "f.md").write_text("x", encoding="utf-8")
        results = scan_md_files(d)
        assert Path(results[0]["abspath"]).is_absolute()


def test_scan_non_existent_root() -> None:
    results = scan_md_files("/nonexistent/path/xyz")
    assert results == []


def test_scan_ignores_wt_dir() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "note.md").write_text("", encoding="utf-8")
        Path(d, ".wt").mkdir()
        Path(d, ".wt", "config.toml").write_text("", encoding="utf-8")
        Path(d, ".wt", "secret.md").write_text("", encoding="utf-8")
        results = scan_md_files(d)
        paths = [r["path"] for r in results]
        assert "note.md" in paths
        assert ".wt/secret.md" not in paths
        assert len(results) == 1


def test_scan_ignores_nested_wt() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "a.md").write_text("", encoding="utf-8")
        sub = Path(d, "chapters")
        sub.mkdir()
        (sub / "b.md").write_text("", encoding="utf-8")
        wt = Path(d, "chapters", ".wt")
        wt.mkdir()
        (wt / "c.md").write_text("", encoding="utf-8")
        results = scan_md_files(d)
        paths = [r["path"] for r in results]
        assert "a.md" in paths
        assert "chapters/b.md" in paths
        assert "chapters/.wt/c.md" not in paths


def test_scan_sorts_by_path() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "z.md").write_text("", encoding="utf-8")
        Path(d, "a.md").write_text("", encoding="utf-8")
        Path(d, "m.md").write_text("", encoding="utf-8")
        results = scan_md_files(d)
        paths = [r["path"] for r in results]
        assert paths == sorted(paths)
