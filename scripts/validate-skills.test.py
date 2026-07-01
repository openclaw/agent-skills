from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate-skills")


class ValidateSkillsTest(unittest.TestCase):
    def run_validator(
        self, skills: dict[str, str] | None
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "scripts").mkdir(parents=True)
            shutil.copy2(SCRIPT, repo / "scripts" / "validate-skills")
            for name, content in (skills or {}).items():
                skill_dir = repo / "skills" / name
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(repo / "scripts" / "validate-skills")],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_frontmatter(self) -> None:
        result = self.run_validator(
            {
                "sample": (
                    '---\nname: sample\ndescription: "Example skill."\n'
                    'metadata:\n  version: "1"\n---\n# Sample\n'
                )
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "validated 1 skills\n")

    def test_missing_frontmatter(self) -> None:
        result = self.run_validator({"sample": "# Sample\n"})

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing YAML frontmatter", result.stderr)

    def test_unterminated_frontmatter(self) -> None:
        result = self.run_validator({"sample": "---\nname: sample\n"})

        self.assertEqual(result.returncode, 1)
        self.assertIn("unterminated YAML frontmatter", result.stderr)

    def test_invalid_yaml(self) -> None:
        result = self.run_validator(
            {"sample": '---\nname: [sample\ndescription: "Example"\n---\n'}
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid YAML", result.stderr)

    def test_frontmatter_must_be_mapping(self) -> None:
        result = self.run_validator({"sample": "---\n- sample\n---\n"})

        self.assertEqual(result.returncode, 1)
        self.assertIn("YAML frontmatter must be a mapping", result.stderr)

    def test_required_fields_must_be_nonempty_strings(self) -> None:
        result = self.run_validator(
            {"sample": '---\nname: true\ndescription: "  "\n---\n'}
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing name", result.stderr)
        self.assertIn("missing description", result.stderr)

    def test_aliases_are_rejected(self) -> None:
        result = self.run_validator(
            {
                "sample": (
                    '---\nname: &name sample\ndescription: *name\n---\n'
                )
            }
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("YAML aliases are not allowed", result.stderr)

    def test_unsafe_tags_are_rejected(self) -> None:
        result = self.run_validator(
            {
                "sample": (
                    "---\nname: sample\n"
                    "description: !!python/object/apply:os.system ['false']\n---\n"
                )
            }
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid YAML", result.stderr)

    def test_no_skills(self) -> None:
        result = self.run_validator(None)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "No skills/*/SKILL.md files found.\n")


if __name__ == "__main__":
    unittest.main()
