from __future__ import annotations

import os
import tempfile
from pathlib import Path

from click.testing import CliRunner

from writing_tool.cli import cli


def _run(*args: str) -> str:
    runner = CliRunner()
    result = runner.invoke(cli, args, catch_exceptions=False)
    return result.output


class TestInit:
    def test_init_creates_wt_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            out = _run("init")
            assert "Initialized" in out
            assert (Path(d) / ".wt").is_dir()
            assert (Path(d) / ".wt" / "writing.db").exists()
            assert (Path(d) / ".wt" / "config.toml").exists()

    def test_init_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("init")
            assert "already exists" in out

    def test_init_with_skill(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            out = _run("init", "--skill")
            assert "Installed skill" in out
            skill_dir = Path(d) / ".agents" / "skills" / "writing-tool"
            assert skill_dir.is_dir()
            assert (skill_dir / "SKILL.md").exists()
            assert (skill_dir / "scripts" / "extract.py").exists()
            assert (skill_dir / "references" / "COMMANDS.md").exists()


class TestInstallSkill:
    def test_install_skill_creates_agents_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            out = _run("install-skill")
            assert "Installed skill" in out
            assert (Path(d) / ".agents" / "skills" / "writing-tool" / "SKILL.md").exists()

    def test_install_skill_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("install-skill")
            out = _run("install-skill")
            assert "already exists" in out

    def test_install_skill_with_force(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("install-skill")
            out = _run("install-skill", "--force")
            assert "Installed skill" in out


class TestInitFailure:
    def test_command_without_init_fails(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            out = _run("stats")
            assert "No .wt/ directory found" in out

    def test_extract_without_init_fails(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            out = _run("extract", "foo.md")
            assert "No .wt/ directory found" in out


class TestStats:
    def test_stats_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("stats")
            assert "Nodes: 0" in out
            assert "Edges: 0" in out


class TestShow:
    def test_show_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("show", "Nonexistent")
            assert "No entity matching" in out

    def test_show_with_json(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("show", "Nonexistent", "--json")
            assert "No entity matching" in out


class TestGraph:
    def test_graph_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("graph")
            assert "(empty)" in out

    def test_graph_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("graph", "Nonexistent")
            assert "No entity matching" in out


class TestExport:
    def test_export_json(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            path = Path(d, "out.json")
            out = _run("export", "--format", "json", str(path))
            assert "Exported" in out
            assert path.exists()

    def test_export_graphml(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("export", "--format", "graphml")
            assert "<?xml" in out
            assert "graphml" in out


class TestAddNode:
    def test_add_node(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("add-node", "--type", "character", "--label", "Макс", "--props", '{"age":30}')
            assert "Added node #1" in out


class TestAddEdge:
    def test_add_edge(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            _run("add-node", "--type", "character", "--label", "A")
            _run("add-node", "--type", "character", "--label", "B")
            out = _run("add-edge", "--source", "1", "--target", "2", "--label", "loves")
            assert "Added edge #1" in out


class TestQuery:
    def test_query_requires_input(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["query"], catch_exceptions=False)
        assert "Usage:" in result.output


class TestServe:
    def test_serve_imports(self) -> None:
        from writing_tool.server import create_app
        from writing_tool.store import Store
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            s = Store(os.path.join(d, "test.db"))
            app = create_app(s)
            with app.test_client() as c:
                resp = c.get("/api/stats")
                assert resp.status_code == 200
                assert resp.json["nodes"] == 0


class TestExtract:
    def test_extract_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("extract", "nonexistent.md")
            assert "File not found" in out

    def test_extract_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("extract")
            assert out == ""


class TestReindex:
    def test_reindex_no_changes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            _run("init")
            out = _run("reindex")
            assert "No changed files" in out
