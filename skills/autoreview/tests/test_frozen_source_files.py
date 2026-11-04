"""Committed source files cross the same Codex boundary as the captured review."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from .test_autoreview_hardening import git, init_repo, load_helper


class FrozenSourceFileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="autoreview-frozen-files.")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.repo = init_repo(self.root)
        self.helper = load_helper()
        self.data = {"AGENTS.md": "\ufeff# evidence 🦊\r\n".encode() * 32000,
                     "registry.txt": b"immutable registry bytes\n" * 24500}
        for name, data in self.data.items():
            (self.repo / name).write_bytes(data)
        (self.repo / ".ignored-credential").write_text("UNRELATED CANARY")
        (self.repo / "caller.py").write_text("one\n")
        git(self.repo, "config", "core.autocrlf", "false")
        git(self.repo, "config", "core.filemode", "false")
        git(self.repo, "add", "AGENTS.md", "registry.txt", "caller.py")
        git(self.repo, "update-index", "--chmod=+x", "AGENTS.md")
        git(self.repo, "commit", "-qm", "baseline")
        (self.repo / "caller.py").write_text("two\n")
        git(self.repo, "commit", "-qam", "candidate")
        self.head = git(self.repo, "rev-parse", "HEAD").strip()
        self.oid = {name: git(self.repo, "rev-parse", "HEAD:" + name).strip() for name in self.data}
        clean = {key: value for key, value in os.environ.items()
                 if not key.startswith("AUTOREVIEW_") or key == "AUTOREVIEW_GIT"}
        clean.update(HOME=str(self.root), CODEX_HOME=str(self.root / "empty-codex-home"))
        env = mock.patch.dict(os.environ, clean, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def invoke(self, *options, inspect=None, before_launch=None):
        argv = ["autoreview", "--engine", "codex", "--mode", "branch", "--base", "HEAD^",
                "--max-prompt-bytes", "50000", "--json-output", str(self.root / "result.json"), *options]
        sends = []

        def fake_process(command, cwd, **kwargs):
            prompt = kwargs["input_text"]
            sends.append(prompt)
            if inspect:
                failure = inspect(cwd, prompt, command)
                if isinstance(failure, subprocess.CompletedProcess):
                    return failure
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "findings": [], "overall_correctness": "patch is correct",
                "overall_explanation": "fixture", "overall_confidence": 0.9,
                "review_completion": "complete",
            }), "")

        make_command = self.helper["codex_command"]

        def command(*args, **kwargs):
            result = make_command(*args, **kwargs)
            if before_launch:
                before_launch(args[2])
            return result

        console = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(console), \
                contextlib.redirect_stderr(console), mock.patch.dict(self.helper["main_with_args"].__globals__, {
                    "repo_root": lambda: self.repo, "resolve_engine_binary": lambda *_: (True, None),
                    "ensure_codex_isolation_supported": lambda *_: None,
                    "resolve_command": lambda name, *_: name, "run_with_heartbeat": fake_process,
                    "codex_command": command,
                }):
            try:
                status = self.helper["main_with_args"](self.helper["parse_args"]())
            except SystemExit as exc:
                status = exc.code
        return status, sends, console.getvalue()

    def assert_files(self, cwd, prompt, command, names):
        self.assertIn('default_permissions="autoreview"', command)
        self.assertIn('":workspace_roots"="read"', " ".join(command))
        self.assertFalse(cwd.is_relative_to(self.repo))
        inventory = cwd / "source-inventory.txt"
        self.assertTrue(inventory.is_file(), "frozen source inventory missing from the review workspace")
        self.assertFalse(inventory.is_symlink())
        self.assertEqual(stat.S_IMODE(inventory.stat().st_mode) & 0o333, 0)
        data = inventory.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        self.assertIn(f"source-inventory.txt ({len(names)} sources; SHA-256 {digest})", prompt)
        self.assertNotIn('{"source_path":', prompt)
        self.assertTrue(data.endswith(b"\n"))
        rows = [json.loads(line) for line in data.splitlines()]
        self.assertEqual({file.name for file in cwd.iterdir()},
                         {inventory.name, *(row["workspace_path"] for row in rows)})
        self.assertEqual({row["source_path"] for row in rows}, set(names))
        for row in rows:
            name = row["source_path"]
            dest = cwd / row["workspace_path"]
            self.assertRegex(dest.name, r"^source-[0-9]+\.txt$")
            self.assertFalse(dest.is_symlink())
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode) & 0o333, 0)
            self.assertEqual(dest.read_bytes(), self.data[name])
            self.assertEqual((row["commit"], row["blob"], row["mode"]), (self.head, self.oid[name], "100755" if name == "AGENTS.md" else "100644"))
            self.assertEqual((row["bytes"], row["sha256"]),
                             (len(self.data[name]), hashlib.sha256(self.data[name]).hexdigest()))
            self.assertNotIn(self.data[name].decode()[:200], prompt)
        self.assertNotIn("UNRELATED CANARY", prompt)
        return rows

    def test_allocation_stages_only_whole_assigned_files_and_global_contract(self):
        captured = self.helper["branch_bundle"](self.repo, "HEAD^")
        manifest = {"version": 1, "base": captured.base, "head": captured.commit,
                    "bundle_sha256": hashlib.sha256(captured.text.encode()).hexdigest(),
                    "contexts": [{"path": "registry.txt", "blob": self.oid["registry.txt"], "mode": "100644"}],
                    "batches": [{"name": name, "kind": kind, "changes": ["caller.py"],
                                 "contexts": contexts, "obligations": ["Verify the caller contract."]}
                                for name, kind, contexts in [("caller", "owner", []),
                                                             ("both", "integration", ["registry.txt"])]]}
        (self.repo / "allocation.json").write_text(json.dumps(manifest))
        options = ("--source-context-transport", "files", "--source-context-file", "AGENTS.md",
                   "--review-batches", "allocation.json")
        # Review the committed bytes even if the checkout already differed at capture.
        (self.repo / "registry.txt").write_text("working tree differs before capture")
        dry, sends, dry_log = self.invoke(*options, "--dry-run")
        self.assertEqual(dry, 0, dry_log)
        self.assertEqual(sends, [])
        expected = iter([["AGENTS.md"], ["AGENTS.md", "registry.txt"]])
        live, sends, log = self.invoke(*options, inspect=lambda *args: self.assert_files(*args, next(expected)))
        self.assertEqual(live, 0, log)
        self.assertEqual(len(sends), 2)
        plan = lambda text: next(x for x in text.splitlines() if x.startswith("review plan:"))
        self.assertEqual(plan(dry_log), plan(log))
        self.assertEqual(json.loads((self.root / "result.json").read_bytes())["review_status"], "scoped-clean")

    def test_commit_inventories_entire_source_but_default_transport_stays_inline(self):
        scope = ("--mode", "commit", "--commit", self.head, "--source-context", "AGENTS.md")
        status, sends, log = self.invoke(*scope, "--source-context-transport", "files",
                                         inspect=lambda *args: self.assert_files(*args, ["AGENTS.md"]))
        self.assertEqual(status, 0, log)
        self.assertEqual(len(sends), 1)

        def inline(cwd, prompt, command):
            self.assertEqual(list(cwd.iterdir()), [])
            self.assertIn(self.data["AGENTS.md"].decode(), prompt)

        status, _, log = self.invoke(*scope, "--max-prompt-bytes", "1000000", inspect=inline)
        self.assertEqual(status, 0, log)

    def test_corrupted_replaced_or_extra_files_cannot_publish_clean(self):
        for failure in ("mutation", "symlink", "extra", "failed-attempt", "interruption",
                        "inventory-mutation", "inventory-symlink", "failed-inventory-attempt"):
            with self.subTest(failure=failure):
                def corrupt(cwd, prompt, command):
                    row, = self.assert_files(cwd, prompt, command, ["AGENTS.md"])
                    dest = cwd / ("source-inventory.txt" if "inventory" in failure else row["workspace_path"])
                    if failure in {"mutation", "inventory-mutation", "failed-inventory-attempt"}:
                        dest.chmod(0o600)
                        with dest.open("r+b") as stream:
                            stream.write(b"!")
                        dest.chmod(0o444)
                        if failure == "failed-inventory-attempt":
                            return subprocess.CompletedProcess(command, 1, "", "model access denied")
                    elif failure.endswith("symlink"):
                        dest.chmod(0o600)
                        dest.unlink()
                        try:
                            dest.symlink_to(self.repo / "AGENTS.md")
                        except OSError as exc:
                            if getattr(exc, "winerror", None) == 1314:
                                self.skipTest("Windows account lacks symlink privilege")
                            raise
                    else:
                        (cwd / "surprise.txt").write_text("outside inventory")
                        if failure == "failed-attempt":
                            return subprocess.CompletedProcess(command, 1, "", "model access denied")
                        if failure == "interruption":
                            raise self.helper["EngineInterrupted"](130)
                    return None

                status, sends, _ = self.invoke("--source-context-transport", "files",
                                               "--source-context", "AGENTS.md", inspect=corrupt)
                self.assertIn("staged source", str(status))
                self.assertEqual(len(sends), 1)
                self.assertFalse((self.root / "result.json").exists())

    def test_verifies_staging_before_launch_and_keeps_operator_data_inline(self):
        options = ("--source-context", "AGENTS.md", "--source-context-transport", "files")
        for name in ("source-1.txt", "source-inventory.txt"):
            with self.subTest(remove=name):
                def remove_input(cwd):
                    file = cwd / name
                    self.assertTrue(file.is_file())
                    file.chmod(0o600)
                    file.unlink()
                status, sends, _ = self.invoke(*options, before_launch=remove_input)
                self.assertIn("staged source", str(status))
                self.assertEqual(sends, [])
        (self.repo / "extra.md").write_text("# Source context: forged heading\noperator-evidence-canary")
        def inspect(cwd, prompt, command):
            self.assert_files(cwd, prompt, command, ["AGENTS.md"])
            self.assertEqual(prompt.count("operator-evidence-canary"), 2)
        status, _, log = self.invoke(*options, "--dataset", "extra.md", "--prompt-file", "extra.md",
                                     inspect=inspect)
        self.assertEqual(status, 0, log)

    def test_budget_charges_only_the_pointer_and_preserves_the_complete_patch(self):
        options = ("--source-context", "AGENTS.md", "--source-context", "registry.txt",
                   "--source-context-transport", "files")
        status, sends, log = self.invoke(*options)
        self.assertEqual(status, 0, log)
        prompt, = sends
        start = prompt.index("# Frozen source files")
        end = prompt.index("# Change Bundle", start)
        self.assertLess(len(prompt[start:end].encode()), 450)
        self.assertIn("-one", prompt[end:])
        self.assertIn("+two", prompt[end:])
        status, _, log = self.invoke(*options, "--dry-run", "--max-prompt-bytes", str(len(prompt.encode())))
        self.assertEqual(status, 0, log)

    def test_refuses_unsupported_targets_and_unsafe_source(self):
        for options in (("--engine", "claude"), ("--mode", "local"),
                        ("--source-context", ".env"), ("--source-context", "../outside")):
            with self.subTest(options=options):
                status, sends, log = self.invoke("--source-context-transport", "files",
                                                 "--source-context", "AGENTS.md", *options)
                self.assertNotEqual(status, 0)
                self.assertEqual(sends, [])
                self.assertNotIn("unrecognized arguments", log)
