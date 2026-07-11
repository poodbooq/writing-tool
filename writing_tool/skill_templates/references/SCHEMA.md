# Database Schema

The graph is stored in `.wt/writing.db` — a single SQLite file.

## Tables

### `nodes`

```sql
CREATE TABLE nodes (
    id          INTEGER PRIMARY KEY,
    type        TEXT    NOT NULL DEFAULT 'note',
    label       TEXT    NOT NULL,
    props       TEXT    NOT NULL DEFAULT '{}',   -- JSON
    source_file TEXT,
    mtime       REAL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
```

### `edges`

```sql
CREATE TABLE edges (
    id         INTEGER PRIMARY KEY,
    source_id  INTEGER NOT NULL REFERENCES nodes(id),
    target_id  INTEGER NOT NULL REFERENCES nodes(id),
    label      TEXT    NOT NULL,
    props      TEXT    NOT NULL DEFAULT '{}',   -- JSON
    created_at TEXT    NOT NULL
);
```

## Node types

Types are arbitrary strings. Common ones:

| Type | Description |
|------|-------------|
| `character` | A named person/being |
| `location` | A named place |
| `scene` | A narrative scene |
| `event` | An event or occurrence |
| `item` | An object or artifact |
| `concept` | An abstract idea |
| `note` | Generic node (default) |

## Props examples

Props are arbitrary JSON key-value pairs. Examples:

```json
// character
{"age": 30, "role": "protagonist", "arc": "fear -> courage", "occupation": "ranger"}

// location
{"mood": "eerie", "climate": "cold", "type": "forest"}

// scene
{"mood": "tense", "pace": "fast", "time_of_day": "night"}

// event
{"date": "1992", "importance": "major", "outcome": "victory"}
```

## Relationship labels

Free-form verb phrases. Common ones:

`loves`, `hates`, `fears`, `knows`, `married_to`, `located_in`, `lives_in`,
`travels_to`, `born_in`, `works_at`, `fights`, `owns`, `created`,
`destroyed`, `meets`, `speaks_to`, `participates_in`, `happened_at`,
`leads_to`, `causes`, `wants`, `needs`, `protects`, `betrays`,
`allied_with`, `related_to`, `mentions`
