"""Package-shape checks for the shipped skills.

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
ENGLISH_SKILL_DIR = SKILLS_DIR / "paseo-auto"

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
NAME_LINE = re.compile(r"(?m)^name:\s*(\S+)\s*$")
DESCRIPTION_BLOCK = re.compile(r"(?ms)^description:\s*(.+)$")
DESCRIPTION_MARKER = re.compile(r"^[>|][-+]?\s*")

MAX_NAME = 64
MAX_DESCRIPTION = 1024

TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml"}
HOME_PATH_MARKERS = ("/Users/", "/home/", "C:\\Users\\")
CJK = re.compile(
    "["
    "\u2e80-\u2fdf"  # CJK radicals supplement and Kangxi radicals
    "\u3000-\u303f"  # CJK symbols and punctuation
    "\u3040-\u30ff"  # Hiragana and katakana
    "\u31c0-\u31ef"  # CJK strokes
    "\u3200-\u32ff"  # enclosed CJK letters and months
    "\u3400-\u4dbf"  # CJK unified ideographs extension A
    "\u4e00-\u9fff"  # CJK unified ideographs
    "\uf900-\ufaff"  # CJK compatibility ideographs
    "\uff00-\uffef"  # halfwidth and fullwidth forms
    "\U00020000-\U0002a6df"  # CJK unified ideographs extension B
    "]"
)

EVAL_FIELDS = ("id", "name", "prompt", "expected_output")


def skill_dirs() -> list[Path]:
    """Every directory under ``skills/`` that ships a SKILL.md."""
    return sorted(path.parent for path in SKILLS_DIR.glob("*/SKILL.md"))


def read_skill_md(skill_dir: Path) -> str:
    return (skill_dir / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(skill_dir: Path) -> str:
    match = FRONTMATTER.match(read_skill_md(skill_dir))
    if match is None:
        raise AssertionError(f"{skill_dir.name}/SKILL.md must start with YAML frontmatter")
    return match.group(1)


def description_text(skill_dir: Path) -> str:
    """The description as the agent runtime sees it: folded, block marker stripped."""
    match = DESCRIPTION_BLOCK.search(frontmatter(skill_dir))
    if match is None:
        raise AssertionError(f"{skill_dir.name}/SKILL.md must declare `description`")
    block = " ".join(line.strip() for line in match.group(1).splitlines()).strip()
    return DESCRIPTION_MARKER.sub("", block)


def load_evals(skill_dir: Path) -> dict:
    return json.loads((skill_dir / "evals" / "evals.json").read_text(encoding="utf-8"))


def reference_names(skill_dir: Path) -> set[str]:
    return {path.name for path in (skill_dir / "references").glob("*.md")}


def eval_ids(skill_dir: Path) -> set[int]:
    return {scenario["id"] for scenario in load_evals(skill_dir)["evals"]}


class PackageContentTest(unittest.TestCase):
    def test_frontmatter_name_matches_directory(self) -> None:
        skills = skill_dirs()
        self.assertTrue(skills, "the package must ship at least one skill")

        for skill_dir in skills:
            with self.subTest(skill=skill_dir.name):
                meta = frontmatter(skill_dir)

                name = NAME_LINE.search(meta)
                self.assertIsNotNone(name, "frontmatter must declare `name`")
                self.assertEqual(
                    name.group(1), skill_dir.name, "`name` must equal the skill directory"
                )
                self.assertLessEqual(
                    len(name.group(1)), MAX_NAME, "`name` must fit the runtime's 64-character cap"
                )

                description = description_text(skill_dir)
                self.assertTrue(
                    description,
                    "frontmatter must declare `description` (the trigger text the agent sees)",
                )
                self.assertLessEqual(
                    len(description),
                    MAX_DESCRIPTION,
                    "`description` must fit the runtime's 1024-character cap",
                )

    def test_every_reference_is_linked_from_skill_md(self) -> None:
        for skill_dir in skill_dirs():
            with self.subTest(skill=skill_dir.name):
                text = read_skill_md(skill_dir)
                references = sorted((skill_dir / "references").glob("*.md"))
                self.assertTrue(references, "the skill must ship reference files")

                unlinked = [path.name for path in references if path.name not in text]
                self.assertEqual(
                    unlinked, [], f"reference files not linked from SKILL.md: {unlinked}"
                )

    def test_no_absolute_home_paths_in_shipped_content(self) -> None:
        offenders: list[str] = []
        for path in sorted(SKILLS_DIR.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(marker in line for marker in HOME_PATH_MARKERS):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}")

        self.assertEqual(
            offenders, [], f"absolute home paths leaked into shipped content: {offenders}"
        )

    def test_evals_parse_and_match_the_skill(self) -> None:
        for skill_dir in skill_dirs():
            with self.subTest(skill=skill_dir.name):
                payload = load_evals(skill_dir)
                self.assertEqual(payload["skill_name"], skill_dir.name)

                evals = payload["evals"]
                self.assertTrue(evals, "evals.json must ship at least one scenario")
                for scenario in evals:
                    for field in EVAL_FIELDS:
                        self.assertIn(
                            field, scenario, f"eval {scenario.get('id')} is missing `{field}`"
                        )
                        self.assertTrue(
                            str(scenario[field]).strip(),
                            f"eval {scenario['id']} has an empty `{field}`",
                        )

    def test_language_variants_share_layout(self) -> None:
        pairs = [
            (skill_dir, skill_dir.with_name(skill_dir.name[: -len("-zh")]))
            for skill_dir in skill_dirs()
            if skill_dir.name.endswith("-zh")
        ]
        pairs = [(variant, base) for variant, base in pairs if base.is_dir()]
        self.assertTrue(pairs, "expected a <name>-zh / <name> language variant pair")

        for variant, base in pairs:
            with self.subTest(skill=base.name):
                self.assertEqual(
                    reference_names(variant),
                    reference_names(base),
                    "both language variants must ship the same reference file names",
                )
                self.assertEqual(
                    eval_ids(variant),
                    eval_ids(base),
                    "both language variants must ship the same eval scenario ids",
                )

    def test_english_skill_has_no_cjk(self) -> None:
        self.assertTrue(
            ENGLISH_SKILL_DIR.is_dir(), "the English skill must ship at skills/paseo-auto"
        )

        offenders: list[str] = []
        for path in sorted(ENGLISH_SKILL_DIR.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if CJK.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}")

        self.assertEqual(offenders, [], f"CJK characters leaked into the English skill: {offenders}")


if __name__ == "__main__":
    unittest.main()
