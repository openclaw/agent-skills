"""Explicit prompt budgets preserve complete inputs and prelaunch limits."""
from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "autoreview"
fixture_git = runpy.run_path(str(SCRIPT.with_name("test-review-harness.py")))["fixture_git"]


class PromptBudgetTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        for name in tuple(os.environ):
            if name.startswith("AUTOREVIEW_") and name != "AUTOREVIEW_GIT":
                os.environ.pop(name)

    def arguments(self, *options):
        with mock.patch.object(sys, "argv", [str(SCRIPT), "--engine", "codex", *options]):
            return self.helper["parse_args"]()

    def git(self, repo, *args):
        return fixture_git(repo, *args, check=True, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

    @contextlib.contextmanager
    def committed_fixture(self):
        with tempfile.TemporaryDirectory(prefix="autoreview-prompt-budget-") as directory:
            repo = Path(directory).resolve()
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.name", "Autoreview Test")
            self.git(repo, "config", "user.email", "autoreview@example.invalid")
            self.git(repo, "config", "core.autocrlf", "false")
            line = "# complete owner context 🦊\r\n".encode()
            repeats, padding = divmod(591_025, len(line))
            content = line * repeats + b"x" * padding
            (repo / "owner.py").write_bytes(content)
            (repo / "guide.md").write_text("Keep all owner context and every selected change.\n")
            (repo / "change.txt").write_text("before\n")
            self.git(repo, "add", ".")
            self.git(repo, "commit", "-qm", "baseline")
            (repo / "change.txt").write_text("after 🦊\n", encoding="utf-8")
            self.git(repo, "commit", "-qam", "selected change")
            yield repo, content

    def invoke(self, repo, *options, completion="complete", mutation=None):
        args = self.arguments("--mode", "branch", "--base", "HEAD^",
                              "--source-context-file", "owner.py", "--prompt-file", "guide.md",
                              *options)
        sends = []

        def engine(_args, _repo, prompt):
            sends.append(prompt)
            if mutation:
                mutation()
            return json.dumps({
                "findings": [], "overall_correctness": "patch is correct",
                "overall_explanation": "synthetic review", "overall_confidence": 0.99,
                "review_completion": completion,
            })

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(self.helper["main_with_args"].__globals__, {
            "repo_root": lambda: repo,
            "run_engine": engine,
            "resolve_engine_binary": lambda *_: (True, None),
        }), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                status = self.helper["main_with_args"](args)
            except SystemExit as exc:
                status = exc.code
        return status, sends, stdout.getvalue() + stderr.getvalue()

    def test_parser_keeps_default_and_requires_a_positive_explicit_budget(self):
        self.assertEqual(self.arguments().max_prompt_bytes, 512_000)
        self.assertEqual(self.arguments("--max-prompt-bytes", "1000000").max_prompt_bytes, 1_000_000)
        for value in ("0", "-1", "1.5", "unlimited"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.arguments("--max-prompt-bytes", value)
                self.assertEqual(error.exception.code, 2)

    def test_default_refuses_large_intact_context_in_dry_and_live_runs(self):
        with self.committed_fixture() as (repo, content):
            self.assertEqual(len(content), 591_025)
            for options in ((), ("--dry-run",)):
                with self.subTest(options=options):
                    status, sends, output = self.invoke(repo, *options)
                    self.assertNotEqual(status, 0)
                    self.assertFalse(sends)
                    self.assertIn("intact context leave too little room", str(status) + output)

    def test_explicit_budget_plans_and_delivers_identical_complete_context(self):
        with self.committed_fixture() as (repo, content):
            options = ("--max-prompt-bytes", "650000", "--max-review-passes", "6")
            status, sends, dry_output = self.invoke(repo, *options, "--dry-run")
            self.assertEqual(status, 0, dry_output)
            self.assertFalse(sends)
            status, sends, live_output = self.invoke(repo, *options)
            self.assertEqual(status, 0, live_output)
            self.assertEqual(len(sends), 1)
            plan = lambda text: next(line for line in text.splitlines() if line.startswith("review plan:"))
            self.assertEqual(plan(dry_output), plan(live_output))
            self.assertIn("650000 bytes per pass", plan(live_output))
            captured = self.helper["branch_bundle"](repo, "HEAD^")
            oid = self.git(repo, "rev-parse", "HEAD:owner.py")
            for prompt in sends:
                self.assertLessEqual(len(prompt.encode()), 650_000)
                self.assertEqual(prompt.count(content.decode()), 1)
                self.assertIn(f"commit={captured.commit} blob={oid} mode=100644; context only", prompt)
                self.assertIn("Keep all owner context and every selected change.", prompt)
                self.assertEqual(prompt.rsplit("\n\n# Change Bundle\n", 1)[1], captured.text)
            self.assertEqual((repo / "owner.py").read_bytes(), content)

    def test_explicit_pass_limit_still_refuses_before_reviewer(self):
        with self.committed_fixture() as (repo, _):
            (repo / "change.txt").write_text("selected change 🦊\n" * 8_000, encoding="utf-8")
            self.git(repo, "commit", "-qam", "large selected change")
            for options in ((), ("--dry-run",)):
                with self.subTest(options=options):
                    status, sends, output = self.invoke(
                        repo, "--max-prompt-bytes", "650000", "--max-review-passes", "1", *options,
                    )
                    self.assertNotEqual(status, 0)
                    self.assertFalse(sends)
                    self.assertIn("--max-review-passes allows 1", str(status) + output)
            status, sends, output = self.invoke(
                repo, "--max-prompt-bytes", "650000", "--max-review-passes", "6",
            )
            self.assertEqual(status, 0, output)
            self.assertGreater(len(sends), 1)
            changes = []
            content = (repo / "owner.py").read_bytes().decode()
            for prompt in sends:
                self.assertLessEqual(len(prompt.encode()), 650_000)
                self.assertEqual(prompt.count(content), 1)
                changes.append(prompt.rsplit("\n\n# Change Bundle\n", 1)[1])
            self.assertEqual("".join(changes), self.helper["branch_bundle"](repo, "HEAD^").text)

    def test_final_plan_guard_counts_utf8_bytes_and_rejects_one_byte_over(self):
        args = self.arguments("--max-prompt-bytes", "4")
        for prompt in ("🦊", self.helper["ReviewPass"]("🦊", self.helper["ReviewChunk"](""))):
            with self.subTest(prompt=type(prompt).__name__), contextlib.redirect_stdout(io.StringIO()):
                self.helper["check_review_plan"](args, [prompt])
                args.max_prompt_bytes = 3
                with self.assertRaisesRegex(SystemExit, "--max-prompt-bytes allows 3"):
                    self.helper["check_review_plan"](args, [prompt])
                args.max_prompt_bytes = 4

    def test_larger_budget_does_not_admit_incomplete_or_mutated_review(self):
        for behavior in ("incomplete", "mutation"):
            with self.subTest(behavior=behavior), self.committed_fixture() as (repo, _):
                status, sends, output = self.invoke(
                    repo, "--max-prompt-bytes", "650000",
                    completion="incomplete" if behavior == "incomplete" else "complete",
                    mutation=(lambda: (repo / "owner.py").write_text("changed\n"))
                    if behavior == "mutation" else None,
                )
                self.assertNotEqual(status, 0, output)
                self.assertEqual(len(sends), 1)
                self.assertNotIn("scoped-clean", output)


if __name__ == "__main__":
    unittest.main()
