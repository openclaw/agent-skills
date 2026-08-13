#!/usr/bin/env python3
"""Zero-model regression tests for the governed Codex high -> xhigh mapping.

The governed GPT-5.6 Sol launch gate certifies only ``medium``/``xhigh`` as Sol
reasoning efforts, so autoreview translates every Codex ``high`` input to
``xhigh`` before launch (see ``reviewer_args`` in the autoreview helper). These
tests pin that translation deterministically: no model call, no network, and
the real helper is only ever run against stub engine binaries and a fake
trufflehog inside temporary git repositories.

Covered input forms:
- global ``--thinking high``
- keyed ``--thinking codex=high``
- inline reviewer ``codex:<model>:high``
- ``AUTOREVIEW_CODEX_THINKING=high`` environment default
- the built-in Codex ``high`` default (no flags at all)

Plus: Codex ``xhigh``/``medium`` pass through unchanged, a dry run of
``--thinking high`` reports effective thinking ``xhigh``, Claude ``high`` stays
``high``, and a stub Codex executable captures the launch argv end-to-end,
proving ``model_reasoning_effort="xhigh"`` reaches the CLI and
``model_reasoning_effort="high"`` never does.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent / "autoreview"

CLEAN_REPORT = {
    "findings": [],
    "overall_correctness": "patch is correct",
    "overall_explanation": "stub review clean",
    "overall_confidence": 0.9,
}

NOTE_SUBSTR = "codex thinking high maps to xhigh"
NOTE_GATE_SUBSTR = "medium/xhigh"
EFFORT_FLAG = "-c"
EFFORT_XHIGH = 'model_reasoning_effort="xhigh"'
EFFORT_HIGH = 'model_reasoning_effort="high"'


def load_helper() -> dict[str, object]:
    return runpy.run_path(str(SCRIPT), run_name="autoreview_under_test")


HELPER = load_helper()


def clear_autoreview_env() -> None:
    for key in list(os.environ):
        if key.startswith("AUTOREVIEW_"):
            os.environ.pop(key, None)


def git(repo: Path, *args: str, check: bool = True) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Autoreview Effort Test",
            "GIT_AUTHOR_EMAIL": "autoreview-effort@example.invalid",
            "GIT_COMMITTER_NAME": "Autoreview Effort Test",
            "GIT_COMMITTER_EMAIL": "autoreview-effort@example.invalid",
        }
    )
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def init_workspace() -> tuple[Path, Path, Path]:
    """Create tempdir with a dirty git repo plus a stub bin directory.

    Returns (tempdir, repo, stubbin). The repo has one committed file and one
    uncommitted modification so --mode local has a review target.
    """
    tempdir = Path(tempfile.mkdtemp(prefix="autoreview-effort-test."))
    repo = tempdir / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Autoreview Effort Test")
    git(repo, "config", "user.email", "autoreview-effort@example.invalid")
    source = repo / "sample.py"
    source.write_text("def answer():\n    return 42\n")
    git(repo, "add", "sample.py")
    git(repo, "commit", "-q", "-m", "initial")
    source.write_text("def answer():\n    return 43\n")
    stubbin = tempdir / "bin"
    stubbin.mkdir()
    return tempdir, repo, stubbin


def write_executable(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def write_codex_stub(stubbin: Path, capture: Path) -> Path:
    body = f"""#!/usr/bin/env python3
import json
import sys

capture = {str(capture)!r}
argv = list(sys.argv[1:])
with open(capture, "w") as handle:
    json.dump(argv, handle)
if "--output-last-message" in argv:
    output_path = argv[argv.index("--output-last-message") + 1]
    with open(output_path, "w") as handle:
        json.dump({json.dumps(CLEAN_REPORT)}, handle)
sys.exit(0)
"""
    return write_executable(stubbin / "codex-stub", body)


def write_trufflehog_stub(stubbin: Path) -> Path:
    return write_executable(stubbin / "trufflehog", "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")


def write_claude_stub(stubbin: Path) -> Path:
    body = """#!/usr/bin/env python3
