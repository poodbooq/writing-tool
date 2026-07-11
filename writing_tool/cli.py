from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import click

from writing_tool.config import get_api_key, get_model, load_config, save_defaults
from writing_tool.extractor import extract as llm_extract
from writing_tool.interactive import run_extract
from writing_tool.scanner import scan_md_files
from writing_tool.skill_installer import ensure_agents_skills_dir
from writing_tool.skill_installer import install_skill as _install_skill
from writing_tool.store import Store


def _find_wt_dir() -> Path:
    cwd = Path.cwd()
    for d in [cwd, *cwd.parents]:
        wt = d / ".wt"
        if wt.is_dir():
            return wt
    raise click.ClickException(
        "No .wt/ directory found. Run 'wt init' first."
    )


def _get_store() -> Store:
    wt_dir = _find_wt_dir()
    return Store(wt_dir / "writing.db")


def _get_config() -> dict[str, Any]:
    wt_dir = _find_wt_dir()
    return load_config(wt_dir)


def _read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


@click.group()
def cli() -> None:
    """wt — graph-based entity/relationship tracker for fiction writers."""


@cli.command()
@click.option("--skill", is_flag=True, help="Also install agent skill to .agents/skills/")
def init(skill: bool) -> None:
    """Initialize a .wt/ directory with writing.db and config.toml."""
    root = Path.cwd()
    wt_dir = root / ".wt"
    if wt_dir.exists():
        click.echo(".wt/ already exists")
        return
    wt_dir.mkdir(parents=True)
    Store(wt_dir / "writing.db")
    save_defaults(wt_dir)
    click.echo(f"Initialized {wt_dir}/")
    if skill:
        agents_skills = ensure_agents_skills_dir(root)
        _install_skill(agents_skills, force=False)
        click.echo(f"Installed skill to {agents_skills / 'writing-tool'}/")


@cli.command(name="install-skill")
@click.option("--force", is_flag=True, help="Overwrite existing skill files")
def install_skill_cmd(force: bool) -> None:
    """Install the agent skill to .agents/skills/writing-tool/."""
    from writing_tool.skill_installer import SKILL_NAME, find_agents_skills_dir

    existing = find_agents_skills_dir()
    if existing:
        skill_dir = existing / SKILL_NAME
        if skill_dir.exists() and not force:
            click.echo(f"Skill already exists at {skill_dir}/")
            click.echo("Use --force to overwrite")
            return
        agents_skills = existing
    else:
        agents_skills = ensure_agents_skills_dir(Path.cwd())
    dest = _install_skill(agents_skills, force=force)
    click.echo(f"Installed skill to {dest}/")


@cli.command(name="update-skill")
def update_skill_cmd() -> None:
    """Reinstall skill files to .agents/skills/writing-tool/ (forces overwrite)."""
    from writing_tool.skill_installer import find_agents_skills_dir

    existing = find_agents_skills_dir()
    if not existing:
        agents_skills = ensure_agents_skills_dir(Path.cwd())
    else:
        agents_skills = existing
    dest = _install_skill(agents_skills, force=True)
    click.echo(f"Updated skill at {dest}/")


@cli.command(name="update")
def update_cmd() -> None:
    """Update wt to the latest version from GitHub."""
    # Find project root — either where this module lives or from CWD
    pkg_dir = Path(__file__).resolve().parent
    for d in [pkg_dir, *pkg_dir.parents]:
        if (d / "pyproject.toml").exists():
            project_root = d
            break
    else:
        project_root = Path.cwd()

    git_dir = project_root / ".git"
    if not git_dir.is_dir():
        click.echo("Not a git repository — cannot update.")
        return

    remote = (
        subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=project_root,
        )
        .stdout.strip()
    )
    if not remote:
        click.echo("No git remote 'origin' configured.")
        return

    click.echo(f"Updating from {remote} ...")
    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        capture_output=True, text=True, cwd=project_root,
    )
    if result.returncode != 0:
        click.echo(f"Update failed:\n{result.stderr.strip()}")
        return
    click.echo(result.stdout.strip())

    # Reinstall the package
    click.echo("Reinstalling package...")
    pip = project_root / ".venv" / "bin" / "pip"
    if pip.exists():
        subprocess.run(
            [str(pip), "install", "-e", ".", "--quiet"],
            cwd=project_root, check=True,
        )
    else:
        # If no .venv, try system pip
        subprocess.run(
            ["pip", "install", "-e", ".", "--quiet"],
            cwd=project_root, check=True,
        )

    click.echo("wt is up to date.")


