"""Literal review scopes must bind capture, prompts and accepted finding paths."""
import argparse
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from .test_autoreview_hardening import git, init_repo, load_helper


class PathScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="autoreview-path-scope.")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = init_repo(self.root)
        self.helper = load_helper()
        for name in ("selected/a.py", "selected/b.py", "other.py", "literal[1].py", "literal1.py"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("before\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD").strip()

    def bundle(self, paths, mode="local"):
        return self.helper["build_bundle"](self.repo, mode, self.base if mode == "branch" else None, "HEAD", paths)

    def change(self, name, text="after\n"):
        (self.repo / name).write_text(text, encoding="utf-8")

    def test_local_scope_keeps_both_transitions_and_untracked_members(self):
        self.change("selected/a.py", "staged value\n")
        git(self.repo, "add", "selected/a.py")
        self.change("selected/a.py", "working value\n")
        self.change("selected/new.py", "new value\n")
        self.change("other.py", "outside value\n")
        (self.repo / "outside.bin").write_bytes(b"\0binary")
        captured = self.bundle(["selected"])
        self.assertEqual(captured.paths, {"selected/a.py", "selected/new.py"})
        self.assertEqual(captured.selected_paths, ("selected",))
        for value in ("staged value", "working value", "new value"):
            self.assertIn(value, captured.text)
        self.assertNotIn("outside value", captured.text)
        self.assertNotIn("outside.bin", captured.text)
        self.assertEqual([item.path for item in captured.mixed], ["selected/a.py"])
        self.helper["verify_mixed_sources"](self.repo, captured.mixed)

    def test_branch_and_commit_scope_read_committed_bytes(self):
        self.change("selected/a.py", "committed selected\n")
        self.change("other.py", "committed outside\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "candidate")
        self.change("selected/a.py", "dirty selected\n")
        for mode in ("branch", "commit"):
            with self.subTest(mode=mode):
                captured = self.bundle(["selected/a.py"], mode)
                self.assertEqual(captured.paths, {"selected/a.py"})
                self.assertIn("committed selected", captured.text)
                self.assertNotIn("committed outside", captured.text)
                self.assertNotIn("dirty selected", captured.text)

    def test_deleted_paths_do_not_need_to_exist(self):
        (self.repo / "selected/a.py").unlink()
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "delete selected")
        for mode in ("branch", "commit"):
            self.assertEqual(self.bundle(["selected/a.py"], mode).paths, {"selected/a.py"})

    def test_literal_names_and_repeated_paths(self):
        self.change("literal[1].py")
        self.change("literal1.py")
        self.change("selected/a.py")
        captured = self.bundle(["literal[1].py", "selected/a.py", "literal[1].py"])
        self.assertEqual(captured.paths, {"literal[1].py", "selected/a.py"})
        self.assertEqual(captured.selected_paths, ("literal[1].py", "selected/a.py"))

    def test_repository_root_and_absolute_file_scope(self):
        self.change("selected/a.py")
        self.change("other.py")
        for root in (".", str(self.repo)):
            self.assertEqual(self.bundle([root]).paths, {"selected/a.py", "other.py"})
        self.assertEqual(self.bundle([str(self.repo / "selected/a.py")]).paths, {"selected/a.py"})

    @unittest.skipIf(os.name == "nt", "POSIX literal backslash filename")
    def test_backslash_is_not_a_posix_separator(self):
        self.change(r"selected\a.py", "literal backslash\n")
        self.change("selected/a.py", "directory path\n")
        captured = self.bundle([r"selected\a.py"])
        self.assertEqual(captured.paths, {r"selected\a.py"})
        self.assertIn("literal backslash", captured.text)
        self.assertNotIn("directory path", captured.text)

    def test_scope_rejects_traversal_and_outside_absolute_paths(self):
        for path in ("", "../other", "selected/../other.py", str(self.root / "outside")):
            with self.subTest(path=path), self.assertRaisesRegex(SystemExit, "--path"):
                self.bundle([path])

    def test_scope_rejects_symlink_escape(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.repo / "escape").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(SystemExit, "--path"):
            self.bundle(["escape/child.py"])

    def test_empty_selected_delta_fails_in_each_mode(self):
        self.change("other.py")
        for mode in ("local", "branch", "commit"):
            # Commit mode reviews the root commit here; an absent path is empty.
            with self.subTest(mode=mode), self.assertRaisesRegex(SystemExit, "no .*changes"):
                self.bundle(["absent.py"], mode)

    def test_sensitive_selected_inputs_still_mark_the_review_incomplete(self):
        self.change(".env", "SYNTHETIC=private\n")
        captured = self.bundle([".env"])
        self.assertIn(self.helper["REVIEW_SECURITY_OMISSION"], captured.text)
        self.assertNotIn("SYNTHETIC", captured.text)
        self.assertEqual(captured.paths, set())

    def parse(self, *args):
        with mock.patch.object(sys, "argv", ["autoreview", *args]):
            return self.helper["parse_args"]()

    def test_partial_scope_refuses_whole_branch_exports_and_batches(self):
        for args in (("--review-batches", "batches.json"),
                     ("--preflight-output", "report.md", "--preflight-repo", "example/repo")):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.parse("--path", "selected", *args)

    def test_main_publishes_scope_and_limits_prompts_and_finding_authority(self):
        self.change("selected/a.py")
        self.change("other.py", "excluded implementation\n")
        output = self.root / "report.json"
        args = self.parse("--mode", "local", "--path", "selected", "--json-output", str(output))
        report = {"findings": [], "overall_correctness": "patch is correct",
                  "overall_explanation": "fixture", "overall_confidence": 1}

        def review(_args, _reviewers, _repo, prompts, captured, _evidence):
            self.assertEqual(captured.paths, {"selected/a.py"})
            for entry in prompts:
                prompt = entry.prompt if hasattr(entry, "prompt") else entry
                self.assertIn("partial review", prompt)
                self.assertNotIn("excluded implementation", prompt)
            return [("fixture", self.helper["ReviewResult"](copy.deepcopy(report), True))]

        stdout = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            with mock.patch.dict(self.helper["main_with_args"].__globals__, {"run_review_passes": review}), \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.helper["main_with_args"](args), 0)
        finally:
            os.chdir(previous)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["selected_paths"], ["selected"])
        self.assertIn("literal path scope (partial review)", stdout.getvalue())


class CodexBinarySelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="autoreview-codex-choice.")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.helper = load_helper()
        self.wrapper_dir = self.root / "wrappers"
        self.native_dir = self.root / "native"
        for directory in (self.wrapper_dir, self.native_dir):
            directory.mkdir()
        self.wrapper = self.wrapper_dir / ("codex.cmd" if os.name == "nt" else "codex")
        self.native = self.native_dir / "codex.exe"
        for path in (self.wrapper, self.native):
            path.write_text("fixture", encoding="utf-8")
            path.chmod(0o755)
        self.path = os.pathsep.join((str(self.repo), ".", "relative", str(self.wrapper_dir), str(self.native_dir)))

    def select(self, explicit=False, binary="codex"):
        args = argparse.Namespace(codex_bin=binary, codex_bin_explicit=explicit)
        with mock.patch.dict(os.environ, {"PATH": self.path}):
            return Path(self.helper["select_codex_binary"](args, self.repo))

    def test_default_prefers_windows_native_and_keeps_posix_path_order(self):
        hostile = self.repo / "codex.exe"
        hostile.write_text("repository executable", encoding="utf-8")
        hostile.chmod(0o755)
        self.assertEqual(self.select(), self.native if os.name == "nt" else self.wrapper)

    def test_explicit_command_and_explicit_path_keep_operator_choice(self):
        self.assertEqual(self.select(True), self.wrapper)
        self.assertEqual(self.select(True, str(self.native)), self.native)

    def test_falls_back_to_wrapper_when_native_is_absent(self):
        self.native.unlink()
        self.assertEqual(self.select(), self.wrapper)

    def test_cli_and_environment_overrides_are_explicit(self):
        for environment, argv in (({}, []), ({"CODEX_BIN": "codex"}, []), ({}, ["--codex-bin=codex"])):
            with self.subTest(environment=environment, argv=argv), \
                    mock.patch.dict(os.environ, environment, clear=True), \
                    mock.patch.object(sys, "argv", ["autoreview", *argv]):
                args = self.helper["parse_args"]()
                self.assertEqual(args.codex_bin_explicit, bool(environment or argv))


if __name__ == "__main__":
    unittest.main()
