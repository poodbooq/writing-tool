from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from writing_tool.cli import cli


@patch("writing_tool.cli.llm_extract")
def test_extract_not_applied_because_empty(mock_llm: object) -> None:
    mock_llm.return_value = {"entities": [], "relationships": []}  # type: ignore[assignment]
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        Path("scene.md").write_text("text", encoding="utf-8")
        out = runner.invoke(cli, ["extract", "scene.md", "--yes"]).output
        assert "Found 0 entities" in out


@patch("writing_tool.cli.llm_extract")
def test_extract_with_relative_root(mock_llm: object) -> None:
    mock_llm.return_value = {  # type: ignore[assignment]
        "entities": [{"label": "X", "type": "character", "props": {}}],
        "relationships": [],
    }
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        sub = Path(d, "sub")
        sub.mkdir()
        p = sub / "scene.md"
        p.write_text("text", encoding="utf-8")
        out = runner.invoke(cli, ["extract", str(p), "--yes"]).output
        assert "Applied" in out


def test_reindex_no_changes_with_db() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        out = runner.invoke(cli, ["reindex"]).output
        assert "No changed files" in out


@patch("litellm.completion")
def test_query_executes(mock_completion: object) -> None:
    mock_completion.return_value.choices[0].message.content = "Max loves Eve."  # type: ignore[assignment]
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "Max"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "Eve"])
        runner.invoke(cli, ["add-edge", "--source", "1", "--target", "2", "--label", "loves"])
        out = runner.invoke(cli, ["query", "Who loves who?"]).output
        assert "Max loves Eve" in out


def test_add_node_with_file_ref() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        out = runner.invoke(cli, [
            "add-node", "--type", "character", "--label", "X", "--props", '{"source":"test"}',
        ]).output
        assert "Added node #1" in out


def test_add_edge_with_props() -> None:
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        runner = CliRunner()
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "A"])
        runner.invoke(cli, ["add-node", "--type", "character", "--label", "B"])
        out = runner.invoke(cli, [
            "add-edge", "--source", "1", "--target", "2", "--label", "knows",
            "--props", '{"since":2020}',
        ]).output
        assert "Added edge #1" in out
