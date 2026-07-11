from __future__ import annotations

import os
import tempfile

import pytest

from writing_tool.store import Store


@pytest.fixture
def store() -> Store:
    tmp = tempfile.mktemp(suffix=".db")
    s = Store(tmp)
    yield s
    s.close()
    os.unlink(tmp)


class TestStore:
    def test_init_creates_tables(self, store: Store) -> None:
        tables = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "nodes" in names
        assert "edges" in names

    def test_add_node(self, store: Store) -> None:
        nid = store.add_node("character", "Максим", {"age": 30})
        assert nid == 1
        node = store.get_node(nid)
        assert node is not None
        assert node["label"] == "Максим"
        assert node["type"] == "character"
        assert node["props"] == {"age": 30}

    def test_get_node_not_found(self, store: Store) -> None:
        assert store.get_node(999) is None

    def test_find_nodes_fuzzy(self, store: Store) -> None:
        store.add_node("character", "Максим")
        store.add_node("character", "Софія")
        results = store.find_nodes("Макс")
        assert len(results) == 1
        assert results[0]["label"] == "Максим"

    def test_find_nodes_exact(self, store: Store) -> None:
        store.add_node("character", "Максим")
        store.add_node("character", "Макс")
        results = store.find_nodes("Максим", exact=True)
        assert len(results) == 1

    def test_search_nodes_by_type(self, store: Store) -> None:
        store.add_node("character", "Максим")
        store.add_node("location", "Ліс")
        results = store.search_nodes(type="location")
        assert len(results) == 1
        assert results[0]["label"] == "Ліс"

    def test_search_nodes_by_label_contains(self, store: Store) -> None:
        store.add_node("character", "Максим")
        store.add_node("character", "Максиміліан")
        results = store.search_nodes(label_contains="Макс")
        assert len(results) == 2

    def test_update_node(self, store: Store) -> None:
        nid = store.add_node("character", "Максим", {"age": 30})
        store.update_node(nid, props={"age": 31, "role": "protagonist"})
        node = store.get_node(nid)
        assert node is not None
        assert node["props"] == {"age": 31, "role": "protagonist"}

    def test_update_node_label(self, store: Store) -> None:
        nid = store.add_node("character", "Максим")
        store.update_node(nid, label="Максим ІІ")
        node = store.get_node(nid)
        assert node is not None
        assert node["label"] == "Максим ІІ"

    def test_delete_node_cascades_edges(self, store: Store) -> None:
        n1 = store.add_node("character", "A")
        n2 = store.add_node("character", "B")
        store.add_edge(n1, n2, "knows")
        store.delete_node(n1)
        assert store.get_node(n1) is None
        assert store.get_node(n2) is not None
        assert len(store.get_edges(n2)) == 0

    def test_add_edge(self, store: Store) -> None:
        n1 = store.add_node("character", "A")
        n2 = store.add_node("character", "B")
        eid = store.add_edge(n1, n2, "loves")
        assert eid == 1

    def test_get_edges(self, store: Store) -> None:
        n1 = store.add_node("character", "A")
        n2 = store.add_node("character", "B")
        store.add_edge(n1, n2, "loves")
        store.add_edge(n2, n1, "hates")
        edges = store.get_edges(n1)
        assert len(edges) == 2

    def test_delete_edge(self, store: Store) -> None:
        n1 = store.add_node("character", "A")
        n2 = store.add_node("character", "B")
        eid = store.add_edge(n1, n2, "loves")
        store.delete_edge(eid)
        assert len(store.get_edges(n1)) == 0

    def test_get_graph_traversal(self, store: Store) -> None:
        n1 = store.add_node("character", "A")
        n2 = store.add_node("character", "B")
        n3 = store.add_node("character", "C")
        n4 = store.add_node("character", "D")
        store.add_edge(n1, n2, "knows")
        store.add_edge(n2, n3, "knows")
        store.add_edge(n3, n4, "knows")

        g = store.get_graph(n1, depth=1)
        assert len(g["nodes"]) == 2
        assert len(g["edges"]) == 1

        g = store.get_graph(n1, depth=2)
        assert len(g["nodes"]) == 3
        assert len(g["edges"]) == 2

    def test_get_graph_includes_all_edges(self, store: Store) -> None:
        n1 = store.add_node("character", "A")
        n2 = store.add_node("character", "B")
        n3 = store.add_node("character", "C")
        store.add_edge(n1, n2, "knows")
        store.add_edge(n2, n3, "knows")
        store.add_edge(n1, n3, "hates")  # direct edge between A and C

        g = store.get_graph(n1, depth=2)
        edge_labels = {e["label"] for e in g["edges"]}
        assert edge_labels == {"knows", "hates"}

    def test_get_tracked_files(self, store: Store) -> None:
        store.add_node("character", "A", source_file="scene.md", mtime=100.0)
        store.add_node("character", "B", source_file="scene.md", mtime=100.0)
        files = store.get_tracked_files()
        assert files == {"scene.md": 100.0}

    def test_stats_empty(self, store: Store) -> None:
        s = store.stats()
        assert s["nodes"] == 0
        assert s["edges"] == 0
        assert s["by_type"] == {}

    def test_stats_with_data(self, store: Store) -> None:
        store.add_node("character", "A")
        store.add_node("character", "B")
        store.add_node("location", "C")
        store.add_node("event", "D")
        store.add_edge(1, 2, "knows")
        s = store.stats()
        assert s["nodes"] == 4
        assert s["edges"] == 1
        assert s["by_type"] == {"character": 2, "location": 1, "event": 1}

    def test_all_nodes_all_edges(self, store: Store) -> None:
        store.add_node("character", "A")
        store.add_node("character", "B")
        store.add_edge(1, 2, "knows")
        assert len(store.all_nodes()) == 2
        assert len(store.all_edges()) == 1

    def test_props_defaults_to_empty(self, store: Store) -> None:
        nid = store.add_node("character", "X")
        node = store.get_node(nid)
        assert node is not None
        assert node["props"] == {}

    def test_update_node_partial(self, store: Store) -> None:
        nid = store.add_node("character", "X", {"a": 1, "b": 2})
        store.update_node(nid, props={"b": 3})
        node = store.get_node(nid)
        assert node is not None
        assert node["props"] == {"b": 3}

    def test_update_node_noop(self, store: Store) -> None:
        nid = store.add_node("character", "X")
        store.update_node(nid)  # no kwargs
        assert store.get_node(nid) is not None

    def test_migration_idempotent(self, store: Store) -> None:
        store._migrate()  # second run should be fine
        tables = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "nodes" in names

    def test_fts_triggers(self, store: Store) -> None:
        store.add_node("character", "Тест")
        rows = store._conn.execute(
            "SELECT label FROM nodes_fts WHERE nodes_fts MATCH ?", ("Тест",)
        ).fetchall()
        assert len(rows) == 1

    def test_get_tracked_files_updated_mtime(self, store: Store) -> None:
        store.add_node("character", "A", source_file="scene.md", mtime=100.0)
        store.add_node("character", "B", source_file="scene2.md", mtime=200.0)
        files = store.get_tracked_files()
        assert files["scene.md"] == 100.0
        assert files["scene2.md"] == 200.0

        store.update_node(1, mtime=300.0)
        files = store.get_tracked_files()
        assert files["scene.md"] == 300.0
