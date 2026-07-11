from __future__ import annotations

import shutil
from pathlib import Path


SKILL_NAME = "writing-tool"


def get_skill_templates_dir() -> Path:
    return Path(__file__).parent / "skill_templates"


def find_agents_skills_dir(start: Path | None = None) -> Path | None:
    cwd = start or Path.cwd()
    for d in [cwd, *cwd.parents]:
        agents_skills = d / ".agents" / "skills"
        if agents_skills.is_dir():
            return agents_skills
    return None


def ensure_agents_skills_dir(at: Path) -> Path:
    agents_skills = at / ".agents" / "skills"
    agents_skills.mkdir(parents=True, exist_ok=True)
    return agents_skills


def install_skill(dest_parent: Path, force: bool = False) -> Path:
    src = get_skill_templates_dir()
    dest = dest_parent / SKILL_NAME
    if dest.exists():
        if force:
            shutil.rmtree(dest)
        else:
            return dest
    shutil.copytree(src, dest)
    return dest
