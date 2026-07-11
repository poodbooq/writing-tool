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
- "props" is a flat JSON object of relevant attributes (age, role, mood, etc.). Include only what's explicitly stated or strongly implied.
- Relationships connect entities that already exist in the "entities" array.
- "label" in relationships is a short verb phrase: "loves", "fears", "located_in", "works_at", "born_in", "married_to", "fights", "owns", "created", "destroyed", "lives_in", "travels_to", "meets", "speaks_to", etc.
- If a relationship involves an entity not yet listed, add it to entities first.
- If no entities or relationships are found, return {"entities": [], "relationships": []}.
- Do NOT include entities that are generic nouns (e.g., "the man", "the house") unless named specifically.
"""


def _default_model() -> str:
    return os.environ.get("WT_LLM_MODEL", "gpt-4o-mini")


def extract(text: str, model: str | None = None) -> dict[str, Any]:
    """Extract entities and relationships from text using LLM."""
    resp = completion(
        model=model or _default_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this text:\n\n{text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
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