@cli.command()
@click.argument("files", nargs=-1)
@click.option("--yes", is_flag=True, help="Auto-approve all extractions")
def extract(files: tuple[str, ...], yes: bool) -> None:
    """Extract entities and relationships from markdown files via LLM."""
    store = _get_store()
    cfg = _get_config()
    model = get_model(cfg)
    api_key = get_api_key(cfg)

    if not files:
        return

    for f in files:
        path = Path(f)
        if not path.exists():
            click.echo(f"File not found: {f}")
            continue
        text = path.read_text(encoding="utf-8")
        stat = path.stat()
        click.echo(f"Analyzing {f}...")
        result = llm_extract(text, model=model, api_key=api_key)
        ne = len(result.get("entities", []))
        nr = len(result.get("relationships", []))
        click.echo(f"  Found {ne} entities, {nr} relationships")

        root = _find_wt_dir().parent
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        changed = run_extract(
            text,
            result,
            store,
            source_file=str(rel),
            mtime=stat.st_mtime,
            yes=yes,
        )
        if changed:
            click.echo("  ✓ Applied")
        else:
            click.echo("  - Skipped")


@cli.command()
@click.option("--yes", is_flag=True, help="Auto-approve all extractions")
def reindex(yes: bool) -> None:
    """Re-extract all changed markdown files."""
    store = _get_store()
    cfg = _get_config()
    model = get_model(cfg)
    api_key = get_api_key(cfg)
    root = _find_wt_dir().parent

    tracked = store.get_tracked_files()
    files = scan_md_files(root)

    changed: list[dict[str, object]] = []
    for f in files:
        fpath = str(f["path"])
        mtime = f["mtime"]
        if fpath not in tracked or mtime != tracked[fpath]:
            changed.append(f)

    if not changed:
        click.echo("No changed files.")
        return

    click.echo(f"Found {len(changed)} changed file(s)")
    for f in changed:
        fpath = str(f["path"])
        abspath = str(f["abspath"])
        mtime = f["mtime"]
        assert isinstance(mtime, float)
        click.echo(f"\n{fpath}")
        text = _read_file(abspath)
        result = llm_extract(text, model=model, api_key=api_key)
        ne = len(result.get("entities", []))
        nr = len(result.get("relationships", []))
        click.echo(f"  {ne} entities, {nr} relationships")
        run_extract(
            text, result, store, source_file=fpath, mtime=mtime, yes=yes
        )
        if not yes:
            click.echo("  ✓ Applied")


@cli.command()
@click.argument("label")
@click.option("--depth", default=1, type=int, help="Traversal depth")
@click.option("--json", "json_", is_flag=True, help="JSON output")
def show(label: str, depth: int, json_: bool) -> None:
    """Show an entity's properties and relationships."""
    store = _get_store()
    nodes = store.find_nodes(label)
    if not nodes:
        click.echo(f"No entity matching '{label}'")
        return
    node = nodes[0]
    graph = store.get_graph(node["id"], depth=depth)
    by_id = {n["id"]: n for n in graph["nodes"]}
    if json_:
        import json as j
        click.echo(j.dumps({"root": node, "graph": graph}, indent=2, ensure_ascii=False))
        return
    _print_node(node)
    for e in graph["edges"]:
        src = by_id.get(e["source_id"], {})
        tgt = by_id.get(e["target_id"], {})
        s_label = src.get("label", f"#{e['source_id']}")
        t_label = tgt.get("label", f"#{e['target_id']}")
        click.echo(f"  ├── {s_label} —{e['label']}— {t_label}")


def _print_node(node: dict[str, Any]) -> None:
    label = node.get("label", "?")
    ntype = node.get("type", "?")
    props = node.get("props", {})
    click.echo(f"{label} ({ntype})")
    for k, v in props.items():
        click.echo(f"  ├── {k}: {v}")


@cli.command()
@click.argument("label", required=False)
@click.option("--depth", default=2, type=int, help="Traversal depth")
@click.option("--format", "fmt", default="ascii", type=click.Choice(["ascii", "dot", "graphml"]))
def graph(label: str | None, depth: int, fmt: str) -> None:
    """Render the graph or a subgraph around an entity."""
    store = _get_store()
    if label:
        nodes = store.find_nodes(label)
        if not nodes:
            click.echo(f"No entity matching '{label}'")
            return
        g = store.get_graph(nodes[0]["id"], depth=depth)
    else:
        g = {"nodes": store.all_nodes(), "edges": store.all_edges()}
    if fmt == "ascii":
        click.echo(_render_ascii(g))
    elif fmt == "dot":
        click.echo(_render_dot(g))
    elif fmt == "graphml":
        click.echo(_render_graphml(g))


def _render_ascii(graph: dict[str, Any]) -> str:
    by_id = {n["id"]: n for n in graph["nodes"]}
    lines: list[str] = []
    for e in graph["edges"]:
        src = by_id.get(e["source_id"], {})
        tgt = by_id.get(e["target_id"], {})
        lines.append(
            f"  {src.get('label', '?')} --[{e['label']}]--> {tgt.get('label', '?')}"
        )
    if not lines:
        nodes = [f"  {n.get('label', '?')} ({n.get('type', '?')})" for n in graph["nodes"]]
        return "\n".join(nodes) if nodes else "(empty)"
    return "\n".join(lines)