import sys

if "--version" in sys.argv:
    print("Claude Code 2.1.180")
elif "--help" in sys.argv:
    print(
        "--safe-mode --setting-sources --strict-mcp-config "
        "--disallowedTools --tools"
    )
sys.exit(0)
"""
    return write_executable(stubbin / "claude-stub", body)


def run_helper(
    repo: Path,
    *argv: str,
    stubbin: Path | None = None,
    env_extra: dict[str, str] | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    clear_autoreview_env()
    if stubbin is not None:
        env["PATH"] = f"{stubbin}:{env['PATH']}"
    # Deterministic: empty/nonexistent codex home -> no auth flags, no real config reads.
    env["CODEX_HOME"] = str(repo.parent / "codex-home")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=repo,
        env=env,
        timeout=timeout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class ReviewerArgsMappingTests(unittest.TestCase):
    """Unit-level mapping checks via the real parse_args/reviewer_args path."""

    def setUp(self) -> None:
        clear_autoreview_env()
        self._env = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def _resolve(self, *argv: str) -> tuple[object, str]:
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", ["autoreview", *argv]), contextlib.redirect_stderr(stderr):
            args = HELPER["parse_args"]()
            reviewers = HELPER["reviewer_args"](args)
        return reviewers[0], stderr.getvalue()

    def _launch_flags(self, reviewer: object, tempdir: Path) -> list[str]:
        """Build the real codex launch argv and return it for assertions."""
        # The helper refuses binaries inside the source repo (isolation), so
        # the source repo is a subdir and the stub lives beside it.
        source_repo = tempdir / "source-repo"
        source_repo.mkdir()
        codex_home = tempdir / "codex-home"
        os.environ["CODEX_HOME"] = str(codex_home)
        stub = write_executable(
            tempdir / "codex-bin",
            "#!/bin/sh\nexit 0\n",
        )
        reviewer.codex_bin = str(stub)
        schema = tempdir / "schema.json"
        schema.write_text("{}")
        output = tempdir / "output.json"
        review_root = tempdir / "review-root"
        runtime_root = tempdir / "runtime-root"
        review_root.mkdir()
        runtime_root.mkdir()
        return HELPER["codex_command"](
            reviewer,
            source_repo,
            review_root,
            runtime_root,
            schema,
            output,
            reviewer.model,
            force_file_auth=False,
        )

    def test_global_thinking_high_maps_to_xhigh(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-effort-unit.") as tmp:
            reviewer, stderr = self._resolve("--engine", "codex", "--thinking", "high")
            self.assertEqual(reviewer.thinking, "xhigh")
            self.assertIn(NOTE_SUBSTR, stderr)
            self.assertIn(NOTE_GATE_SUBSTR, stderr)
            cmd = self._launch_flags(reviewer, Path(tmp))
            self.assertIn(EFFORT_FLAG, cmd)
            self.assertIn(EFFORT_XHIGH, cmd)
            self.assertNotIn(EFFORT_HIGH, cmd)

    def test_keyed_codex_high_maps_to_xhigh(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-effort-unit.") as tmp:
            reviewer, stderr = self._resolve("--engine", "codex", "--thinking", "codex=high")
            self.assertEqual(reviewer.thinking, "xhigh")
            self.assertIn(NOTE_SUBSTR, stderr)
            cmd = self._launch_flags(reviewer, Path(tmp))
            self.assertIn(EFFORT_XHIGH, cmd)
            self.assertNotIn(EFFORT_HIGH, cmd)

    def test_inline_reviewer_high_maps_to_xhigh(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-effort-unit.") as tmp:
            reviewer, stderr = self._resolve("--reviewers", "codex:gpt-5.6-sol:high")
            self.assertEqual(reviewer.engine, "codex")
            self.assertEqual(reviewer.thinking, "xhigh")
            self.assertIn(NOTE_SUBSTR, stderr)
            cmd = self._launch_flags(reviewer, Path(tmp))
            self.assertIn(EFFORT_XHIGH, cmd)
            self.assertNotIn(EFFORT_HIGH, cmd)

    def test_env_codex_thinking_high_maps_to_xhigh(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-effort-unit.") as tmp:
            os.environ["AUTOREVIEW_CODEX_THINKING"] = "high"
            reviewer, stderr = self._resolve("--engine", "codex")
            self.assertEqual(reviewer.thinking, "xhigh")
            self.assertIn(NOTE_SUBSTR, stderr)

    def test_builtin_codex_default_maps_to_xhigh(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-effort-unit.") as tmp:
            reviewer, stderr = self._resolve("--engine", "codex")
            self.assertEqual(reviewer.thinking, "xhigh")
            self.assertIn(NOTE_SUBSTR, stderr)

    def test_codex_xhigh_and_medium_pass_through(self) -> None:
        for level in ("xhigh", "medium"):
            with self.subTest(level=level):
                with tempfile.TemporaryDirectory(prefix="autoreview-effort-unit.") as tmp:
                    reviewer, stderr = self._resolve("--engine", "codex", "--thinking", level)
                    self.assertEqual(reviewer.thinking, level)
                    self.assertNotIn(NOTE_SUBSTR, stderr)
                    cmd = self._launch_flags(reviewer, Path(tmp))
                    self.assertIn(f'model_reasoning_effort="{level}"', cmd)

    def test_claude_high_remains_high_without_note(self) -> None:
        reviewer, stderr = self._resolve("--engine", "claude", "--thinking", "high")
        self.assertEqual(reviewer.engine, "claude")
        self.assertEqual(reviewer.thinking, "high")
        self.assertNotIn(NOTE_SUBSTR, stderr)


class DryRunReportingTests(unittest.TestCase):
    """Dry runs print the effective (mapped) thinking with rc 0."""

    def _run_dry(self, *extra: str) -> subprocess.CompletedProcess[str]:
        tempdir, repo, stubbin = init_workspace()
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)
        write_codex_stub(stubbin, tempdir / "captured-argv.json")
        write_trufflehog_stub(stubbin)
        write_claude_stub(stubbin)
        result = run_helper(
            repo,
            "--mode",
            "local",
            "--dry-run",
            *extra,
            stubbin=stubbin,
            env_extra={"CODEX_BIN": str(stubbin / "codex-stub"), "CLAUDE_BIN": str(stubbin / "claude-stub")},
        )
        return result

    def test_dry_run_codex_high_reports_xhigh(self) -> None:
        result = self._run_dry("--engine", "codex", "--thinking", "high")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("thinking: xhigh", result.stdout)
        self.assertIn(NOTE_SUBSTR, result.stderr)

    def test_dry_run_claude_high_remains_high(self) -> None:
        result = self._run_dry("--engine", "claude", "--thinking", "high")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("thinking: high", result.stdout)
        self.assertNotIn(NOTE_SUBSTR, result.stderr)


class EndToEndStubTests(unittest.TestCase):
    """Full helper run with a stub codex: the launch argv proves the mapping."""

    def test_codex_high_launches_with_xhigh_effort(self) -> None:
        tempdir, repo, stubbin = init_workspace()
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)
        capture = tempdir / "captured-argv.json"
        write_codex_stub(stubbin, capture)
        write_trufflehog_stub(stubbin)
        result = run_helper(
            repo,
            "--mode",
            "local",
            "--engine",
            "codex",
            "--thinking",
            "high",
            stubbin=stubbin,
            env_extra={"CODEX_BIN": str(stubbin / "codex-stub")},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("autoreview clean", result.stdout)
        self.assertIn(NOTE_SUBSTR, result.stderr)
        self.assertTrue(capture.is_file(), "stub codex never captured argv")
        captured = json.loads(capture.read_text())
        self.assertIn(EFFORT_XHIGH, captured)
        self.assertNotIn(EFFORT_HIGH, captured)
        self.assertIn("--model", captured)
        self.assertEqual(captured[captured.index("--model") + 1], "gpt-5.6-sol")


if __name__ == "__main__":
    unittest.main()
