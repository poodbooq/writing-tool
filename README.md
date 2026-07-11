# wt — Writing Tool

Graph-based entity/relationship tracker for fiction writers.  
Files are the source of truth (`.md`), SQLite (`writing.db`) is the graph index.  
LLM extracts entities and relationships; you approve via `$EDITOR`.

## Installation

```bash
# One-line setup
just setup
just install    # symlinks wt → ~/.local/bin/wt

# Or manually
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
ln -sf "$(realpath .venv/bin/wt)" ~/.local/bin/wt
```

Requires Python ≥ 3.11.

## Quick start

```bash
cd ~/my-novel
wt init

# Write a scene
cat > scene-001.md <<EOF
Максим — лісник. Він закоханий у Софію.
Вони разом живуть у лісі, який називають Темним.
EOF

# Extract entities (opens $EDITOR for approval)
wt extract scene-001.md

# Explore
wt show Максим
wt graph --format ascii
wt stats
wt serve
```

## Commands

| Command | Description |
|---------|-------------|
| `wt init` | Create `writing.db` in current directory |
| `wt extract [--yes] <file>...` | LLM analyzes `.md` files, opens `$EDITOR` |
| `wt reindex [--yes]` | Re-extract all changed `.md` files |
| `wt show <label> [--depth N] [--json]` | Show entity properties + relationships |
| `wt graph [<label>] [--depth N] [--format ascii\|dot\|graphml]` | Render graph |
| `wt query <question>` | Ask a question about your story graph |
| `wt serve [--port N]` | Start sigma.js web viewer |
| `wt export [--format json\|graphml] [<file>]` | Export entire graph |
| `wt stats` | Show node/edge counts |
| `wt add-node --type <t> --label <l> --props '{}'` | Add node (for scripting) |
| `wt add-edge --source <id> --target <id> --label <l>` | Add edge (for scripting) |

## How it works

1. You write `.md` files (any directory structure)
2. `wt extract file.md` sends the text to an LLM
3. LLM returns structured entities + relationships in JSON
4. `$EDITOR` opens a YAML preview — you accept, edit, or delete items
5. Changes are written to `writing.db` (two tables: `nodes`, `edges`)
6. `wt show`, `wt graph`, `wt query` read from the graph

## Interactive approval

When you run `wt extract scene.md`, your `$EDITOR` opens a file like this:

```yaml
# wt extract — scene.md
# Save & close to accept. Delete items to skip. Edit props as needed.

entities:
  - label: Максим
    type: character
    props:
      age: 30
      role: protagonist

  - label: Софія
    type: character
    props: {}

relationships:
  - source: Максим
    target: Софія
    label: loves
```

Save and close to apply. Delete lines to skip. Edit `props` as needed.  
For batch processing: `wt extract --yes file.md` skips the editor.

## Examples

### Show entity

```
$ wt show Максим
Максим (character)
  ├── age: 30
  ├── role: protagonist
  ├── Максим —loves— Софія
  └── Максим —lives_in— Темний ліс
```

### Graph export

```bash
wt graph --format graphml > graph.graphml    # → yEd, Gephi
wt graph Максим --depth 2 --format ascii     # → terminal
wt export --format json > backup.json        # → full export
```

### Web viewer

```bash
wt serve                        # → http://127.0.0.1:5000
```

## For AI agents

The `SKILL.md` file documents all commands, schema, and examples.  
Use `--json` flag for structured output, `--yes` for auto-approve:

```bash
# Agent-friendly
wt show Максим --json
wt reindex --yes
wt add-node --type character --label Максим --props '{"age":30}'
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `WT_LLM_MODEL` | `gpt-4o-mini` | LLM model to use |
| `EDITOR` | `vi` | Text editor for approval |
| `OPENAI_API_KEY` | — | For OpenAI models |
| `OPENROUTER_API_KEY` | — | For OpenRouter |
| `DEEPSEEK_API_KEY` | — | For DeepSeek |
| `OLLAMA_API_BASE` | — | For local Ollama |

## Development

```bash
just check        # lint → typecheck → test
just coverage     # test with coverage report
just lint         # ruff
just typecheck    # mypy
just test         # pytest
```

Architecture overview:

| Module | Purpose |
|--------|---------|
| `cli.py` | Click commands (11 commands) |
| `store.py` | SQLite graph: nodes + edges, CRUD, FTS5 |
| `extractor.py` | LiteLLM wrapper, system prompt, JSON parser |
| `interactive.py` | `$EDITOR` workflow, YAML roundtrip |
| `scanner.py` | Recursive `.md` file scanner |
| `server.py` | Flask app with sigma.js viewer |
| `web/index.html` | Graph visualisation (sigma v2) |
