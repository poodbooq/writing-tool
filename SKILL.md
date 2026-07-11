# wt — Writing Tool

Graph-based entity/relationship tracker for fiction writers.  
File is source of truth (`.md` files), SQLite (`writing.db`) is the graph index.

## Commands

| Command | Description | Agent Usage |
|---------|-------------|-------------|
| `wt init` | Create `writing.db` in project root | On project setup |
| `wt extract [--yes] <file>...` | LLM analyzes `.md` files, opens `$EDITOR` for approval | `--yes` for auto-approve |
| `wt reindex [--yes]` | Re-extract all changed `.md` files | `--yes` for batch |
| `wt show <label> [--depth N] [--json]` | Show entity properties + relationships | `--json` for structured data |
| `wt graph [<label>] [--depth N] [--format ascii\|dot\|graphml]` | Render graph | graphml for external tools |
| `wt query <question>` | Natural language question about the graph | For human users |
| `wt serve [--port N]` | Start sigma.js web viewer | For visual exploration |
| `wt export [--format json\|graphml] [<file>]` | Export entire graph | For backups/external tools |
| `wt stats` | Show node/edge counts by type | Quick status check |
| `wt add-node --type <t> --label <l> --props '{}'` | Add node directly (low-level) | For scripting |
| `wt add-edge --source <id> --target <id> --label <l>` | Add edge directly (low-level) | For scripting |

## Schema

```sql
nodes(id INTEGER PRIMARY KEY,
      type TEXT NOT NULL DEFAULT 'note',
      label TEXT NOT NULL,
      props TEXT NOT NULL DEFAULT '{}',  -- JSON
      source_file TEXT,
      mtime REAL,
      created_at TEXT,
      updated_at TEXT)

edges(id INTEGER PRIMARY KEY,
      source_id INTEGER REFERENCES nodes(id),
      target_id INTEGER REFERENCES nodes(id),
      label TEXT NOT NULL,
      props TEXT NOT NULL DEFAULT '{}',  -- JSON
      created_at TEXT)
```

## Node types

Dynamic — assign any string: `character`, `location`, `scene`, `event`, `item`, `concept`, `note`.

## Props

Arbitrary JSON key-value pairs. Examples:
- Character: `{"age": 30, "role": "protagonist", "arc": "fear → courage"}`
- Location: `{"mood": "eerie", "climate": "cold"}`
- Scene: `{"mood": "tense", "pace": "fast"}`
- Event: `{"date": "1992", "importance": "major"}`

## Relationship labels

Free-form verb phrases: `loves`, `fears`, `located_in`, `works_at`, `born_in`, `married_to`, `fights`, `owns`, `created`, `lives_in`, `travels_to`, `meets`, `speaks_to`, `happened_at`, `participates_in`, etc.

## Python API

```python
from writing_tool.store import Store

store = Store("writing.db")

# Nodes
nid = store.add_node("character", "Максим", {"age": 30})
node = store.get_node(nid)
nodes = store.find_nodes("Макс")       # fuzzy
node = store.find_nodes("Максим", exact=True)[0]
store.update_node(nid, props={"age": 31})
store.delete_node(nid)

# Edges
eid = store.add_edge(nid1, nid2, "loves")
edges = store.get_edges(nid)
store.delete_edge(eid)

# Graph traversal
graph = store.get_graph(root_id=nid, depth=2)

# Stats
store.stats()
```

## Workflow

1. `wt init` — one-time setup
2. Write `.md` files in any directory structure
3. `wt extract file.md` or `wt reindex --yes` — LLM extracts entities
4. `wt show "Максим"` — inspect entity graph
5. `wt serve` — visual graph explorer
6. For agents: use `--json` and `--yes` flags for automation

## Environment

- `WT_LLM_MODEL`: LLM model (default: `gpt-4o-mini`)
- `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` etc. — per LiteLLM conventions
- `EDITOR`: text editor for interactive approval (default: `vi`)
