from __future__ import annotations

import json
import sqlite3
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1

SQL_CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS nodes (
        id          INTEGER PRIMARY KEY,
        type        TEXT    NOT NULL DEFAULT 'note',
        label       TEXT    NOT NULL,
        props       TEXT    NOT NULL DEFAULT '{}',
        source_file TEXT,
        mtime       REAL,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS edges (
        id         INTEGER PRIMARY KEY,
        source_id  INTEGER NOT NULL REFERENCES nodes(id),
        target_id  INTEGER NOT NULL REFERENCES nodes(id),
        label      TEXT    NOT NULL,
        props      TEXT    NOT NULL DEFAULT '{}',
        created_at TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)",
    "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)",
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
        label, type, content='nodes', content_rowid='id'
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
        INSERT INTO nodes_fts(rowid, label, type) VALUES (new.id, new.label, new.type);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
        INSERT INTO nodes_fts(nodes_fts, rowid, label, type) VALUES('delete', old.id, old.label, old.type);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
        INSERT INTO nodes_fts(nodes_fts, rowid, label, type) VALUES('delete', old.id, old.label, old.type);
        INSERT INTO nodes_fts(rowid, label, type) VALUES (new.id, new.label, new.type);
    END
    """,
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json(value: dict[str, Any] | None) -> str:
    if value is None:
        return "{}"
    return json.dumps(value, ensure_ascii=False)


def _parse(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d: dict[str, Any] = dict(row)
    if "props" in d and isinstance(d["props"], str):
        d["props"] = json.loads(d["props"])
    return d


def _parse_all(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [d for r in rows if (d := _parse(r)) is not None]


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if version < SCHEMA_VERSION:
            cur = self._conn.cursor()
            for sql in SQL_CREATE_TABLES:
                cur.execute(sql)
            cur.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ---- Nodes ----

    def add_node(
        self,
        type: str,
        label: str,
        props: dict[str, Any] | None = None,
        source_file: str | None = None,
        mtime: float | None = None,
    ) -> int:
        now = _now()
        cur = self._conn.execute(
            "INSERT INTO nodes (type, label, props, source_file, mtime, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (type, label, _json(props), source_file, mtime, now, now),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_node(self, id: int) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM nodes WHERE id = ?", (id,))
        return _parse(cur.fetchone())

    def find_nodes(self, label: str, exact: bool = False) -> list[dict[str, Any]]:
        if exact:
            cur = self._conn.execute("SELECT * FROM nodes WHERE label = ?", (label,))
        else:
            cur = self._conn.execute(
                "SELECT * FROM nodes WHERE label LIKE ?", (f"%{label}%",)
            )
        return _parse_all(cur.fetchall())

    def search_nodes(
        self,
        type: str | None = None,
        label_contains: str | None = None,
    ) -> list[dict[str, Any]]:
        parts: list[str] = ["SELECT * FROM nodes WHERE 1=1"]
        params: list[Any] = []
        if type:
            parts.append("AND type = ?")
            params.append(type)
        if label_contains:
            parts.append("AND label LIKE ?")
            params.append(f"%{label_contains}%")
        cur = self._conn.execute(" ".join(parts), params)
        return _parse_all(cur.fetchall())

    def update_node(self, id: int, **kwargs: Any) -> None:
        sets: list[str] = []
        params: list[Any] = []
        for key in ("type", "label", "props", "source_file", "mtime"):
            if key in kwargs:
                val = kwargs[key]
                if key == "props" and isinstance(val, dict):
                    val = _json(val)
                sets.append(f"{key} = ?")
                params.append(val)
        if not sets:
            return
        sets.append("updated_at = ?")
        params.append(_now())
        params.append(id)
        self._conn.execute(
            f"UPDATE nodes SET {', '.join(sets)} WHERE id = ?", params
        )
        self._conn.commit()

    def delete_node(self, id: int) -> None:
        self._conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (id, id))
        self._conn.execute("DELETE FROM nodes WHERE id = ?", (id,))
        self._conn.commit()

    # ---- Edges ----

    def add_edge(
        self,
        source_id: int,
        target_id: int,
        label: str,
        props: dict[str, Any] | None = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO edges (source_id, target_id, label, props, created_at) VALUES (?, ?, ?, ?, ?)",
            (source_id, target_id, label, _json(props), _now()),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_edges(self, node_id: int) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
            (node_id, node_id),
        )
        return _parse_all(cur.fetchall())

    def delete_edge(self, id: int) -> None:
        self._conn.execute("DELETE FROM edges WHERE id = ?", (id,))
        self._conn.commit()

    # ---- Graph traversal ----

    def get_graph(self, root_id: int, depth: int = 2) -> dict[str, list[dict[str, Any]]]:
        visited: set[int] = set()
        node_ids: list[int] = [root_id]
        queue: deque[tuple[int, int]] = deque()
        queue.append((root_id, 0))
        while queue:
            nid, d = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            if d >= depth:
                continue
            rows = self._conn.execute(
                "SELECT source_id, target_id FROM edges WHERE source_id = ? OR target_id = ?",
                (nid, nid),
            ).fetchall()
            for row in rows:
                other = row["target_id"] if row["source_id"] == nid else row["source_id"]
                if other not in visited:
                    node_ids.append(other)
                    queue.append((other, d + 1))
        nodes = list[dict[str, Any]]()
        for nid in node_ids:
            nd = _parse(self._conn.execute("SELECT * FROM nodes WHERE id = ?", (nid,)).fetchone())
            if nd is not None:
                nodes.append(nd)
        placeholders = ",".join("?" for _ in node_ids)
        edges = _parse_all(
            self._conn.execute(
                f"SELECT * FROM edges WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})",
                node_ids + node_ids,
            ).fetchall()
        )
        return {"nodes": nodes, "edges": edges}

    # ---- File tracking ----

    def get_tracked_files(self) -> dict[str, float]:
        cur = self._conn.execute(
            "SELECT DISTINCT source_file, mtime FROM nodes WHERE source_file IS NOT NULL"
        )
        return {r["source_file"]: r["mtime"] for r in cur.fetchall()}

    # ---- Stats ----

    def stats(self) -> dict[str, Any]:
        node_count = self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        by_type = {
            r["type"]: r["cnt"]
            for r in self._conn.execute(
                "SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type ORDER BY cnt DESC"
            ).fetchall()
        }
        return {
            "nodes": node_count,
            "edges": edge_count,
            "by_type": by_type,
        }

    # ---- Export ----

    def all_nodes(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM nodes ORDER BY id")
        return _parse_all(cur.fetchall())

    def all_edges(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM edges ORDER BY id")
        return _parse_all(cur.fetchall())
