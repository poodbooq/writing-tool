# Workflow Examples

## Scenario 1: New scene

User writes a new markdown file and wants to index it.

```bash
# Analyze and commit
scripts/extract.py chapter-3/scene-012.md --yes

# Check what was added
scripts/show-entity.py "Maxim"
```

**Expected output:** JSON with `status: "ok"`, entity and relationship counts.

---

## Scenario 2: Explore a character

User wants to know everything about a character.

```bash
# Show entity with depth 2 (friends, locations, etc.)
scripts/show-entity.py "Maxim" --depth 2

# Natural language
scripts/query-graph.py "Tell me about Maxim"
```

---

## Scenario 3: Dry-run analysis

User wants to preview what the LLM will extract before committing.

```bash
scripts/analyze-file.py draft-scene.md

# Review the JSON output, then if satisfactory:
scripts/extract.py draft-scene.md --yes
```

---

## Scenario 4: Find location relationships

User wants to know which characters are associated with a location.

```bash
wt show "Dark Forest" --depth 2 --json
# Look for edges where Dark Forest is source or target

# Or with the script:
scripts/show-entity.py "Dark Forest" --depth 2
```

---

## Scenario 5: Full reindex

User has edited many files and wants to update the graph.

```bash
wt reindex --yes
wt stats
```

---

## Scenario 6: Manual edits

The LLM missed something and the user wants to fix it.

```bash
# Add a missing edge
wt add-edge --source 1 --target 3 --label "allied_with"

# Verify
wt show "Maxim" --json
```