def _render_dot(graph: dict[str, Any]) -> str:
    lines = ['digraph G {', '  rankdir=LR;']
    for n in graph["nodes"]:
        label = n.get("label", "?")
        ntype = n.get("type", "?")
        safe = label.replace('"', '\\"')
        lines.append(f'  n{n["id"]} [label="{safe}" shape="box" tooltip="{ntype}"];')
    for e in graph["edges"]:
        lines.append(f'  n{e["source_id"]} -> n{e["target_id"]} [label="{e["label"]}"];')
    lines.append("}")
    return "\n".join(lines)


def _render_graphml(graph: dict[str, Any]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
        '  <graph id="G" edgedefault="directed">',
    ]
    for n in graph["nodes"]:
        lines.append(f'    <node id="n{n["id"]}">')
        lines.append(f'      <data key="type">{n.get("type", "?")}</data>')
        lines.append(f'      <data key="label">{n.get("label", "?")}</data>')
        lines.append("    </node>")
    for e in graph["edges"]:
        lines.append(
            f'    <edge source="n{e["source_id"]}" target="n{e["target_id"]}">'
            f'<data key="label">{e["label"]}</data></edge>'
        )
    lines.append("  </graph>")
    lines.append("</graphml>")
    return "\n".join(lines)


@cli.command()
@click.argument("query_str", nargs=-1)
def query(query_str: tuple[str, ...]) -> None:
    """Ask a natural language question about your story graph."""
    if not query_str:
        click.echo("Usage: wt query <question>")
        return
    cfg = _get_config()
    model = get_model(cfg)
    api_key = get_api_key(cfg)
    store = _get_store()
    question = " ".join(query_str)
    stats = store.stats()
    context = f"The graph has {stats['nodes']} nodes and {stats['edges']} edges."
    from litellm import completion
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a story graph assistant. Answer questions based on the available graph data. "
                "Be concise and focus on relationships. Say 'I don't have that information' if unknown.",
            },
            {
                "role": "user",
                "content": f"{context}\n\nQuestion: {question}\n\n"
                f"To answer, use the store: call python code with store.get_graph, store.find_nodes, etc.",
            },
        ],
        "temperature": 0.3,
    }
    if api_key:
        kwargs["api_key"] = api_key
    resp = completion(**kwargs)
    click.echo(resp.choices[0].message.content)


@cli.command()
@click.option("--port", default=5000, type=int, help="Port to serve on")
def serve(port: int) -> None:
    """Start a local web server with an interactive graph viewer."""
    cfg = _get_config()
    store = _get_store()
    from writing_tool.server import create_app
    app = create_app(store, cfg=cfg)
    click.echo(f"Starting server on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)


@cli.command()
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "graphml"]))
@click.argument("output", required=False)
def export(fmt: str, output: str | None) -> None:
    """Export the entire graph."""
    store = _get_store()
    data = {"nodes": store.all_nodes(), "edges": store.all_edges()}
    if fmt == "json":
        import json as j
        text = j.dumps(data, indent=2, ensure_ascii=False)
    else:
        text = _render_graphml(data)
    if output:
        Path(output).write_text(text, encoding="utf-8")
        click.echo(f"Exported to {output}")
    else:
        click.echo(text)


@cli.command()
def stats() -> None:
    """Show graph statistics."""
    store = _get_store()
    s = store.stats()
    click.echo(f"Nodes: {s['nodes']}")
    click.echo(f"Edges: {s['edges']}")
    click.echo("By type:")
    for t, c in s["by_type"].items():
        click.echo(f"  {t}: {c}")


@cli.command(name="add-node")
@click.option("--type", "ntype", required=True, help="Node type")
@click.option("--label", required=True, help="Node label")
@click.option("--props", default="{}", help="JSON props")
def add_node(ntype: str, label: str, props: str) -> None:
    """Add a node directly (for scripting/agent use)."""
    store = _get_store()
    import json
    props_dict = json.loads(props)
    nid = store.add_node(ntype, label, props_dict)
    click.echo(f"Added node #{nid}: {label} ({ntype})")


@cli.command(name="add-edge")
@click.option("--source", type=int, required=True, help="Source node ID")
@click.option("--target", type=int, required=True, help="Target node ID")
@click.option("--label", required=True, help="Edge label")
@click.option("--props", default="{}", help="JSON props")
def add_edge(source: int, target: int, label: str, props: str) -> None:
    """Add an edge directly (for scripting/agent use)."""
    store = _get_store()
    import json
    props_dict = json.loads(props)
    eid = store.add_edge(source, target, label, props_dict)
    click.echo(f"Added edge #{eid}: {source} --[{label}]--> {target}")
