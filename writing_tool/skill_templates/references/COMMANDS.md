# CLI Command Reference

All commands support `--help` for full option details.

## Core

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wt init [--skill]` | Create `.wt/` directory with DB + config | `--skill` also install agent skill to `.agents/skills/` |
| `wt install-skill [--force]` | Install/update agent skill to `.agents/skills/` | `--force` overwrites existing files |
| `wt update` | Update wt to latest version via git pull | — |
| `wt extract [--yes] [--deep] <file>...` | LLM analyzes `.md` files, opens `$EDITOR` for approval | `--yes` auto-approve, `--deep` full extraction |
| `wt reindex [--yes] [--deep]` | Re-extract all changed `.md` files | `--yes` batch mode, `--deep` full extraction |

## Exploration

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wt show <label> [--depth N] [--json]` | Show entity properties + relationships | `--json` for structured output |
| `wt graph [<label>] [--depth N] [--format ascii\|dot\|graphml]` | Render graph | `graphml` for external tools |
| `wt query <question>` | Ask a natural language question | — |
| `wt serve [--port N]` | Start sigma.js web viewer | default port 5000 |

## Management

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wt stats` | Show node/edge counts by type | — |
| `wt export [--format json\|graphml] [<file>]` | Export entire graph | stdout if no file given |
| `wt add-node --type <t> --label <l> [--props '{}']` | Add node directly (scripting) | — |
| `wt add-edge --source <id> --target <id> --label <l> [--props '{}']` | Add edge directly (scripting) | — |

## Examples

```bash
# Initialize project with skill
cd ~/my-novel && wt init --skill

# Analyze a single file
wt extract --yes chapter-1/scene-001.md

# Show character
wt show "Maxim" --json

# Subgraph around a location
wt graph "Dark Forest" --depth 2 --format ascii

# Export for Gephi
wt export --format graphml story.graphml

# Stats
wt stats

# Add a relationship manually
wt add-edge --source 1 --target 2 --label "fears"

# Update wt to latest version
wt update
```
