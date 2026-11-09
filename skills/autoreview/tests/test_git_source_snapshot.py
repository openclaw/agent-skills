"""Native Git membership and index records in full source snapshots."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .test_autoreview_hardening import fixture_git, git, init_repo, load_helper


class GitSourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="autoreview-source-snapshot.")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        home = self.root / "operator"
        home.mkdir()
        platform_keys = (
            "PATH", "PATHEXT", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC",
            "TEMP", "TMP", "TMPDIR", "DEVELOPER_DIR",
        )
        env = {key: os.environ[key] for key in platform_keys if key in os.environ}
        env.update({
            "HOME": str(home), "USERPROFILE": str(home),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        })
        environment = mock.patch.dict(os.environ, env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.repo = init_repo(self.root)
        git(self.repo, "config", "core.autocrlf", "false")
        git(self.repo, "config", "commit.gpgsign", "false")
        self.helper = load_helper()

    def native_index(self):
        # Read bytes so CR/LF inside a pathname cannot be normalized by pipes.
        return fixture_git(
            self.repo, "ls-files", "--stage", "-z", check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.decode("utf-8")

    def test_index_flags_and_ignore_rules_preserve_full_snapshot_membership(self):
        (self.repo / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        tracked = {"ordinary.txt", "skipped.txt", "assumed.txt", "tracked.tmp"}
        for name in tracked:
            (self.repo / name).write_bytes(b"before\n")
        git(self.repo, "add", "-f", ".gitignore", *sorted(tracked))
        git(self.repo, "commit", "-qm", "tracked membership")
        git(self.repo, "update-index", "--skip-worktree", "skipped.txt")
        git(self.repo, "update-index", "--assume-unchanged", "assumed.txt")
        # Index hints must not replace content checks, and exclusions must not
        # hide an already tracked file when tracked/untracked listing is shared.
        (self.repo / "skipped.txt").unlink()
        (self.repo / "assumed.txt").write_bytes(b"after!\n")
        (self.repo / "ignored.tmp").write_bytes(b"not reviewed\n")
        (self.repo / "untracked.txt").write_bytes(b"reviewed\n")
        expected_index = self.native_index()
        calls = mock.Mock(wraps=self.helper["git_bytes"])
        with mock.patch.dict(self.helper["source_tree_snapshot"].__globals__, {"git_bytes": calls}):
            snapshot = self.helper["source_tree_snapshot"](self.repo)
        self.assertEqual(snapshot[1], expected_index)
        files = dict(snapshot[2])
        self.assertEqual(set(files), tracked | {".gitignore", "untracked.txt"})
        self.assertEqual(files["skipped.txt"], ("missing", 0, 0, ""))
        self.assertEqual(files["assumed.txt"][3], hashlib.sha256(b"after!\n").hexdigest())
        # This operation's process budget is the optimization's contract; the
        # spy observes native executions without replacing any Git responses.
        self.assertEqual(sum("ls-files" in call.args[1:] for call in calls.call_args_list), 1)

    def test_merge_conflict_retains_all_index_stages_and_working_content(self):
        source = self.repo / "conflict.txt"
        source.write_bytes(b"base\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        branch = git(self.repo, "symbolic-ref", "--short", "HEAD").strip()
        git(self.repo, "checkout", "-qb", "other")
        source.write_bytes(b"other\n")
        git(self.repo, "commit", "-qam", "other")
        git(self.repo, "checkout", "-q", branch)
        source.write_bytes(b"current\n")
        git(self.repo, "commit", "-qam", "current")
        merged = fixture_git(
            self.repo, "merge", "--no-edit", "other", check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(merged.returncode, 1, merged.stderr)
        expected_index = self.native_index()
        self.assertEqual(len(expected_index.split("\0")[:-1]), 3)
        snapshot = self.helper["source_tree_snapshot"](self.repo)
        self.assertEqual(snapshot[1], expected_index)
        self.assertEqual(set(dict(snapshot[2])), {"conflict.txt"})
        self.assertEqual(dict(snapshot[2])["conflict.txt"][3], hashlib.sha256(source.read_bytes()).hexdigest())

    @unittest.skipIf(os.name == "nt", "Windows forbids control characters in filenames")
    def test_tag_and_stage_looking_filenames_keep_exact_paths(self):
        oid = "a" * 40
        tracked = {"tracked\tname\r\n.txt", f"? 100644 {oid} 0\ttracked"}
        untracked = {
            f"100644 {oid} 0\tplain-stage", f"H 100644 {oid} 0\tH-stage",
            f"S 100644 {oid} 0\tS-stage", f"M 100644 {oid} 3\tM-stage",
            "? raw\r\nname", "trailing\n",
        }
        for name in tracked | untracked:
            (self.repo / name).write_bytes(b"before\n")
        git(self.repo, "add", "--", *sorted(tracked))
        git(self.repo, "commit", "-qm", "literal paths")
        before = self.helper["source_tree_snapshot"](self.repo)
        self.assertEqual(before[1], self.native_index())
        self.assertEqual(set(dict(before[2])), tracked | untracked)
        # A name resembling Git's tagged metadata is still an independently
        # fingerprinted untracked source, including when its bytes change.
        changed = f"H 100644 {oid} 0\tH-stage"
        (self.repo / changed).write_bytes(b"after!\n")
        after = self.helper["source_tree_snapshot"](self.repo)
        self.assertNotEqual(after, before)
        self.assertEqual(after[1], before[1])
        self.assertEqual(dict(after[2])[changed][3], hashlib.sha256(b"after!\n").hexdigest())

    def test_local_text_diff_needs_no_gitlink_head_lookup(self):
        source = self.repo / "ordinary.txt"
        source.write_bytes(b"before\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        source.write_bytes(b"after\n")
        calls = mock.Mock(wraps=self.helper["git_result"])
        with mock.patch.dict(self.helper["local_bundle"].__globals__, {"git_result": calls}):
            bundle = self.helper["local_bundle"](self.repo)
        self.assertEqual(bundle.paths, {"ordinary.txt"})
        self.assertIn("-before\n+after", bundle.text)
        self.assertFalse(any(
            call.args[1:] == ("rev-parse", "--verify", "HEAD")
            for call in calls.call_args_list
        ))
