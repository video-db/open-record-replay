"""Tests for registry.py."""

from pathlib import Path

import registry


def test_install_skill_globally_copies_generated_skill_md(tmp_path, monkeypatch):
    global_skills_root = tmp_path / "global-skills"
    monkeypatch.setattr(registry, "AGENT_GLOBAL_SKILLS_ROOT", global_skills_root)

    source_dir = tmp_path / "generated" / "example-skill"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "SKILL.md"
    source_path.write_text("# Example\n", encoding="utf-8")

    destination = registry.install_skill_globally(
        {"name": "example-skill"},
        Path(source_path),
    )

    assert destination == global_skills_root / "example-skill" / "SKILL.md"
    assert destination.read_text(encoding="utf-8") == "# Example\n"
