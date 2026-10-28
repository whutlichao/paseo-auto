"""Package-shape checks for the shipped skill.

No network, no credentials, no particular machine: the suite reads the files in
``skills/`` and asserts the Agent Skill contract that the installer and the agent
runtime rely on.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
SKILL_DIR = SKILLS_DIR / "paseo-auto-zh"
SKILL_MD = SKILL_DIR / "SKILL.md"

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
NAME_LINE = re.compile(r"(?m)^name:\s*(\S+)\s*$")
DESCRIPTION = re.compile(r"(?m)^description:\s*\S")

TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml"}
HOME_PATH_MARKERS = ("/Users/", "/home/", "C:\\Users\\")


class PackageContentTest(unittest.TestCase):
    def test_frontmatter_name_matches_directory(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        match = FRONTMATTER.match(text)
        self.assertIsNotNone(match, "SKILL.md must start with YAML frontmatter")

        name = NAME_LINE.search(match.group(1))
        self.assertIsNotNone(name, "frontmatter must declare `name`")
        self.assertEqual(name.group(1), SKILL_DIR.name, "`name` must equal the skill directory")
        self.assertIsNotNone(
            DESCRIPTION.search(match.group(1)),
            "frontmatter must declare `description` (the trigger text the agent sees)",
        )

    def test_every_reference_is_linked_from_skill_md(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        references = sorted((SKILL_DIR / "references").glob("*.md"))
        self.assertTrue(references, "the skill must ship reference files")

        unlinked = [path.name for path in references if path.name not in text]
        self.assertEqual(unlinked, [], f"reference files not linked from SKILL.md: {unlinked}")

    def test_no_absolute_home_paths_in_shipped_content(self) -> None:
        offenders: list[str] = []
        for path in sorted(SKILLS_DIR.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(marker in line for marker in HOME_PATH_MARKERS):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}")

        self.assertEqual(offenders, [], f"absolute home paths leaked into shipped content: {offenders}")

    def test_evals_parse_and_match_the_skill(self) -> None:
        payload = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["skill_name"], SKILL_DIR.name)

        evals = payload["evals"]
        self.assertTrue(evals, "evals.json must ship at least one scenario")
        for scenario in evals:
            for field in ("id", "name", "prompt", "expected_output"):
                self.assertIn(field, scenario, f"eval {scenario.get('id')} is missing `{field}`")
                self.assertTrue(str(scenario[field]).strip(), f"eval {scenario['id']} has an empty `{field}`")


if __name__ == "__main__":
    unittest.main()
