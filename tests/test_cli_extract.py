from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from writing_tool.cli import cli
from writing_tool.server import create_app
from writing_tool.store import Store


@patch("writing_tool.cli.llm_extract")
def test_extract_with_file(mock_llm: object) -> None:
    mock_llm.return_value = {  # type: ignore[assignment]
        "entities": [{"label": "Max", "type": "character", "props": {}}],
        "relationships": [],
    }
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        Path("scene.md").write_text("Max is a hero.", encoding="utf-8")
        out = runner.invoke(cli, ["extract", "scene.md", "--yes"]).output
        assert "Found 1 entities" in out
        assert "Applied" in out


@patch("writing_tool.cli.llm_extract")
@patch("writing_tool.interactive._edit_temp")
def test_extract_edit(mock_edit: object, mock_llm: object) -> None:
    mock_llm.return_value = {  # type: ignore[assignment]
        "entities": [{"label": "Max", "type": "character", "props": {}}],
        "relationships": [],
    }
    mock_edit.return_value = (  # type: ignore[assignment]
        "entities:\n  - label: Max\n    type: character\n    props: {}\nrelationships: []\n"
    )
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        Path("scene.md").write_text("Max is a hero.", encoding="utf-8")
        out = runner.invoke(cli, ["extract", "scene.md"]).output
        assert "Applied" in out


@patch("writing_tool.cli.llm_extract")
def test_reindex_with_changes(mock_llm: object) -> None:
    mock_llm.return_value = {  # type: ignore[assignment]
        "entities": [{"label": "Max", "type": "character", "props": {}}],
        "relationships": [],
    }
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        Path("scene.md").write_text("Max is a hero.", encoding="utf-8")
        out = runner.invoke(cli, ["reindex", "--yes"]).output
        assert "Found 1 changed file" in out


@patch("writing_tool.cli.llm_extract")
def test_extract_with_deep_flag(mock_llm: object) -> None:
    mock_llm.return_value = {  # type: ignore[assignment]
        "entities": [
            {"label": "Max", "type": "character", "props": {"role": "protagonist"}},
            {"label": "Fear", "type": "emotion", "props": {}},
        ],
        "relationships": [{"source": "Max", "target": "Fear", "label": "feels"}],
    }
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        Path("scene.md").write_text("Max is afraid.", encoding="utf-8")
        out = runner.invoke(cli, ["extract", "scene.md", "--yes", "--deep"]).output
        assert "Found 2 entities" in out
        # Verify deep=True was passed to llm_extract
        assert mock_llm.call_args[1]["deep"] is True


@patch("writing_tool.cli.llm_extract")
def test_reindex_with_deep_flag(mock_llm: object) -> None:
    mock_llm.return_value = {  # type: ignore[assignment]
        "entities": [{"label": "X", "type": "character", "props": {}}],
        "relationships": [],
    }
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        Path("scene.md").write_text("X exists.", encoding="utf-8")
        out = runner.invoke(cli, ["reindex", "--yes", "--deep"]).output
        assert "Found 1 changed file" in out
        assert mock_llm.call_args[1]["deep"] is True


def test_graph_with_label() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "Max"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "Eve"])
        runner.invoke(cli, ["add-edge", "--source", "1", "--target", "2", "--label", "loves"])
        out = runner.invoke(cli, ["graph", "Max", "--format", "ascii"]).output
        assert "Max" in out
        assert "Eve" in out
        assert "loves" in out


def test_graph_all_dot() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "A"])
        out = runner.invoke(cli, ["graph", "--format", "dot"]).output
        assert "digraph" in out


def test_export_stdout() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        out = runner.invoke(cli, ["export", "--format", "json"]).output
        assert '"nodes"' in out


def test_serve_api_graph() -> None:
    with tempfile.TemporaryDirectory() as d:
        s = Store(os.path.join(d, "test.db"))
        s.add_node("character", "Max", source_file="test.md", mtime=1.0)
        s.add_node("location", "Forest", source_file="test.md", mtime=1.0)
        s.add_edge(1, 2, "located_in")
        app = create_app(s)
        with app.test_client() as c:
            resp = c.get("/api/graph")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["nodes"]) == 2
            assert len(data["edges"]) == 1

            resp2 = c.get("/api/graph/Max")
            assert resp2.status_code == 200
            data2 = resp2.get_json()
            assert len(data2["nodes"]) >= 1

            resp3 = c.get("/api/graph/Nonexistent")
            assert resp3.status_code == 200
            assert resp3.get_json() == {"nodes": [], "edges": []}


def test_serve_index_html() -> None:
    with tempfile.TemporaryDirectory() as d:
        s = Store(os.path.join(d, "test.db"))
        app = create_app(s)
        with app.test_client() as c:
            resp = c.get("/")
            assert resp.status_code == 200
            assert "sigma" in resp.get_data(as_text=True)


def test_show_with_data() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "Макс",
                           "--props", '{"age":30, "role":"protagonist"}'])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "Софія"])
        runner.invoke(cli, ["add-edge", "--source", "1", "--target", "2", "--label", "loves"])
        out = runner.invoke(cli, ["show", "Макс"]).output
        assert "Макс" in out
        assert "loves" in out
        assert "Софія" in out


def test_stats_with_data() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "X"])
        runner.invoke(cli, ["add-node", "--type", "location", "--label", "Y"])
        out = runner.invoke(cli, ["stats"]).output
        assert "Node" in out
        assert "character: 1" in out
        assert "location: 1" in out
