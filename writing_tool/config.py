from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_IGNORE_DIRS: list[str] = [".wt", ".agents"]


def load_config(wt_dir: Path) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "llm": {"model": DEFAULT_MODEL},
        "scanner": {"ignore_dirs": DEFAULT_IGNORE_DIRS},
    }
    cfg_path = wt_dir / "config.toml"
    if cfg_path.exists():
        import tomllib
        with cfg_path.open("rb") as f:
            data = tomllib.load(f)
        if isinstance(data, dict):
            if "llm" in data and isinstance(data["llm"], dict):
                cfg["llm"].update(data["llm"])
            if "scanner" in data and isinstance(data["scanner"], dict):
                cfg["scanner"].update(data["scanner"])
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


def get_detail_level(cfg: dict[str, Any]) -> str:
    val = cfg.get("extractor", {}).get("detail_level", "high")
    if isinstance(val, str) and val in ("low", "medium", "high"):
        return val
    return "high"


def get_is_deep(cfg: dict[str, Any]) -> bool:
    return get_detail_level(cfg) == "high"


def get_ignored_dirs(cfg: dict[str, Any]) -> set[str]:
    dirs = cfg.get("scanner", {}).get("ignore_dirs", DEFAULT_IGNORE_DIRS)
    if isinstance(dirs, list):
        return set(dirs)
    return set(DEFAULT_IGNORE_DIRS)


def save_defaults(wt_dir: Path) -> None:
    cfg_path = wt_dir / "config.toml"
    if not cfg_path.exists():
        cfg_path.write_text(
            "[llm]\n"
            'model = "gpt-4o-mini"\n'
            '# api_key = "sk-..."   # optional, overrides OPENAI_API_KEY\n'
            "\n"
            "[extractor]\n"
            'detail_level = "high"     # low | medium | high\n'
            "\n"
            "[scanner]\n"
            'ignore_dirs = [".wt", ".agents"]\n',
            encoding="utf-8",
        )
