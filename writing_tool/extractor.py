from __future__ import annotations

import json
import os
import re
from typing import Any

from litellm import completion


SYSTEM_PROMPT = """You are a literary text analyzer. Given a text passage, extract all named entities and their relationships.

Return ONLY valid JSON with this exact structure:
{
  "entities": [
    {"label": "Entity Name", "type": "character|location|event|item|concept", "props": {"key": "value"}}
  ],
  "relationships": [
    {"source": "Entity Name", "target": "Entity Name", "label": "relationship_name", "props": {}}
  ]
}

Rules:
- "label" is the entity's name as it appears in the text.
- "type" must be one of: character, location, event, item, concept.
- "props" is a flat JSON object of relevant attributes.
- Relationships connect entities in the "entities" array.
- If a relationship involves an entity not listed, add it to entities first.
- If none found, return {"entities": [], "relationships": []}.
- Do NOT include generic nouns as entities.
"""

SYSTEM_PROMPT_DEEP = """You are a deep literary text analyzer. Extract all entities and relationships — both explicit and implicit — with maximum detail.

Return ONLY valid JSON with this exact structure:
{
  "entities": [...],
  "relationships": [...]
}

## Entity types (use the most specific type)

| Type | Description | Props |
|------|-------------|-------|
| `character` | Named person/being | age, role, species, occupation, status, motive, flaw, strength, gender, arc |
| `group` | Organization, faction, family, team | type, purpose, size, ideology |
| `creature` | Non-human animal, monster, mythical being | species, danger, habitat, intelligence |
| `location` | Place — concrete or abstract | mood, climate, type, significance |
| `event` | Occurrence, battle, ritual, festival | date, outcome, scale, impact |
| `item` | Object, artifact, weapon, tool, letter | material, owner, purpose, magical |
| `concept` | Abstract idea: justice, freedom, sacrifice | domain, significance |
| `emotion` | Feeling or state: fear, hope, despair | intensity, target |
| `theme` | Story theme: redemption, betrayal, coming-of-age | prominence |
| `trope` | Narrative archetype: hero's journey, prophecy | context |
| `time_period` | Era, season, time of day | climate, mood, era |
| `scene` | Narrative scene | mood, pace, atmosphere, time_of_day, weather, narrative_pov |
| `arc` | Character or plot arc | from, to, status |
| `profession` | Occupation or role: ranger, witch, king | domain, status |
| `lineage` | Family line, house, dynasty | origin, status, reputation |
| `magic_system` | Magic, technology, supernatural rules | type, cost, limitations |
| `artifact` | Meta-object containing info: diary, map, letter | content_summary, author |

## Relationship labels (60+)

### Emotional & psychological
loves, hates, fears, desires, yearns_for, regrets, resents, admires, trusts, distrusts, envies, pities, despises, adores, mourns, sympathizes_with, ashamed_of, proud_of

### Social & hierarchical
parent_of, child_of, sibling_of, spouse_of, relative_of, friend_of, enemy_of, rival_of, ally_with, mentors, mentored_by, leads, serves, follows, betrays, protects, threatens, obeys, commands, belongs_to, member_of

### Spatial & movement
located_in, lives_in, travels_to, originates_from, visits, flees_to, returns_to, guards, enters, leaves, explores, crosses, passes_through

### Chronological & causal
causes, results_in, prevents, triggers, leads_to, follows_after, precedes, happens_during, happens_before, happens_after, interrupted_by, delayed_by, foreshadows, recalls, refers_to

### Action & event
fights, kills, wounds, saves, rescues, captures, frees, creates, destroys, builds, steals, gives, takes, discovers, hides, seeks, finds, loses, uses, wields, wears, carries

### Communication & information
speaks_to, tells, asks, answers, confesses, lies_to, convinces, argues_with, negotiates, promises, reveals, hides, learns, teaches, writes, reads

### Conceptual & symbolic
symbolizes, represents, embodies, contrasts_with, parallels, reflects, mirrors, subverts, deconstructs, exemplifies, defines, questions, challenges, explores

### Transformation
transforms_into, becomes, changes, evolves, regresses, heals, corrupts, redeems, sacrifices, chooses, rejects

## Key rules

- Extract implicit connections: what does X symbolize? What emotions does Y evoke?
- Extract character motivations, desires, and flaws even if implied.
- Extract group affiliations, species, organizations.
- For concepts/emotions/themes — extract only if distinctly named or strongly thematic.
- For relationships, include props like: intensity, reciprocated, since (for emotional); outcome, date (for events).
- Do NOT include generic nouns as entities.

## Example

```json
{
  "entities": [
    {"label": "Maxim", "type": "character", "props": {"age": 30, "role": "protagonist", "occupation": "ranger", "motive": "save Sophia", "flaw": "pride"}},
    {"label": "Sophia", "type": "character", "props": {"age": 28, "role": "love_interest"}},
    {"label": "Dark Forest", "type": "location", "props": {"mood": "eerie", "type": "forest", "significance": "forbidden"}},
    {"label": "Fear", "type": "emotion", "props": {"intensity": "high"}},
    {"label": "Werewolves", "type": "creature", "props": {"species": "lycanthrope", "danger": "extreme"}},
    {"label": "Sacrifice", "type": "concept", "props": {"domain": "moral"}},
    {"label": "Redemption", "type": "theme", "props": {"prominence": "major"}}
  ],
  "relationships": [
    {"source": "Maxim", "target": "Sophia", "label": "loves", "props": {"intensity": "strong", "reciprocated": true}},
    {"source": "Maxim", "target": "Dark Forest", "label": "fears", "props": {}},
    {"source": "Werewolves", "target": "Dark Forest", "label": "lives_in", "props": {}},
    {"source": "Maxim", "target": "Sacrifice", "label": "embodies", "props": {}},
    {"source": "Dark Forest", "target": "Fear", "label": "evokes", "props": {"intensity": "strong"}},
    {"source": "Maxim", "target": "Redemption", "label": "seeks", "props": {}}
  ]
}
```
"""


def _default_model() -> str:
    return os.environ.get("WT_LLM_MODEL", "gpt-4o-mini")


def extract(
    text: str,
    model: str | None = None,
    api_key: str | None = None,
    deep: bool = False,
) -> dict[str, Any]:
    """Extract entities and relationships from text using LLM."""
    prompt = SYSTEM_PROMPT_DEEP if deep else SYSTEM_PROMPT
    kwargs: dict[str, Any] = {
        "model": model or _default_model(),
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Analyze this text:\n\n{text}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }
    if api_key:
        kwargs["api_key"] = api_key
    resp = completion(**kwargs)
    content = resp.choices[0].message.content
    if not content:
        return {"entities": [], "relationships": []}
    return _parse_response(content)


def _parse_response(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"entities": [], "relationships": []}
    if not isinstance(data, dict):
        return {"entities": [], "relationships": []}
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    if not isinstance(entities, list):
        entities = []
    if not isinstance(relationships, list):
        relationships = []
    for e in entities:
        if not isinstance(e.get("props"), dict):
            e["props"] = {}
    return {"entities": entities, "relationships": relationships}
