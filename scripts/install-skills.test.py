from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("install-skills")


class InstallSkillsTest(unittest.TestCase):
    def make_repo(self, root: Path, skills: tuple[str, ...] = ("sample",)) -> Path:
        repo = root / "repo"
        (repo / "scripts").mkdir(parents=True)
        shutil.copy2(SCRIPT, repo / "scripts" / "install-skills")
        for name in skills:
            skill_dir = repo / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {name}\n---\n", encoding="utf-8"
            )
        return repo

    def run_installer(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(repo / "scripts" / "install-skills"), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_force_skips_target_that_is_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(Path(tmp))
            result = self.run_installer(
                repo, "--target", str(repo / "skills"), "--force", "sample"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("target is source, skipping", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue((repo / "skills" / "sample" / "SKILL.md").exists())

    def test_force_copy_replaces_existing_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            target = root / "target"
            target.mkdir()
            try:
                os.symlink(repo / "skills" / "sample", target / "sample", target_is_directory=True)
            except OSError as error:
                if os.name == "nt":
                    self.skipTest(f"symlink creation unavailable: {error}")
                raise

            result = self.run_installer(
                repo, "--target", str(target), "--force", "--mode", "copy", "sample"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("copy sample", result.stdout)
            self.assertFalse((target / "sample").is_symlink())
            self.assertTrue((target / "sample" / "SKILL.md").exists())
            self.assertTrue((repo / "skills" / "sample" / "SKILL.md").exists())

    def test_list_is_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(Path(tmp), ("zeta", "alpha"))
            result = self.run_installer(repo, "--list")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "alpha\nzeta\n")

    def test_dry_run_does_not_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            target = root / "missing" / "skills"
            result = self.run_installer(repo, "--target", str(target), "--dry-run", "sample")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, f"would symlink sample -> {target / 'sample'}\n")
            self.assertFalse(target.exists())

    def test_unknown_skill_reports_available_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(Path(tmp))
            result = self.run_installer(repo, "missing")

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                "unknown skill(s): missing\navailable: sample\n",
            )

    def test_invalid_mode_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(Path(tmp))
            result = self.run_installer(repo, "--mode", "invalid")

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, "invalid --mode: invalid\n")


if __name__ == "__main__":
    unittest.main()
