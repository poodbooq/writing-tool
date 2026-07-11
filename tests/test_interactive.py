from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from writing_tool.interactive import _yaml_dump, _yaml_load, run_extract
from writing_tool.store import Store


def test_yaml_dump_load_roundtrip() -> None:
    data = {
        "entities": [{"label": "Max", "type": "character", "props": {"age": 30}}],
        "relationships": [{"source": "Max", "target": "Eve", "label": "loves"}],
    }
    dumped = _yaml_dump(data)
    loaded = _yaml_load(dumped)
    assert loaded == data


def test_yaml_load_empty() -> None:
    assert _yaml_load("") == {}


def test_yaml_load_none() -> None:
    assert _yaml_load("null") == {}


class TestRunExtract:
    def test_yes_mode(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "test.db")
            s = Store(db)
            result = run_extract(
                "Max loves Eve.",
                {
                    "entities": [
                        {"label": "Max", "type": "character", "props": {"age": 30}},
                        {"label": "Eve", "type": "character", "props": {}},
                    ],
                    "relationships": [{"source": "Max", "target": "Eve", "label": "loves"}],
                },
                s,
                source_file="test.md",
                mtime=100.0,
                yes=True,
            )
            assert result is True
            nodes = s.all_nodes()
            assert len(nodes) == 2
            assert s.stats()["edges"] == 1

    def test_yes_mode_skips_duplicate_edges(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "test.db")
            s = Store(db)
            data = {
                "entities": [
                    {"label": "Max", "type": "character", "props": {}},
                    {"label": "Eve", "type": "character", "props": {}},
                ],
                "relationships": [{"source": "Max", "target": "Eve", "label": "loves"}],
            }
            run_extract("text", data, s, "test.md", 100.0, yes=True)
            run_extract("text", data, s, "test.md", 100.0, yes=True)
            assert s.stats()["edges"] == 1

    def test_yes_mode_updates_existing_node(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "test.db")
            s = Store(db)
            data1 = {
                "entities": [{"label": "Max", "type": "character", "props": {"age": 30}}],
                "relationships": [],
            }
            data2 = {
                "entities": [{"label": "Max", "type": "character", "props": {"age": 31, "role": "hero"}}],
                "relationships": [],
            }
            run_extract("text", data1, s, "test.md", 100.0, yes=True)
            run_extract("text", data2, s, "test.md", 200.0, yes=True)
            node = s.find_nodes("Max", exact=True)[0]
            assert node["props"] == {"age": 31, "role": "hero"}

    @patch("writing_tool.interactive._edit_temp")
    def test_editor_accepts(self, mock_edit: object) -> None:
        mock_edit.return_value = (  # type: ignore[assignment]
            "entities:\n"
            '  - label: Max\n'
            '    type: character\n'
            '    props: {}\n'
            'relationships: []\n'
        )
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "test.db")
            s = Store(db)
            result = run_extract(
                "text",
                {"entities": [{"label": "Max", "type": "character", "props": {}}], "relationships": []},
                s, "test.md", 100.0,
            )
            assert result is True
            assert len(s.all_nodes()) == 1

    @patch("writing_tool.interactive._edit_temp")
    def test_editor_skips(self, mock_edit: object) -> None:
        mock_edit.return_value = "entities: []\nrelationships: []\n"  # type: ignore[assignment]
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "test.db")
            s = Store(db)
            result = run_extract(
                "text",
                {"entities": [{"label": "Max", "type": "character", "props": {}}], "relationships": []},
                s, "test.md", 100.0,
            )
            assert result is False
            assert len(s.all_nodes()) == 0

    @patch("writing_tool.interactive._edit_temp")
    def test_editor_cancels(self, mock_edit: object) -> None:
        mock_edit.return_value = None  # type: ignore[assignment]
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "test.db")
            s = Store(db)
            result = run_extract(
                "text",
                {"entities": [], "relationships": []},
                s, "test.md", 100.0,
            )
            assert result is False
