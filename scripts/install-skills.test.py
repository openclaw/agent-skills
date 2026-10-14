from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("install-skills")


class InstallSkillsTest(unittest.TestCase):
    def file_bytes(self, root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()
        }

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

    def test_install_rejects_target_inside_source_before_mutating(self) -> None:
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run), tempfile.TemporaryDirectory() as tmp:
                repo = self.make_repo(Path(tmp))
                source = repo / "skills" / "sample"
                target = source / "installed"
                args = ["--target", str(target), "--force", "sample"]
                if dry_run:
                    args.insert(0, "--dry-run")
                result = self.run_installer(repo, *args)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("overlaps source", result.stderr)
                self.assertFalse(target.exists())
                self.assertTrue((source / "SKILL.md").is_file())

    def test_force_rejects_target_containing_source_before_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root, ("repo",))
            result = self.run_installer(repo, "--target", str(root), "--force", "repo")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("overlaps source", result.stderr)
            self.assertFalse(repo.is_symlink())
            self.assertTrue((repo / "skills" / "repo" / "SKILL.md").is_file())

    def test_install_checks_all_destinations_before_creating_any(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root, ("alpha", "repo"))
            result = self.run_installer(repo, "--target", str(root), "--force")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse((root / "alpha").exists())
            self.assertTrue((repo / "skills" / "repo" / "SKILL.md").is_file())

    def test_install_resolves_target_parent_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            alias = root / "alias"
            try:
                alias.symlink_to(repo / "skills" / "sample", target_is_directory=True)
            except OSError as error:
                if os.name == "nt":
                    self.skipTest(f"symlink creation unavailable: {error}")
                raise
            result = self.run_installer(repo, "--target", str(alias / "nested"), "sample")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("overlaps source", result.stderr)
            self.assertFalse((alias / "nested").exists())

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

    def test_copy_upgrade_and_rollback_preserve_external_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.make_repo(root / "release-one")
            second = self.make_repo(root / "release-two")
            for repo, version in ((first, "1"), (second, "2")):
                (repo / ".release-version").write_text(version)
                (repo / "skills/sample/payload").write_text(version)
            (first / "skills/sample/retired").write_text("old source file")
            source_bytes = [self.file_bytes(repo) for repo in (first, second)]
            target = root / "installed skills"
            external = root / "user state"
            external.mkdir()
            for name in ("auth.json", "config.toml", "review.txt"):
                (external / name).write_text("operator-owned fixture")
            external_bytes = self.file_bytes(external)
            sibling = target / "unselected"
            sibling.mkdir(parents=True)
            (sibling / "keep").write_text("unselected skill")

            def install(repo: Path, *options: str) -> subprocess.CompletedProcess[str]:
                result = self.run_installer(
                    repo, "--target", str(target), "--mode", "copy", *options, "sample"
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return result

            install(first)
            selected = target / "sample"
            self.assertFalse((selected / ".release-version").exists())
            (selected / "local-customization").write_text("replaceable installation state")
            installed = self.file_bytes(target)
            self.assertIn("exists, skipping", install(second).stderr)
            self.assertEqual(self.file_bytes(target), installed)
            preview = install(second, "--force", "--dry-run")
            self.assertIn("would copy sample", preview.stdout)
            self.assertEqual(self.file_bytes(target), installed)

            install(second, "--force")
            self.assertEqual(self.file_bytes(selected), self.file_bytes(second / "skills/sample"))
            self.assertFalse((selected / "retired").exists())
            self.assertFalse((selected / "local-customization").exists())
            install(first, "--force")
            self.assertEqual(self.file_bytes(selected), self.file_bytes(first / "skills/sample"))
            self.assertEqual((sibling / "keep").read_text(), "unselected skill")
            self.assertEqual(self.file_bytes(external), external_bytes)
            self.assertEqual([self.file_bytes(repo) for repo in (first, second)], source_bytes)

    def test_symlink_upgrade_rollback_and_mode_change_preserve_release_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.make_repo(root / "release-one")
            second = self.make_repo(root / "release-two")
            for repo, version in ((first, "1"), (second, "2")):
                (repo / ".release-version").write_text(version)
                (repo / "skills/sample/payload").write_text(version)
            source_bytes = [self.file_bytes(repo) for repo in (first, second)]
            target = root / "installed skills"
            probe = root / "symlink-probe"
            try:
                probe.symlink_to(first, target_is_directory=True)
                probe.unlink()
            except OSError as error:
                if os.name == "nt":
                    self.skipTest(f"symlink creation unavailable: {error}")
                raise

            def install(repo: Path, *options: str) -> None:
                result = self.run_installer(repo, "--target", str(target), *options, "sample")
                self.assertEqual(result.returncode, 0, result.stderr)

            selected = target / "sample"
            install(first)
            self.assertEqual(selected.resolve(), (first / "skills/sample").resolve())
            install(second, "--force", "--dry-run")
            self.assertEqual(selected.resolve(), (first / "skills/sample").resolve())
            install(second, "--force")
            self.assertEqual(selected.resolve(), (second / "skills/sample").resolve())
            self.assertEqual((selected.resolve().parents[1] / ".release-version").read_text(), "2")
            install(second, "--force", "--mode", "copy")
            self.assertFalse(selected.is_symlink())
            self.assertEqual(self.file_bytes(selected), self.file_bytes(second / "skills/sample"))
            install(first, "--force")
            self.assertEqual(selected.resolve(), (first / "skills/sample").resolve())
            self.assertEqual([self.file_bytes(repo) for repo in (first, second)], source_bytes)

    def test_real_autoreview_copy_preserves_files_and_runs_from_another_directory(self) -> None:
        repo = SCRIPT.parent.parent
        source = repo / "skills/autoreview"
        source_bytes = self.file_bytes(source)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "installed skills"
            result = self.run_installer(repo, "--target", str(target), "--mode", "copy", "autoreview")
            self.assertEqual(result.returncode, 0, result.stderr)
            installed = target / "autoreview"
            self.assertEqual(self.file_bytes(installed), source_bytes)
            self.assertTrue((repo / ".release-version").is_file())
            self.assertFalse((installed / ".release-version").exists())
            self.assertTrue((installed / "scripts/autoreview.ps1").is_file())
            cwd = root / "separate project 雪"
            cwd.mkdir()
            for option, code in (("--help", 0), ("--version", 0), ("--unknown-option", 2)):
                with self.subTest(option=option):
                    result = subprocess.run(
                        [sys.executable, str(installed / "scripts/autoreview"), option],
                        cwd=cwd, capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, code, result.stderr)
                    if option == "--version":
                        digest = hashlib.sha256((installed / "scripts/autoreview").read_bytes()).hexdigest()
                        self.assertEqual(result.stdout, f"autoreview source-sha256:{digest}\n")
                        self.assertEqual(result.stderr, "")
                    else:
                        self.assertIn("usage:", result.stdout + result.stderr)
                        if option == "--unknown-option":
                            self.assertIn("unrecognized arguments: --unknown-option", result.stderr)
            self.assertEqual(list(cwd.iterdir()), [])
            self.assertEqual(self.file_bytes(installed), source_bytes)
            self.assertEqual(self.file_bytes(source), source_bytes)


if __name__ == "__main__":
    unittest.main()
