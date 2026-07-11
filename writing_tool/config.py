from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gpt-4o-mini"


def load_config(wt_dir: Path) -> dict[str, Any]:
    cfg: dict[str, Any] = {"llm": {"model": DEFAULT_MODEL}}
    cfg_path = wt_dir / "config.toml"
    if cfg_path.exists():
        import tomllib
        with cfg_path.open("rb") as f:
            data = tomllib.load(f)
        if isinstance(data, dict):
            if "llm" in data and isinstance(data["llm"], dict):
                cfg["llm"].update(data["llm"])
    env_model = os.environ.get("WT_LLM_MODEL")
    if env_model:
        cfg["llm"]["model"] = env_model
    return cfg


def get_model(cfg: dict[str, Any]) -> str:
    val = cfg.get("llm", {}).get("model", DEFAULT_MODEL)
    assert isinstance(val, str)
    return val


def get_api_key(cfg: dict[str, Any]) -> str | None:
    val = cfg.get("llm", {}).get("api_key")
    return str(val) if val else None


def save_defaults(wt_dir: Path) -> None:
    cfg_path = wt_dir / "config.toml"
    if not cfg_path.exists():
        cfg_path.write_text(
            "[llm]\n"
            'model = "gpt-4o-mini"\n'
            '# api_key = "sk-..."   # optional, overrides OPENAI_API_KEY\n',
            encoding="utf-8",
        )
