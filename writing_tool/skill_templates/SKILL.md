---
name: writing-tool
description: Graph-based entity and relationship tracker for fiction writers. Extracts characters, locations, events, and items from markdown text using an LLM, stores them in a local SQLite graph. Use when analyzing narrative text, tracking story entities, exploring relationships, or answering questions about characters, locations, and plot events.
compatibility: Python 3.11+, `wt` installed in PATH, LLM API key configured (OPENAI_API_KEY or equivalent per LiteLLM conventions)
---

# writing-tool

A CLI tool that turns markdown story text into a queryable graph of entities and relationships. File is the source of truth (`.md`), SQLite (`.wt/writing.db`) is the graph index.

## When to use

- The user mentions characters, locations, events, or story entities
- The user asks to analyze a text file for named entities
- The user wants to see relationships between characters
- The user asks "who is X", "what happened at Y", "tell me about Z"
- The user is writing fiction and wants to track their story graph

## Quick start

```bash
# Initialize (one-time)
cd /path/to/project
wt init --skill

# Analyze a scene
wt extract --yes scene-001.md

# Explore
wt show "Maxim"
wt graph "Forest" --depth 2 --format ascii

# Visual
wt serve
```

## Scripts

Scripts are in `scripts/`. Each is a self-contained Python file.

| Script | Purpose |
|--------|---------|
| `scripts/extract.py` | Analyze a `.md` file and commit to graph |
| `scripts/show-entity.py` | Show entity details as JSON |
| `scripts/query-graph.py` | Ask a natural language question |
| `scripts/analyze-file.py` | Dry-run analysis without writing to DB |

## References

Detailed documentation in `references/`:

| File | Content |
|------|---------|
| `references/COMMANDS.md` | All CLI commands with options and examples |
| `references/SCHEMA.md` | Database schema, node types, props, relationship labels |
| `references/EXAMPLES.md` | End-to-end workflow scenarios |

## Notes

- Always use `--yes` for auto-approval when running scripts
- Use `--json` for structured machine-readable output
- The `.wt/` directory contains the database and configuration
- The LLM model is configured in `.wt/config.toml` or `WT_LLM_MODEL` env var
- API key can be set in `.wt/config.toml` (`[llm].api_key`) or in environment variables
- Run `wt update` to update wt to the latest version
- Run `wt install-skill --force` to refresh the skill files
