from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

import yaml

from writing_tool.store import Store


def _yaml_dump(data: dict[str, Any]) -> str:
    return cast(str, yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ))


def _yaml_load(text: str) -> dict[str, Any]:
    result = yaml.safe_load(text) or {}
    assert isinstance(result, dict)
    return result


def _edit_temp(content: str, suffix: str = ".yml") -> str | None:
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmppath = f.name
    try:
        result = subprocess.run(
            [editor, tmppath],
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return None
        return Path(tmppath).read_text(encoding="utf-8")
    finally:
        Path(tmppath).unlink(missing_ok=True)


def _apply_extract(
    data: dict[str, Any],
    store: Store,
    source_file: str,
    mtime: float,
) -> None:
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    label_to_id: dict[str, int] = {}

    for ent in entities:
        label: str = ent.get("label", "")
        etype: str = ent.get("type", "note")
        props: dict[str, Any] = ent.get("props", {})
        existing = store.find_nodes(label, exact=True)
        if existing:
            node_id = existing[0]["id"]
            store.update_node(
                node_id,
                type=etype,
                props={**existing[0].get("props", {}), **props},
                source_file=source_file,
                mtime=mtime,
            )
        else:
            node_id = store.add_node(
                type=etype,
                label=label,
                props=props,
                source_file=source_file,
                mtime=mtime,
            )
        label_to_id[label] = node_id

    for rel in relationships:
        src_label: str = rel.get("source", "")
        tgt_label: str = rel.get("target", "")
        rel_label: str = rel.get("label", "")
        src_id = label_to_id.get(src_label)
        tgt_id = label_to_id.get(tgt_label)
        if src_id is None or tgt_id is None:
            continue
        existing_edges = store.get_edges(src_id)
        dup = False
        for e in existing_edges:
            if (
                e["target_id"] == tgt_id
                and e["label"] == rel_label
                and e["source_id"] == src_id
            ):
                dup = True
                break
        if not dup:
            store.add_edge(
                source_id=src_id,
                target_id=tgt_id,
                label=rel_label,
                props=rel.get("props"),
            )


def run_extract(
    file_text: str,
    llm_result: dict[str, Any],
    store: Store,
    source_file: str,
    mtime: float,
    yes: bool = False,
) -> bool:
    """Run interactive or auto extract. Returns True if changes were made."""
    if yes:
        _apply_extract(llm_result, store, source_file, mtime)
        return True

    template = "# wt extract — " + source_file + "\n"
    template += "# Save & close to accept. Delete items to skip. Edit props as needed.\n\n"
    template += _yaml_dump(llm_result)

    edited = _edit_temp(template)
    if edited is None:
        return False

    parsed = _yaml_load(edited)
    entities = parsed.get("entities", [])
    relationships = parsed.get("relationships", [])
    if not isinstance(entities, list):
        entities = []
    if not isinstance(relationships, list):
        relationships = []

    if not entities and not relationships:
        return False

    _apply_extract(parsed, store, source_file, mtime)
    return True
