"""Explicit allocations retain one range, whole contracts and aggregate refusals."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import runpy
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "autoreview"
fixture_git = runpy.run_path(str(SCRIPT.with_name("test-review-harness.py")))["fixture_git"]


class ReviewBatchTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        for name in tuple(os.environ):
            if name.startswith("AUTOREVIEW_") and name != "AUTOREVIEW_GIT":
                os.environ.pop(name)

    def git(self, repo, *args):
        return fixture_git(repo, *args, check=True, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

    @contextlib.contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory(prefix="autoreview-batches-") as directory:
            repo = Path(directory).resolve() / "repo"
            repo.mkdir()
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.name", "Autoreview Test")
            self.git(repo, "config", "user.email", "autoreview@example.invalid")
            self.git(repo, "config", "core.autocrlf", "false")
            self.git(repo, "config", "core.filemode", "false")
            (repo / ".gitignore").write_bytes(b".review/\n")
            for name in ("first.py", "second.py", "retired.py"):
                (repo / name).write_bytes(b"value = 1\n")
            (repo / "contract.py").write_bytes(b"# whole contract\r\n" * 2_000)
            (repo / "global.md").write_bytes(b"GLOBAL WHOLE OWNER\n")
            self.git(repo, "add", ".")
            self.git(repo, "commit", "-qm", "baseline")
            (repo / "first.py").write_bytes("value = 2  # fox 🦊\n".encode("utf-8"))
            (repo / "second.py").write_bytes(b"value = 3\n")
            self.git(repo, "update-index", "--chmod=+x", "second.py")
            (repo / "retired.py").unlink()
            self.git(repo, "commit", "-qam", "selected change")
            (repo / ".review").mkdir()
            yield repo

    def manifest(self, repo):
        capture = self.helper["branch_bundle"](repo, "HEAD^")
        return {
            "version": 1, "base": capture.base, "head": capture.commit,
            "bundle_sha256": hashlib.sha256(capture.text.encode()).hexdigest(),
            "contexts": [{"path": "contract.py", "blob": self.git(repo, "rev-parse", "HEAD:contract.py"),
                          "mode": "100644"}],
            "batches": [
                {"name": "first-owner", "kind": "owner", "changes": ["first.py", "retired.py"],
                 "contexts": ["contract.py"], "obligations": ["Validate the owner and retirement."]},
                {"name": "integration", "kind": "integration", "changes": ["second.py", "first.py"],
                 "contexts": ["contract.py"], "obligations": ["Validate first-to-second value handoff."]},
            ],
        }

    def write_manifest(self, repo, manifest):
        (repo / ".review/batches.json").write_bytes(json.dumps(manifest).encode("utf-8"))

    def invoke(self, repo, *options, engine=None, allocated=True, real_engine_probe=False, codex_transport=None, source_context=True):
        argv = [str(SCRIPT), "--mode", "branch", "--base", "HEAD^", "--engine", "codex",
                "--max-priority", "P2", "--review-batches", ".review/batches.json",
                "--source-context-file", "global.md", "--max-prompt-bytes", "80000",
                "--max-review-passes", "2", "--json-output", str(repo.parent / "result.json"),
                *options]
        if not allocated:
            offset = argv.index("--review-batches")
            del argv[offset:offset + 2]
        if not source_context:
            offset = argv.index("--source-context-file")
            del argv[offset:offset + 2]
        with mock.patch.object(sys, "argv", argv):
            args = self.helper["parse_args"]()
        sends = []

        def run(_args, _repo, prompt):
            sends.append(prompt)
            report = {
                "findings": [], "overall_correctness": "patch is correct",
                "overall_explanation": "synthetic assignment", "overall_confidence": 0.99,
                "review_completion": "complete",
            }
            return json.dumps(engine(len(sends), report) if engine else report)

        output = io.StringIO()
        # Substitute the CLI transport, keeping capture, dispatch, retry
        # classification and publication on their supported paths.
        transport_patches = ({
            "ensure_codex_isolation_supported": lambda *_: None,
            "codex_subscription_login_missing": lambda *_: False,
            "run_with_heartbeat": codex_transport,
        } if codex_transport is not None else {})
        with mock.patch.dict(self.helper["main_with_args"].__globals__, {
            **transport_patches,
            "repo_root": lambda: repo,
            "run_engine": self.helper["run_engine"] if codex_transport else run,
            "discover_repo_root": lambda _: repo,
            "resolve_engine_binary": (self.helper["resolve_engine_binary"] if real_engine_probe
                                      else lambda *_: (True, None)),
        }), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                status = self.helper["main_with_args"](args)
            except SystemExit as exc:
                status = exc.code
            except self.helper["ReviewerUnavailable"] as exc:
                status = str(exc)
        return status, sends, output.getvalue()

    @contextlib.contextmanager
    def external_fixture(self, path="src/client-credential-operations.ts", content=None,
                         object_format="sha1"):
        with self.fixture() as repo:
            upstream = repo.parent / "upstream"
            upstream.mkdir()
            self.git(upstream, "init", "-q", "--object-format=" + object_format)
            self.git(upstream, "config", "user.name", "Autoreview Test")
            self.git(upstream, "config", "user.email", "autoreview@example.invalid")
            self.git(upstream, "config", "core.autocrlf", "false")
            source = upstream / path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(content if content is not None else b"// full external contract\r\n")
            self.git(upstream, "add", ".")
            self.git(upstream, "commit", "-qm", "external contract")
            manifest = {
                "version": 1, "root": str(upstream),
                "commit": self.git(upstream, "rev-parse", "HEAD"),
                "files": [{"path": path, "blob": self.git(upstream, "rev-parse", "HEAD:" + path),
                           "mode": "100644"}],
            }
            (repo / ".review/external.json").write_text(json.dumps(manifest))
            self.write_manifest(repo, self.manifest(repo))
            yield repo, upstream, source, manifest


    @contextlib.contextmanager
    def primary_linked_fixture(self):
        with self.external_fixture() as (repo, upstream, _, manifest):
            linked = repo.parent / "primary-linked"
            self.git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
            shutil.copytree(repo / ".review", linked / ".review")
            git_dir = Path(self.git(linked, "rev-parse", "--absolute-git-dir"))
            common = (linked / self.git(linked, "rev-parse", "--git-common-dir")).resolve()
            yield linked, upstream, git_dir, common, manifest

    @unittest.skipUnless(os.name == "posix", "uses an inert local shell wrapper")
    def test_git_metadata_cannot_supply_the_initial_git_executable(self):
        for role in ("primary", "external"):
            fixture = self.primary_linked_fixture if role == "primary" else self.linked_external_fixture
            with self.subTest(role=role), fixture() as (repo, _, git_dir, _, _):
                marker = repo.parent / "metadata-executable-ran"
                wrapper = git_dir / "fixture-git"
                wrapper.write_text("#!/bin/sh\nprintf ran > " + shlex.quote(str(marker))
                                   + "\nexec /usr/bin/git \"$@\"\n")
                wrapper.chmod(0o700)
                # The executable is benign, but its storage belongs to the
                # reviewed Git repository before the first version probe.
                with mock.patch.dict(os.environ, {"AUTOREVIEW_GIT": str(wrapper)}):
                    status, sends, _ = self.invoke(
                        repo, "--external-source-context-file", ".review/external.json")
                self.assertFalse(marker.exists(), "metadata-owned Git must never execute")
                self.assertNotEqual(status, 0)
                self.assertFalse(sends)

    def test_primary_linked_metadata_is_protected_with_unrelated_external_source(self):
        for with_external, destination_kind in ((external, kind) for external in (False, True)
                                                 for kind in ("head", "config", "object")):
            with self.subTest(external=with_external, kind=destination_kind), self.primary_linked_fixture() as fixture:
                repo, _, git_dir, common, _ = fixture
                oid = self.git(repo, "rev-parse", "HEAD:first.py")
                destination = {"head": git_dir / "HEAD", "config": common / "config",
                               "object": common / "objects" / oid[:2] / oid[2:]}[destination_kind]
                before = destination.read_bytes()
                identity = destination.stat().st_ino
                probe = mock.Mock(wraps=self.helper["require_output_ready"])
                with mock.patch.dict(self.helper["main_with_args"].__globals__, {"require_output_ready": probe}):
                    status, sends, _ = self.invoke(
                        repo, *(["--external-source-context-file", ".review/external.json"] if with_external else []),
                        "--status-output", str(destination))
                self.assertIn("--status-output must point outside", str(status))
                self.assertFalse(sends)
                probe.assert_not_called()
                self.assertEqual(destination.read_bytes(), before)
                self.assertEqual(destination.stat().st_ino, identity)
                self.assertEqual(self.helper["SOURCE_METADATA_BINDINGS"].get(), ())

    def test_pre_output_metadata_binding_survives_until_capture_and_publication(self):
        for phase in ("probe", "unlink", "capture"):
            with self.subTest(phase=phase), self.linked_external_fixture() as fixture:
                repo, linked, git_dir, common, manifest = fixture
                second_common = repo.parent / "second-common"
                second_admin = repo.parent / "second-admin"
                shutil.copytree(common, second_common)
                shutil.copytree(git_dir, second_admin)
                (second_admin / "commondir").write_text(str(second_common) + "\n")
                pointer = linked / ".git"
                original_pointer = pointer.read_bytes()
                pointer.write_text("gitdir: " + str(second_admin) + "\n")
                # Stock Git confirms the second storage describes the exact
                # same pinned commit before the actual admission starts.
                self.assertEqual(self.git(linked, "rev-parse", "HEAD"), manifest["commit"])
                self.assertEqual(self.git(linked, "rev-parse", "HEAD:" + manifest["files"][0]["path"]),
                                 manifest["files"][0]["blob"])
                pointer.write_bytes(original_pointer)
                destination = second_admin / "HEAD" if phase == "unlink" else second_common / "config"
                before = destination.read_bytes()
                inode = destination.stat().st_ino
                switched = False
                def switch():
                    nonlocal switched
                    if not switched:
                        pointer.write_text("gitdir: " + str(second_admin) + "\n")
                        switched = True
                real_prepare = self.helper["prepare_output_paths"]
                real_capture = self.helper["capture_external_source_contexts"]
                def prepare(*args):
                    if phase == "probe":
                        switch()
                    result = real_prepare(*args)
                    if phase == "unlink":
                        switch()
                    return result
                def capture(*args):
                    if phase == "capture":
                        switch()
                    return real_capture(*args)
                real_probe = tempfile.NamedTemporaryFile
                probes_after_switch = []
                def probe(*args, **kwargs):
                    if switched and Path(kwargs.get("dir", ".")) == second_common:
                        probes_after_switch.append(kwargs["dir"])
                    return real_probe(*args, **kwargs)
                with mock.patch.dict(self.helper["main_with_args"].__globals__, {
                    "prepare_output_paths": prepare, "capture_external_source_contexts": capture,
                }), mock.patch.object(tempfile, "NamedTemporaryFile", side_effect=probe):
                    option = "--status-output" if phase == "unlink" else "--json-output"
                    status, sends, _ = self.invoke(
                        repo, "--external-source-context-file", ".review/external.json",
                        option, str(destination))
                self.assertTrue(switched)
                self.assertEqual(destination.read_bytes(), before, "newly selected metadata must remain unchanged")
                self.assertFalse(probes_after_switch, "no readiness probe may write into newly selected metadata")
                self.assertIn("metadata changed after admission", str(status))
                self.assertFalse(sends)
                self.assertEqual(destination.stat().st_ino, inode)
                self.assertFalse(list(second_common.glob(".autoreview-output-probe.*")))
                self.assertEqual(self.helper["SOURCE_METADATA_BINDINGS"].get(), ())

    @contextlib.contextmanager
    def linked_external_fixture(self):
        with self.external_fixture() as (repo, upstream, _, manifest):
            linked = repo.parent / "linked-source"
            self.git(upstream, "worktree", "add", "--detach", str(linked), manifest["commit"])
            manifest = {**manifest, "root": str(linked)}
            (repo / ".review/external.json").write_text(json.dumps(manifest))
            git_dir = Path(self.git(linked, "rev-parse", "--absolute-git-dir"))
            common = (linked / self.git(linked, "rev-parse", "--git-common-dir")).resolve()
            yield repo, linked, git_dir, common, manifest

    def test_linked_external_metadata_is_protected_before_output_mutation(self):
        for option, kind in (("--status-output", "head"), ("--preflight-output", "head"),
                             ("--json-output", "config"), ("--json-output", "object")):
            with self.subTest(option=option, kind=kind), self.linked_external_fixture() as fixture:
                repo, linked, git_dir, common, manifest = fixture
                oid = manifest["files"][0]["blob"]
                destination = {"head": git_dir / "HEAD", "config": common / "config",
                               "object": common / "objects" / oid[:2] / oid[2:]}[kind]
                before = destination.read_bytes()
                identity = destination.stat()
                extra = ["--preflight-repo", "example/repository"] if option == "--preflight-output" else []
                probe = mock.Mock(wraps=self.helper["require_output_ready"])
                with mock.patch.dict(self.helper["main_with_args"].__globals__, {"require_output_ready": probe}):
                    status, sends, _ = self.invoke(
                        repo, "--external-source-context-file", ".review/external.json",
                        option, str(destination), *extra,
                    )
                self.assertIn(option + " must point outside", str(status))
                probe.assert_not_called()
                self.assertFalse(sends)
                self.assertEqual(destination.read_bytes(), before)
                self.assertEqual(destination.stat().st_ino, identity.st_ino)
                self.assertEqual(self.git(linked, "rev-parse", "HEAD"), manifest["commit"])
                self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())

    def test_linked_alternate_object_store_is_refused_before_output_mutation(self):
        with self.linked_external_fixture() as (repo, _, _, common, _):
            alternate = repo.parent / "alternate-objects"
            alternate.mkdir()
            pointer = common / "objects/info/alternates"
            pointer.write_text(str(alternate) + "\n")
            before = pointer.read_bytes()
            probe = mock.Mock(wraps=self.helper["require_output_ready"])
            with mock.patch.dict(self.helper["main_with_args"].__globals__, {"require_output_ready": probe}):
                status, sends, _ = self.invoke(
                    repo, "--external-source-context-file", ".review/external.json",
                    "--status-output", str(pointer),
                )
            self.assertIn("alternate object stores are unsupported", str(status))
            probe.assert_not_called()
            self.assertFalse(sends)
            self.assertEqual(pointer.read_bytes(), before)
            self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())

    @unittest.skipIf(os.name == "nt", "requires local symlink privilege")
    def test_linked_metadata_stays_protected_when_output_parent_changes_during_review(self):
        with self.linked_external_fixture() as (repo, linked, git_dir, _, manifest):
            outside = repo.parent / "reports"
            outside.mkdir()
            alias = repo.parent / "report-alias"
            alias.symlink_to(outside, target_is_directory=True)
            destination = git_dir / "HEAD"
            before = destination.read_bytes()
            def retarget(number, report):
                if number == 2:
                    alias.unlink()
                    alias.symlink_to(git_dir, target_is_directory=True)
                return report
            status, sends, _ = self.invoke(
                repo, "--external-source-context-file", ".review/external.json",
                "--json-output", str(alias / "HEAD"), engine=retarget,
            )
            self.assertEqual(len(sends), 2)
            self.assertIn("output parent changed after admission", str(status))
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(self.git(linked, "rev-parse", "HEAD"), manifest["commit"])
            self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())

    def test_external_capture_batches_objects_and_revalidates_each_fence(self):
        with self.external_fixture() as (repo, upstream, source, manifest):
            expected = {}
            for index in range(100):
                relative = f"src/part-{index:03}.py"
                content = (f"# complete source {index} 🦊\r\nvalue = {index}\r\n" if index % 3 else "")
                (upstream / relative).write_bytes(content.encode("utf-8"))
                expected[relative] = content
            self.git(upstream, "add", ".")
            self.git(upstream, "commit", "-qm", "many source files")
            manifest["commit"] = self.git(upstream, "rev-parse", "HEAD")
            manifest["files"] = []
            for entry in self.git(upstream, "ls-tree", "-rz", "HEAD").split("\0"):
                if not entry:
                    continue
                metadata, relative = entry.split("\t", 1)
                if relative in expected:
                    mode, _, oid = metadata.split()
                    manifest["files"].append({"path": relative, "mode": mode, "blob": oid})
            (repo / ".review/external.json").write_text(json.dumps(manifest))
            args = argparse.Namespace(external_source_context_file=[".review/external.json"])
            args.external_source_manifests = self.helper["read_external_source_manifests"](args, repo)
            captured = self.helper["CapturedBundle"]("", set(), commit=self.git(repo, "rev-parse", "HEAD"))
            empty = self.helper["EvidenceInputs"]("", [], [])
            binding = mock.Mock(wraps=self.helper["external_source_binding"])
            reads = mock.Mock(wraps=self.helper["git_bytes"])
            path_scans = mock.Mock(wraps=self.helper["safe_engine_path"])
            with mock.patch.dict(self.helper["capture_external_source_inputs"].__globals__, {
                "external_source_binding": binding, "git_bytes": reads, "safe_engine_path": path_scans,
            }):
                evidence = self.helper["capture_external_source_inputs"](args, repo, captured, empty)
                records = [record for record in evidence.files if isinstance(record, self.helper["ExternalSourceContext"])]
                self.assertEqual({record.source.raw_path: record.source.source.content for record in records}, expected)
                self.assertLessEqual(reads.call_count, 12, "100 files must not cause per-file Git processes")
                self.assertLessEqual(path_scans.call_count, 12, "object reads must not rescan PATH per file")
                self.assertEqual(binding.call_count, 2)
                initial_reads = reads.call_count
                reads.reset_mock()
                binding.reset_mock()
                self.helper["verify_evidence"](repo, evidence.files)
                self.assertEqual(reads.call_count, initial_reads, "each fence must perform fresh immutable reads")
                self.assertEqual(binding.call_count, 2, "metadata binding cannot survive across fences")
                # Changing a selected file after a successful fence must fail the
                # next one, even if its immutable blob is shared with other files.
                (upstream / next(iter(expected))).write_text("changed between fences\n")
                with self.assertRaisesRegex(SystemExit, "evidence changed"):
                    self.helper["verify_evidence"](repo, evidence.files)


    def test_multiple_external_roots_reuse_scope_and_recheck_every_binding(self):
        with self.fixture() as repo:
            roots = []
            commits = []
            for index in range(3):
                root = repo.parent / f"external-{index}"
                root.mkdir()
                self.git(root, "init", "-q")
                self.git(root, "config", "user.name", "Autoreview Test")
                self.git(root, "config", "user.email", "autoreview@example.invalid")
                (root / "source.py").write_bytes(f"value = {index}\n".encode("utf-8"))
                self.git(root, "add", ".")
                self.git(root, "commit", "-qm", "external source")
                roots.append(root)
                commits.append(self.git(root, "rev-parse", "HEAD"))
            scopes = mock.Mock(wraps=self.helper["metadata_source_roots"])
            reads = mock.Mock(wraps=self.helper["git_bytes"])
            with mock.patch.dict(self.helper["capture_external_source_contexts"].__globals__, {
                "metadata_source_roots": scopes, "git_bytes": reads,
            }), self.helper["repository_metadata_scope"]((repo, *roots)):
                records = [
                    self.helper["capture_external_source_context"](repo, root, "source.py", commit)
                    for root, commit in zip(roots, commits)
                ]
                self.assertEqual([record.source.source.content for record in records],
                                 [f"value = {index}\n" for index in range(3)])
                self.helper["verify_evidence"](repo, records)
                # Multiple roots share one admitted containment set. Capturing
                # and verifying each root must not rebuild that complete set.
                self.assertEqual(scopes.call_count, 1)
                # Reuse is only structural: metadata in another retained root
                # must still stop a new capture before its first Git process.
                (roots[-1] / ".git/objects/info/alternates").write_text("unexpected\n")
                reads.reset_mock()
                with self.assertRaisesRegex(SystemExit, "metadata changed after admission"):
                    self.helper["capture_external_source_context"](
                        repo, roots[0], "source.py", commits[0])
                reads.assert_not_called()
            self.assertEqual(self.helper["SOURCE_METADATA_BINDINGS"].get(), ())
            self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())


    def test_external_batch_rejects_malformed_blob_stream(self):
        with self.external_fixture() as (repo, upstream, _, manifest):
            original = self.helper["git_bytes"]
            for damage in ("truncated", "type", "extra"):
                def read(*args, **kwargs):
                    result = original(*args, **kwargs)
                    if args[1:3] == ("cat-file", "--batch"):
                        if damage == "truncated":
                            result.stdout = result.stdout[:-1]
                        elif damage == "type":
                            result.stdout = result.stdout.replace(b" blob ", b" tree ", 1)
                        else:
                            result.stdout += b"unrequested output\n"
                    return result
                with self.subTest(damage=damage), mock.patch.dict(
                    self.helper["capture_external_source_context"].__globals__, {"git_bytes": read},
                ), self.assertRaisesRegex(SystemExit, "committed source batch response"):
                    self.helper["capture_external_source_context"](
                        repo, upstream, manifest["files"][0]["path"], manifest["commit"],
                    )


    def test_external_batch_preserves_distinct_commits_for_the_same_path(self):
        with self.external_fixture() as (repo, upstream, source, manifest):
            old_content = source.read_bytes().decode("utf-8")
            old_commit = manifest["commit"]
            source.write_text("// second committed contract\n")
            self.git(upstream, "commit", "-qam", "second contract")
            new_commit = self.git(upstream, "rev-parse", "HEAD")
            second = {**manifest, "commit": new_commit, "files": [{
                **manifest["files"][0], "blob": self.git(upstream, "rev-parse", "HEAD:" + manifest["files"][0]["path"]),
            }]}
            (repo / ".review/second.json").write_text(json.dumps(second))
            status, sends, output = self.invoke(
                repo, "--external-source-context-file", ".review/external.json",
                "--external-source-context-file", ".review/second.json",
            )
            self.assertEqual(status, 0, output)
            for prompt in sends:
                self.assertIn(old_commit, prompt)
                self.assertIn(new_commit, prompt)
                self.assertLess(prompt.index(old_commit), prompt.index(new_commit))
                self.assertIn(old_content, prompt)
                self.assertIn("// second committed contract", prompt)


    def test_external_batch_rejects_metadata_mutation_during_object_read(self):
        with self.external_fixture() as (repo, upstream, _, manifest):
            original = self.helper["git_bytes"]
            def read(*args, **kwargs):
                result = original(*args, **kwargs)
                if args[1:3] == ("cat-file", "--batch"):
                    # The object read succeeds, then the repository gains an
                    # unsupported alternate before the closing metadata fence.
                    (upstream / ".git/objects/info/alternates").write_text("")
                return result
            with mock.patch.dict(self.helper["capture_external_source_context"].__globals__, {"git_bytes": read}):
                with self.assertRaisesRegex(SystemExit, "metadata changed after admission"):
                    self.helper["capture_external_source_context"](
                        repo, upstream, manifest["files"][0]["path"], manifest["commit"],
                    )

    def test_metadata_corroboration_rejects_mutation_after_git_returns(self):
        with self.external_fixture() as (_, upstream, _, _):
            expected = self.helper["repository_metadata"](upstream)
            original = self.helper["git"]
            def read(*args, **kwargs):
                result = original(*args, **kwargs)
                # Git saw the admitted store, but its raw metadata changed
                # before the caller can accept the corroborating path output.
                (upstream / ".git/objects/info/alternates").write_text("")
                return result
            with mock.patch.dict(self.helper["corroborate_repository_metadata"].__globals__, {"git": read}):
                with self.assertRaisesRegex(SystemExit, "metadata changed after admission"):
                    self.helper["corroborate_repository_metadata"](expected)


    def test_invalid_external_manifest_cannot_publish_stage_before_output_admission(self):
        with self.external_fixture() as (repo, upstream, source, _):
            (repo / ".review/external.json").write_text("{invalid JSON")
            before = source.read_bytes()
            argv = [str(SCRIPT), "--mode", "branch", "--base", "HEAD^",
                    "--external-source-context-file", ".review/external.json",
                    "--engine-stage-dir", str(upstream), "--stream-engine-output"]
            persist = mock.Mock(wraps=self.helper["persist_engine_stage"])
            with mock.patch.object(sys, "argv", argv), mock.patch.dict(
                self.helper["main_impl"].__globals__, {
                    "discover_repo_root": lambda _: repo, "persist_engine_stage": persist,
                },
            ), self.assertRaisesRegex(SystemExit, "invalid external source manifest JSON"):
                self.helper["main_impl"]()
            persist.assert_not_called()
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse((upstream / "engine-stage.json").exists())
            self.assertFalse((upstream / ".engine-stage.partial").exists())


    def test_external_sources_cannot_be_output_destinations_before_probes(self):
        with self.external_fixture() as (repo, upstream, source, manifest):
            other = repo.parent / "other-source"
            shutil.copytree(upstream, other)
            (repo / ".review/other.json").write_text(json.dumps({**manifest, "root": str(other)}))
            for destination in (source, other / manifest["files"][0]["path"]):
                before = destination.read_bytes()
                identity = destination.stat()
                for option in ("--json-output", "--output", "--status-output", "--preflight-output",
                               "--engine-stage-dir", "--native-handoff"):
                    # Native handoff is POSIX-only; all other output refusals
                    # still exercise the actual entry point on Windows.
                    if option == "--native-handoff" and os.name == "nt":
                        continue
                    extra = (["--preflight-repo", "example/repository"] if option == "--preflight-output"
                             else ["--engine", "openclaw"] if option == "--native-handoff" else [])
                    with self.subTest(destination=destination, option=option):
                        probe = mock.Mock(side_effect=AssertionError("must reject before any probe"))
                        with mock.patch.dict(self.helper["main_with_args"].__globals__, {"preflight_git": probe}):
                            status, sends, _ = self.invoke(
                                repo, "--external-source-context-file", ".review/external.json",
                                "--external-source-context-file", ".review/other.json",
                                option, str(destination), *extra,
                            )
                        self.assertIn(option + " must point outside", str(status))
                        probe.assert_not_called()
                        self.assertFalse(sends)
                        self.assertEqual(destination.read_bytes(), before)
                        self.assertEqual(destination.stat().st_ino, identity.st_ino)

    @unittest.skipIf(os.name == "nt", "requires local symlink privilege")
    def test_external_output_alias_is_rejected_and_outside_output_is_preserved(self):
        with self.external_fixture() as (repo, upstream, source, _):
            alias = repo.parent / "output-alias"
            alias.symlink_to(source.parent, target_is_directory=True)
            before = source.read_bytes()
            status, sends, _ = self.invoke(
                repo, "--external-source-context-file", ".review/external.json",
                "--json-output", str(alias / source.name),
            )
            self.assertIn("--json-output must point outside", str(status))
            self.assertFalse(sends)
            self.assertEqual(source.read_bytes(), before)
            # A stable operator-owned destination still publishes a complete report.
            outside = repo.parent / "outside"
            outside.mkdir()
            alias.unlink()
            alias.symlink_to(outside, target_is_directory=True)
            status, _, output = self.invoke(
                repo, "--external-source-context-file", ".review/external.json",
                "--json-output", str(alias / "report.json"),
            )
            self.assertEqual(status, 0, output)
            self.assertEqual(json.loads((outside / "report.json").read_text())["review_status"], "scoped-clean")

    @unittest.skipIf(os.name == "nt", "requires local symlink privilege")
    def test_output_parent_retargeted_during_review_cannot_replace_external_source(self):
        with self.external_fixture() as (repo, upstream, source, _):
            outside = repo.parent / "outside"
            outside.mkdir()
            alias = repo.parent / "output-alias"
            alias.symlink_to(outside, target_is_directory=True)
            before = source.read_bytes()
            def retarget(number, report):
                if number == 2:
                    alias.unlink()
                    alias.symlink_to(source.parent, target_is_directory=True)
                return report
            status, sends, _ = self.invoke(
                repo, "--external-source-context-file", ".review/external.json",
                "--json-output", str(alias / source.name), engine=retarget,
            )
            self.assertEqual(len(sends), 2)
            self.assertIn("output parent changed after admission", str(status))
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "requires local symlink privilege")
    def test_ordinary_review_cannot_replace_source_through_retargeted_output_parent(self):
        with self.fixture() as repo:
            self.write_manifest(repo, self.manifest(repo))
            outside = repo.parent / "outside"
            outside.mkdir()
            alias = repo.parent / "output-alias"
            alias.symlink_to(outside, target_is_directory=True)
            source = repo / "first.py"
            before = source.read_bytes()
            def retarget(number, report):
                if number == 2:
                    alias.unlink()
                    alias.symlink_to(repo, target_is_directory=True)
                return report
            status, sends, _ = self.invoke(
                repo, "--json-output", str(alias / source.name), engine=retarget,
            )
            self.assertEqual(len(sends), 2)
            self.assertIn("output parent changed after admission", str(status))
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())

    @unittest.skipUnless(os.name == "nt", "requires native Windows directory junctions")
    def test_windows_junctions_preserve_all_source_boundaries(self):
        with self.external_fixture() as (repo, upstream, source, _):
            trusted = repo.parent / "trusted"
            trusted.mkdir()
            cmd = Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe"
            direct = repo.parent / "source-junction"
            controlled = upstream / "controlled-junction"
            indirect = repo.parent / "indirect-junction"
            safe = repo.parent / "safe-junction"
            for link, target in ((direct, source.parent), (controlled, trusted),
                                 (indirect, controlled), (safe, trusted)):
                subprocess.run([str(cmd), "/d", "/c", "mklink", "/J", str(link), str(target)],
                               check=True, capture_output=True, text=True)
                self.assertEqual(link.lstat().st_reparse_tag, stat.IO_REPARSE_TAG_MOUNT_POINT)
            # The final referent is trusted, but the intermediate source-owned
            # junction can later change. Exercise real metadata even on Python 3.10.
            self.assertTrue(os.path.samefile(indirect, trusted))
            token = self.helper["UNTRUSTED_SOURCE_ROOTS"].set((repo, upstream))
            try:
                for path in (direct / source.name, direct / "new-output.json", indirect / "new-output.json"):
                    with self.subTest(path=path):
                        self.assertFalse(self.helper["external_env_path"](repo, str(path)))
                self.assertTrue(self.helper["external_env_path"](repo, str(safe / "new-output.json")))
            finally:
                self.helper["UNTRUSTED_SOURCE_ROOTS"].reset(token)

    @unittest.skipUnless(os.name == "nt", "requires native Windows path normalization")
    def test_windows_parent_segments_cannot_hide_source_after_a_junction(self):
        with self.external_fixture() as (repo, upstream, source, _):
            deep = repo.parent / "trusted" / "deep"
            deep.mkdir(parents=True)
            alias = repo.parent / "trusted-junction"
            cmd = Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe"
            subprocess.run([str(cmd), "/d", "/c", "mklink", "/J", str(alias), str(deep)],
                           check=True, capture_output=True, text=True)
            candidate = alias / ".." / upstream.name / source.relative_to(upstream)
            # Win32 removes alias/.. before following junctions for this DOS path.
            self.assertTrue(os.path.samefile(candidate, source))
            self.assertEqual(candidate.resolve(), source.resolve())
            token = self.helper["UNTRUSTED_SOURCE_ROOTS"].set((repo, upstream))
            try:
                self.assertFalse(self.helper["external_env_path"](repo, str(candidate)))
            finally:
                self.helper["UNTRUSTED_SOURCE_ROOTS"].reset(token)

    @unittest.skipUnless(os.name == "nt", "requires native Windows drive-relative paths")
    def test_windows_same_drive_relative_path_ignores_drive_letter_case(self):
        with self.fixture() as repo:
            if len(repo.drive) != 2 or repo.drive[1] != ":":
                self.skipTest("requires a drive-letter volume")
            shared = repo.parent / "shared"
            shared.mkdir()
            previous = Path.cwd()
            try:
                os.chdir(repo)
                candidate = repo.drive.swapcase() + "../shared"
                self.assertEqual(Path(candidate).resolve(), shared.resolve())
                self.assertTrue(self.helper["external_env_path"](repo, candidate))
            finally:
                os.chdir(previous)

    def test_case_aliases_do_not_admit_source_executables_or_overlapping_roots(self):
        with self.external_fixture() as (repo, upstream, _, manifest):
            alias = upstream.with_name(upstream.name.upper())
            if not alias.exists() or not os.path.samefile(alias, upstream):
                self.skipTest("requires a case-insensitive filesystem")
            executable = upstream / "reviewer"
            executable.write_text("#!/bin/sh\nexit 99\n")
            executable.chmod(0o755)
            boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
            token = boundary.set((repo, upstream))
            try:
                self.assertFalse(self.helper["external_env_path"](repo, str(alias / "reviewer")))
                self.assertIsNone(self.helper["find_command"](str(alias / "reviewer"), repo))
                with self.assertRaisesRegex(SystemExit, "must point outside"):
                    self.helper["require_output_outside_sources"](alias / "new-output.json", "output", repo)
            finally:
                boundary.reset(token)
            # A differently spelled root must not turn the target into its own external source.
            (repo / ".review/external.json").write_text(json.dumps({**manifest, "root": str(repo.with_name(repo.name.upper()))}))
            status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
            self.assertIn("canonical, separate absolute worktree", str(status))
            self.assertFalse(sends)
            with self.assertRaisesRegex(SystemExit, "canonical, separate absolute worktree"):
                self.helper["external_source_binding"](upstream, alias)

    def test_primary_metadata_checked_before_codex_retry_without_evidence(self):
        for retry in ("model", "auth"):
            for changed in (False, True):
                with self.subTest(retry=retry, changed=changed), self.fixture() as repo:
                    # Both stores are valid and contain the same commits. Only the
                    # retained gitfile binding changes between reviewer attempts.
                    original = repo.parent / "original.git"
                    replacement = repo.parent / "replacement.git"
                    (repo / ".git").rename(original)
                    shutil.copytree(original, replacement)
                    pointer = repo / ".git"
                    pointer.write_text(f"gitdir: {original}\n")
                    operator = repo.parent / "operator"
                    operator.mkdir()
                    if retry == "auth":
                        (operator / "config.toml").write_text(
                            'model_provider = "review_api"\n'
                            '[model_providers.review_api]\n'
                            'base_url = "https://api.openai.com/v1"\n'
                            '[model_providers.review_api.auth]\n'
                            f'command = {json.dumps(sys.executable)}\n'
                        )
                    attempts = []

                    def transport(command, _cwd, **kwargs):
                        attempts.append((command, kwargs["input_text"]))
                        if len(attempts) == 1:
                            if changed:
                                pointer.write_text(f"gitdir: {replacement}\n")
                            model = command[command.index("--model") + 1]
                            error = ("401 Unauthorized" if retry == "auth" else
                                     f"The model {model} does not exist or you do not have access to it.")
                            return subprocess.CompletedProcess(command, 1, "", error)
                        report = {
                            "findings": [], "overall_correctness": "patch is correct",
                            "overall_explanation": "synthetic CLI reply", "overall_confidence": 0.99,
                            "review_completion": "complete",
                        }
                        Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(report))
                        return subprocess.CompletedProcess(command, 0, "", "")

                    with mock.patch.dict(os.environ, {"CODEX_HOME": str(operator)}):
                        status, _, output = self.invoke(
                            repo, "--codex-bin", sys.executable, allocated=False,
                            source_context=False, codex_transport=transport,
                        )
                    if changed:
                        self.assertEqual(len(attempts), 1, str(status) + output)
                        self.assertIn("metadata changed after admission", str(status) + output)
                        self.assertFalse((repo.parent / "result.json").exists(),
                                         "changed metadata must not publish a report")
                    else:
                        self.assertEqual(status, 0, output)
                        self.assertEqual(len(attempts), 2)
                        self.assertEqual(attempts[0][1], attempts[1][1],
                                         "an admitted retry retains the frozen prompt")
                        first, second = (attempt[0] for attempt in attempts)
                        if retry == "model":
                            self.assertNotEqual(first[first.index("--model") + 1],
                                                second[second.index("--model") + 1])
                        else:
                            self.assertNotIn('model_provider="review_api"', first)
                            self.assertIn('model_provider="review_api"', second)

    def test_external_evidence_checked_before_codex_retry(self):
        for retry in ("model", "auth"):
            for mutation in ("source", "manifest", None):
                with self.subTest(retry=retry, mutation=mutation), self.external_fixture() as fixture:
                    repo, _, source, _ = fixture
                    operator = repo.parent / "operator"
                    operator.mkdir()
                    if retry == "auth":
                        (operator / "config.toml").write_text(
                            'model_provider = "review_api"\n'
                            '[model_providers.review_api]\n'
                            'base_url = "https://api.openai.com/v1"\n'
                            '[model_providers.review_api.auth]\n'
                            f'command = {json.dumps(sys.executable)}\n'
                        )
                    attempts = []
                    def transport(command, _cwd, **kwargs):
                        attempts.append((command, kwargs["input_text"]))
                        if len(attempts) == 1:
                            # The first CLI attempt loses access while its captured
                            # source is changed or the operator withdraws the manifest.
                            if mutation == "source":
                                source.write_text("// changed after first send\n")
                            elif mutation == "manifest":
                                (repo / ".review/external.json").unlink()
                            model = command[command.index("--model") + 1]
                            error = ("401 Unauthorized" if retry == "auth" else
                                     f"The model {model} does not exist or you do not have access to it.")
                            return subprocess.CompletedProcess(command, 1, "", error)
                        report = {
                            "findings": [], "overall_correctness": "patch is correct",
                            "overall_explanation": "synthetic CLI reply", "overall_confidence": 0.99,
                            "review_completion": "complete",
                        }
                        Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(report))
                        return subprocess.CompletedProcess(command, 0, "", "")

                    with mock.patch.dict(os.environ, {"CODEX_HOME": str(operator)}):
                        status, _, output = self.invoke(
                            repo, "--external-source-context-file", ".review/external.json",
                            "--codex-bin", sys.executable, codex_transport=transport,
                        )
                    if mutation:
                        self.assertEqual(len(attempts), 1, str(status) + output)
                        self.assertNotEqual(status, 0, output)
                        self.assertIn("evidence changed", str(status) + output)
                        self.assertFalse((repo.parent / "result.json").exists(),
                                         "changed evidence must never publish a clean report")
                    else:
                        self.assertEqual(status, 0, output)
                        self.assertEqual(len(attempts), 3)  # Retry plus the second allocated pass.
                        self.assertEqual(attempts[0][1], attempts[1][1], "retry must retain the frozen prompt")
                        first, second = (attempt[0] for attempt in attempts[:2])
                        if retry == "model":
                            self.assertNotEqual(first[first.index("--model") + 1], second[second.index("--model") + 1])
                        else:
                            self.assertNotIn('model_provider="review_api"', first)
                            self.assertIn('model_provider="review_api"', second)

    def test_external_linked_worktree_sha256_and_executable_blob(self):
        with self.external_fixture(object_format="sha256") as (repo, upstream, source, manifest):
            self.git(upstream, "update-index", "--chmod=+x", manifest["files"][0]["path"])
            self.git(upstream, "commit", "-qm", "executable owner")
            linked = repo.parent / "linked"
            self.git(upstream, "worktree", "add", "--detach", str(linked), "HEAD")
            manifest.update(root=str(linked), commit=self.git(linked, "rev-parse", "HEAD"))
            manifest["files"][0]["mode"] = "100755"
            (repo / ".review/external.json").write_text(json.dumps(manifest))
            status, sends, output = self.invoke(repo, "--external-source-context-file", ".review/external.json")
            self.assertEqual(status, 0, output)
            self.assertEqual(len(sends), 2)
            self.assertEqual(len(manifest["commit"]), 64)
            self.assertIn("mode=100755", sends[0])

    def test_external_source_refuses_duplicate_keys_and_alternate_object_stores(self):
        with self.external_fixture() as (repo, upstream, _, manifest):
            duplicate = json.dumps(manifest).replace('"version": 1', '"version": 1, "version": 1')
            (repo / ".review/external.json").write_text(duplicate)
            status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
            self.assertNotEqual(status, 0)
            self.assertFalse(sends)

            (repo / ".review/external.json").write_text(json.dumps(manifest))
            (upstream / ".git/objects/info/alternates").write_text("")
            status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
            self.assertNotEqual(status, 0)
            self.assertFalse(sends)

    def test_external_source_without_allocation_ignores_git_redirection(self):
        with self.external_fixture() as (repo, upstream, source, manifest):
            original = source.read_bytes().decode()
            source.write_text("// replacement must not become review context\n")
            self.git(upstream, "commit", "-qam", "replacement")
            self.git(upstream, "replace", manifest["commit"], "HEAD")
            with mock.patch.dict(os.environ, {
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(repo / "missing-object-store"),
                "GIT_OBJECT_DIRECTORY": str(repo / "missing-object-store"),
                "GIT_DIR": str(repo / ".git"),
                "GIT_WORK_TREE": str(repo),
                "GIT_NO_LAZY_FETCH": "0",
            }):
                for options in ((), ("--mode", "commit", "--commit", "HEAD")):
                    with self.subTest(options=options):
                        status, sends, output = self.invoke(
                            repo, "--external-source-context-file", ".review/external.json",
                            *options, allocated=False,
                        )
                        self.assertEqual(status, 0, output)
                        self.assertTrue(sends)
                        for prompt in sends:
                            self.assertIn(original, prompt)
                            self.assertNotIn("replacement must not", prompt)

    @unittest.skipIf(os.name == "nt", "uses executable shell wrappers")
    def test_external_source_cannot_supply_the_reviewer_probe(self):
        with self.external_fixture() as (repo, upstream, _, _):
            marker = repo.parent / "untrusted-reviewer-executed"
            binary = upstream / "codex"
            binary.write_text("#!/bin/sh\ntouch " + shlex.quote(str(marker)) + "\nexit 99\n")
            binary.chmod(0o755)
            status, sends, _ = self.invoke(
                repo, "--external-source-context-file", ".review/external.json",
                "--codex-bin", str(binary), "--dry-run", real_engine_probe=True,
            )
            self.assertNotEqual(status, 0)
            self.assertFalse(sends)
            self.assertFalse(marker.exists(), "source-owned reviewer executed during preflight")
            (repo.parent / "bin").mkdir()
            trusted = repo.parent / "bin" / "trusted-codex"
            shutil.copy2(binary, trusted)
            config = repo.parent / "operator-config"
            config.mkdir()
            (upstream / "config.toml").write_text('cli_auth_credentials_store="keyring"\n')
            (config / "config.toml").symlink_to(upstream / "config.toml")
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(config)}):
                status, sends, output = self.invoke(
                    repo, "--external-source-context-file", ".review/external.json",
                    "--codex-bin", str(trusted), "--dry-run", real_engine_probe=True,
                )
            self.assertNotEqual(status, 0)
            self.assertFalse(sends)
            self.assertIn("Codex configuration and authentication must be outside reviewed source roots", output)
            self.assertFalse(marker.exists(), "reviewer probe admitted source-owned configuration")

    @unittest.skipIf(os.name == "nt", "uses executable shell wrappers")
    def test_external_source_cannot_supply_host_configuration_or_authentication(self):
        with self.external_fixture() as (repo, upstream, _, _):
            binary = upstream / "auth-helper"
            binary.write_text("#!/bin/sh\nexit 99\n")
            binary.chmod(0o755)
            config = repo.parent / "operator-config"
            config.mkdir()
            (config / "config.toml").write_text(
                'model_provider="review_api"\n[model_providers.review_api]\n'
                'name="Example"\nbase_url="https://api.openai.com/v1"\n'
                'wire_api="responses"\nrequires_openai_auth=false\n'
                '[model_providers.review_api.auth]\ncommand=' + json.dumps(str(binary)) + "\n"
            )
            boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
            token = boundary.set((repo, upstream))
            external_token = self.helper["EXTERNAL_SOURCE_REVIEW"].set(True)
            try:
                with mock.patch.dict(os.environ, {"CODEX_HOME": str(config), "HOME": str(repo.parent)}):
                    with self.assertRaisesRegex(SystemExit, "authentication executable must be outside"):
                        self.helper["load_codex_inference_route"](repo, ['model_provider="review_api"'])
                with mock.patch.dict(os.environ, {
                    "CODEX_HOME": str(upstream), "HOME": str(upstream),
                    "SSL_CERT_FILE": str(binary), "PATH": str(upstream) + os.pathsep + os.environ["PATH"],
                }):
                    environment = self.helper["safe_engine_env"](repo, engine="codex")
                    for key in ("HOME", "CODEX_HOME", "SSL_CERT_FILE"):
                        self.assertNotIn(key, environment)
                    self.assertNotIn(str(upstream), environment["PATH"].split(os.pathsep))
                    with self.assertRaisesRegex(SystemExit, "trusted caller HOME"):
                        self.helper["codex_auth_helper_home"](repo)
                    with self.assertRaises(SystemExit):
                        self.helper["resolve_command"](str(binary), repo)
                # The login-status subprocess must use the same filtered host PATH.
                marker = repo.parent / "unsafe-login-environment"
                (repo.parent / "trusted-bin").mkdir()
                wrapper = repo.parent / "trusted-bin" / "trusted-login-wrapper"
                wrapper.write_text(
                    '#!/bin/sh\ncase ":$PATH:" in *' + shlex.quote(":" + str(upstream) + ":")
                    + '*) touch ' + shlex.quote(str(marker)) + '; exit 99;; esac\n'
                    'test "$CODEX_HOME" = ' + shlex.quote(str(config)) + ' || exit 98\n'
                    'test "$HOME" = ' + shlex.quote(str(repo.parent)) + ' || exit 97\n'
                    'echo "not logged in"\nexit 1\n'
                )
                wrapper.chmod(0o755)
                with mock.patch.dict(os.environ, {
                    "PATH": str(upstream) + os.pathsep + os.environ["PATH"],
                    "HOME": str(repo.parent), "CODEX_HOME": str(config),
                }):
                    self.assertTrue(self.helper["codex_subscription_login_missing"](str(wrapper), repo.parent, repo))
                self.assertFalse(marker.exists())
            finally:
                self.helper["EXTERNAL_SOURCE_REVIEW"].reset(external_token)
                boundary.reset(token)

    def test_git_home_cannot_hide_changes_through_source_owned_default_ignores(self):
        with self.external_fixture() as (repo, upstream, _, _):
            (repo / "untracked-evidence.txt").write_text("candidate source\n")
            neutral = repo.parent / "neutral-home"
            neutral.mkdir()
            trusted = repo.parent / "trusted-home"
            for home in (trusted, upstream):
                directory = home / ".config" / "git"
                directory.mkdir(parents=True)
                (directory / "ignore").write_text("untracked-evidence.txt\n")
            token = self.helper["UNTRUSTED_SOURCE_ROOTS"].set((repo, upstream))
            try:
                # Real Git honors trusted defaults; a source tree cannot choose them.
                for home, expected in ((neutral, "?? untracked-evidence.txt\n"), (trusted, "")):
                    with self.subTest(home=home), mock.patch.dict(os.environ, {"HOME": str(home)}):
                        result = self.helper["git_result"](repo, "status", "--porcelain", "--untracked-files=all")
                        self.assertEqual(result.returncode, 0)
                        self.assertEqual(result.stdout, expected)
                for home in (upstream, repo):
                    with self.subTest(source_home=home), mock.patch.dict(os.environ, {"HOME": str(home)}):
                        with self.assertRaisesRegex(SystemExit, "Git.*HOME"):
                            self.helper["safe_git_env"](repo)
            finally:
                self.helper["UNTRUSTED_SOURCE_ROOTS"].reset(token)

    @unittest.skipIf(os.name == "nt", "uses POSIX symlinks; native junction case is separate")
    def test_windows_cleanup_rejects_source_selected_executable_before_preflight(self):
        with self.external_fixture() as (repo, upstream, _, _):
            trusted = repo.parent / "installed"
            trusted.mkdir()
            (trusted / "taskkill.exe").write_bytes(b"inert installed executable")
            (upstream / "taskkill.exe").write_bytes(b"inert source executable")
            # Exercise both descendants omitted by the old SystemRoot-only
            # check, plus a source-owned selector whose final target is safe.
            for kind in ("directory", "leaf", "source-selector"):
                with self.subTest(kind=kind):
                    system = repo.parent / ("system-" + kind)
                    system.mkdir()
                    system32 = system / "System32"
                    if kind == "directory":
                        system32.symlink_to(upstream, target_is_directory=True)
                    elif kind == "leaf":
                        system32.mkdir()
                        (system32 / "taskkill.exe").symlink_to(upstream / "taskkill.exe")
                    else:
                        selector = upstream / "selector"
                        selector.symlink_to(trusted, target_is_directory=True)
                        system32.symlink_to(selector, target_is_directory=True)
                    probe = mock.Mock(side_effect=AssertionError("preflight must not start"))
                    # Change only the helper's platform dispatch; Path and all
                    # filesystem resolution remain real POSIX operations.
                    windows = types.SimpleNamespace(**{**vars(os), "name": "nt"})
                    windows_stat = types.SimpleNamespace(**{**vars(stat), "IO_REPARSE_TAG_MOUNT_POINT": 0xA0000003})
                    with mock.patch.dict(os.environ, {"SystemRoot": str(system)}), mock.patch.dict(
                        self.helper["main_with_args"].__globals__, {"os": windows, "stat": windows_stat, "preflight_git": probe}
                    ):
                        status, sends, _ = self.invoke(
                            repo, "--external-source-context-file", ".review/external.json")
                    self.assertIn("trusted System32/taskkill.exe", str(status))
                    self.assertFalse(sends)
                    probe.assert_not_called()
                    self.assertIsNone(self.helper["WINDOWS_TASKKILL"].get())

    def test_windows_cleanup_binding_pins_identity_and_source_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            repo = parent / "repo"
            repo.mkdir()
            source = parent / "source"
            source.mkdir()
            system = parent / "system"
            system32 = system / "System32"
            system32.mkdir(parents=True)
            executable = system32 / "taskkill.exe"
            executable.write_bytes(b"inert installed executable")
            sources = self.helper["UNTRUSTED_SOURCE_ROOTS"]
            token = sources.set((repo, source))
            try:
                with mock.patch.dict(os.environ, {"SystemRoot": str(system)}):
                    binding = self.helper["_capture_windows_taskkill"](repo)
            finally:
                sources.reset(token)
            bound = self.helper["WINDOWS_TASKKILL"].set(binding)
            try:
                # Environment changes cannot select a new executable during
                # cleanup, even once the original source context has unwound.
                with mock.patch.dict(os.environ, {"SystemRoot": str(source)}):
                    self.assertEqual(self.helper["_resolve_windows_taskkill"](), str(executable))
                # A later source boundary (e.g. linked Git metadata) still
                # constrains the already admitted executable.
                added = sources.set((system,))
                try:
                    self.assertIsNone(self.helper["_resolve_windows_taskkill"]())
                finally:
                    sources.reset(added)
                replacement = system32 / "replacement.exe"
                replacement.write_bytes(executable.read_bytes())
                replacement.replace(executable)
                self.assertIsNone(self.helper["_resolve_windows_taskkill"]())
            finally:
                self.helper["WINDOWS_TASKKILL"].reset(bound)

    @unittest.skipIf(os.name == "nt", "uses POSIX symlinks; native junction case is separate")
    def test_windows_cleanup_rechecks_raw_selector_after_source_context_unwinds(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            repo = parent / "repo"
            repo.mkdir()
            source = parent / "source"
            source.mkdir()
            system = parent / "system"
            system.mkdir()
            installed = parent / "installed"
            installed.mkdir()
            executable = installed / "taskkill.exe"
            executable.write_bytes(b"inert installed executable")
            alias = system / "System32"
            alias.symlink_to(installed, target_is_directory=True)
            sources = self.helper["UNTRUSTED_SOURCE_ROOTS"]
            token = sources.set((repo, source))
            try:
                with mock.patch.dict(os.environ, {"SystemRoot": str(system)}):
                    binding = self.helper["_capture_windows_taskkill"](repo)
            finally:
                sources.reset(token)
            bound = self.helper["WINDOWS_TASKKILL"].set(binding)
            try:
                self.assertEqual(self.helper["_resolve_windows_taskkill"](), str(executable))
                # The final target and its identity stay unchanged. Only the
                # raw selector now traverses a retained source-owned link.
                selector = source / "selector"
                selector.symlink_to(installed, target_is_directory=True)
                alias.unlink()
                alias.symlink_to(selector, target_is_directory=True)
                self.assertEqual(alias.resolve(), installed)
                self.assertIsNone(self.helper["_resolve_windows_taskkill"]())
                windows = types.SimpleNamespace(**{**vars(os), "name": "nt"})
                windows_stat = types.SimpleNamespace(**{**vars(stat), "IO_REPARSE_TAG_MOUNT_POINT": 0xA0000003})
                with mock.patch.dict(self.helper["_signal_owned_process_group"].__globals__, {"os": windows, "stat": windows_stat}), mock.patch(
                    "subprocess.run", side_effect=AssertionError("untrusted taskkill must not execute")
                ) as launch:
                    self.assertTrue(self.helper["_signal_owned_process_group"](mock.Mock(pid=1234)))
                launch.assert_not_called()
            finally:
                self.helper["WINDOWS_TASKKILL"].reset(bound)

    @unittest.skipUnless(os.name == "nt", "requires native Windows directory junctions")
    def test_windows_cleanup_rejects_native_system32_junction(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            repo = parent / "repo"
            repo.mkdir()
            source = parent / "source"
            source.mkdir()
            (source / "taskkill.exe").write_bytes(b"inert source executable")
            system = parent / "system"
            system.mkdir()
            system32 = system / "System32"
            cmd = Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe"
            subprocess.run([str(cmd), "/c", "mklink", "/J", str(system32), str(source)],
                           check=True, capture_output=True)
            token = self.helper["UNTRUSTED_SOURCE_ROOTS"].set((repo, source))
            try:
                with mock.patch.dict(os.environ, {"SystemRoot": str(system)}):
                    with self.assertRaisesRegex(SystemExit, "trusted System32/taskkill.exe"):
                        self.helper["_capture_windows_taskkill"](repo)
                    self.assertIsNone(self.helper["_resolve_windows_taskkill"]())
            finally:
                self.helper["UNTRUSTED_SOURCE_ROOTS"].reset(token)
                system32.rmdir()

    def test_external_source_platform_environment_is_refused_before_any_process(self):
        with self.external_fixture() as (repo, upstream, _, _):
            for key in ("SystemRoot", "COMSPEC", "SHELL", "TMPDIR"):
                with self.subTest(key=key), mock.patch.dict(os.environ, {key: str(upstream)}):
                    probe = mock.Mock(side_effect=AssertionError("process admission must not run"))
                    with mock.patch.dict(self.helper["main_with_args"].__globals__, {"preflight_git": probe}):
                        status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
                    self.assertNotEqual(status, 0)
                    self.assertFalse(sends)
                    probe.assert_not_called()
                    self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())

    @unittest.skipIf(os.name == "nt", "requires local symlink privilege")
    def test_external_source_platform_paths_reject_source_owned_intermediate_links(self):
        with self.external_fixture() as (repo, upstream, _, _):
            trusted = repo.parent / "trusted-system"
            trusted.mkdir()
            inside = upstream / "system-link"
            inside.symlink_to(trusted, target_is_directory=True)
            outside = repo.parent / "outside-system-link"
            outside.symlink_to(inside, target_is_directory=True)
            for key in ("SystemRoot", "COMSPEC", "SHELL", "TMPDIR"):
                for path in (inside, outside):
                    with self.subTest(key=key, path=path), mock.patch.dict(os.environ, {key: str(path)}):
                        probe = mock.Mock(side_effect=AssertionError("process admission must not run"))
                        with mock.patch.dict(self.helper["main_with_args"].__globals__, {"preflight_git": probe}):
                            status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
                        self.assertNotEqual(status, 0)
                        self.assertFalse(sends)
                        probe.assert_not_called()
                        self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())
            # A caller-owned alias entirely outside reviewed sources remains valid.
            outside.unlink()
            outside.symlink_to(trusted, target_is_directory=True)
            token = self.helper["UNTRUSTED_SOURCE_ROOTS"].set((repo, upstream))
            try:
                self.assertTrue(self.helper["external_env_path"](repo, str(outside)))
            finally:
                self.helper["UNTRUSTED_SOURCE_ROOTS"].reset(token)

    @unittest.skipIf(os.name == "nt", "uses executable shell wrappers")
    def test_external_sources_exclude_all_source_roots_before_git_admission(self):
        with self.external_fixture() as (repo, upstream, _, manifest):
            other = repo.parent / "other-source"
            shutil.copytree(upstream, other)
            other_manifest = {**manifest, "root": str(other)}
            (repo / ".review/other.json").write_text(json.dumps(other_manifest))
            marker = repo.parent / "untrusted-executed"
            trusted_git = shutil.which("git")
            self.assertIsNotNone(trusted_git)
            directories = [root / "bin" for root in (repo, upstream, other)]
            for directory in directories:
                directory.mkdir()
                candidate = directory / "git"
                candidate.write_text("#!/bin/sh\ntouch " + shlex.quote(str(marker)) + "\nexit 99\n")
                candidate.chmod(0o755)
            (repo.parent / "trusted-bin").mkdir()
            wrapper = repo.parent / "trusted-bin" / "trusted-git-wrapper"
            wrapper.write_text("#!/bin/sh\n" + "\n".join(
                'case ":$PATH:" in *' + shlex.quote(":" + str(directory) + ":")
                + '*) touch ' + shlex.quote(str(marker)) + '; exit 98;; esac'
                for directory in directories
            ) + "\nexec " + shlex.quote(trusted_git) + ' "$@"\n')
            wrapper.chmod(0o755)
            for selected in ("git", str(wrapper), str(directories[2] / "git")):
                with self.subTest(selected=selected), mock.patch.dict(os.environ, {
                    "PATH": os.pathsep.join(map(str, directories)) + os.pathsep + os.environ["PATH"],
                    "AUTOREVIEW_GIT": selected,
                }):
                    status, sends, output = self.invoke(
                        repo, "--external-source-context-file", ".review/external.json",
                        "--external-source-context-file", ".review/other.json",
                    )
                    if selected == str(directories[2] / "git"):
                        self.assertNotEqual(status, 0)
                        self.assertFalse(sends)
                    else:
                        self.assertEqual(status, 0, output)
                        self.assertEqual(len(sends), 2)
                    self.assertFalse(marker.exists(), "a declared source supplied executable code")
                    self.assertEqual(self.helper["UNTRUSTED_SOURCE_ROOTS"].get(), ())

    def test_external_committed_source_is_whole_in_every_assignment(self):
        content = ("// external contract 🦊\r\n" * 120 + "// final line").encode()
        with self.external_fixture(content=content) as (repo, upstream, source, manifest):
            # A committed source role must not substitute the caller's dirty checkout.
            source.write_text("dirty external body must not be sent")
            status, sends, output = self.invoke(
                repo, "--external-source-context-file", ".review/external.json",
            )
            self.assertEqual(status, 0, output)
            self.assertEqual(len(sends), 2)
            for prompt in sends:
                self.assertEqual(prompt.count(content.decode()), 1)
                self.assertNotIn("dirty external body", prompt)
                self.assertIn(manifest["commit"], prompt)
                self.assertIn(manifest["files"][0]["blob"], prompt)
                self.assertIn(f"# External source worktree: {json.dumps(str(upstream))}\n", prompt)
                self.assertNotIn(source.name, prompt.split("# Change Bundle\n", 1)[1])
            result = json.loads((repo.parent / "result.json").read_text())
            self.assertEqual(len(result["review_allocation"]["units"]), 3)

    def test_external_source_rejects_ambiguous_or_unpinned_manifests_before_send(self):
        with self.external_fixture() as (repo, upstream, source, original):
            changes = {
                "relative root": lambda m: m.update(root="../upstream"),
                "review root": lambda m: m.update(root=str(repo)),
                "parent root": lambda m: m.update(root=str(repo.parent)),
                "not root": lambda m: m.update(root=str(source.parent)),
                "mutable ref": lambda m: m.update(commit="HEAD"),
                "wrong blob": lambda m: m["files"][0].update(blob="0" * 40),
                "wrong mode": lambda m: m["files"][0].update(mode="100755"),
                "traversal": lambda m: m["files"][0].update(path="../upstream/" + m["files"][0]["path"]),
                "absent source": lambda m: m["files"][0].update(path="missing.ts"),
                "duplicate": lambda m: m["files"].append({**m["files"][0], "path": "./" + m["files"][0]["path"]}),
                "unknown field": lambda m: m.update(command="not executed"),
            }
            for name, change in changes.items():
                with self.subTest(name=name):
                    manifest = json.loads(json.dumps(original))
                    change(manifest)
                    (repo / ".review/external.json").write_text(json.dumps(manifest))
                    status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
                    self.assertNotEqual(status, 0)
                    self.assertFalse(sends)
            (repo / ".review/external.json").write_text(json.dumps(original))
            status, sends, _ = self.invoke(repo, "--mode", "local", "--external-source-context-file", ".review/external.json")
            self.assertNotEqual(status, 0)
            self.assertFalse(sends)

    def test_external_source_retains_sensitive_directory_and_keyfile_refusals(self):
        for path in ("credentials/owner.ts", ".aws/owner.ts", "private/owner.ts", ".env", "key.pem"):
            with self.subTest(path=path), self.external_fixture(path=path) as (repo, _, _, _):
                status, sends, output = self.invoke(repo, "--external-source-context-file", ".review/external.json")
                self.assertNotEqual(status, 0)
                self.assertIn("sensitive", str(status) + output)
                self.assertFalse(sends)

    def test_external_source_mutation_stops_later_pass_and_publication(self):
        for mutation in ("bytes", "manifest", "object store", "git pointer"):
            with self.subTest(mutation=mutation), self.external_fixture() as (repo, upstream, source, _):
                def mutate(_count, report):
                    if mutation == "bytes":
                        source.write_text("changed after first send")
                    elif mutation == "manifest":
                        (repo / ".review/external.json").write_text("{}")
                    elif mutation == "object store":
                        objects = upstream / ".git/objects"
                        objects.rename(upstream / ".git/old-objects")
                        # Preserve all objects: repository identity, not missing data, must fail.
                        shutil.copytree(upstream / ".git/old-objects", objects)
                    else:
                        (upstream / ".git").rename(upstream / "metadata")
                        (upstream / ".git").write_text("gitdir: metadata\n")
                    return report
                status, sends, output = self.invoke(
                    repo, "--external-source-context-file", ".review/external.json", engine=mutate,
                )
                self.assertNotEqual(status, 0, output)
                self.assertEqual(len(sends), 1)
                self.assertFalse((repo.parent / "result.json").exists())

    @unittest.skipIf(os.name == "nt", "requires local symlink privilege")
    def test_external_source_refuses_symlink_roots_paths_and_object_stores(self):
        for mutation in ("root", "source", "objects"):
            with self.subTest(mutation=mutation), self.external_fixture() as (repo, upstream, source, manifest):
                if mutation == "root":
                    alias = repo.parent / "alias"
                    alias.symlink_to(upstream, target_is_directory=True)
                    manifest["root"] = str(alias)
                    (repo / ".review/external.json").write_text(json.dumps(manifest))
                else:
                    path = source if mutation == "source" else upstream / ".git/objects"
                    moved = path.with_name("moved-" + path.name)
                    path.rename(moved)
                    path.symlink_to(moved, target_is_directory=moved.is_dir())
                status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
                self.assertNotEqual(status, 0)
                self.assertFalse(sends)

    @unittest.skipIf(os.name == "nt", "requires local symlink privilege")
    def test_external_source_refuses_symlinks_in_metadata_pointer_targets(self):
        for pointer in ("gitdir", "commondir"):
            for alias_kind in ("leaf", "parent"):
                with self.subTest(pointer=pointer, alias=alias_kind), self.external_fixture() as (repo, upstream, _, manifest):
                    if pointer == "gitdir":
                        target = upstream / "metadata"
                        (upstream / ".git").rename(target)
                        pointer_file = upstream / ".git"
                        prefix = "gitdir: "
                    else:
                        linked = repo.parent / "linked"
                        self.git(upstream, "worktree", "add", "--detach", str(linked), "HEAD")
                        pointer_file = Path(self.git(linked, "rev-parse", "--absolute-git-dir")) / "commondir"
                        target = upstream / ".git"
                        upstream = linked
                        manifest["root"] = str(linked)
                        prefix = ""
                    alias = repo.parent / "metadata-alias"
                    alias.symlink_to(target if alias_kind == "leaf" else target.parent, target_is_directory=True)
                    redirected = alias if alias_kind == "leaf" else alias / target.name
                    pointer_file.write_text(prefix + str(redirected) + "\n")
                    (repo / ".review/external.json").write_text(json.dumps(manifest))
                    # Real Git accepts these pointers and hides their symlinks in
                    # its resolved metadata paths. Reject before sending context.
                    self.assertEqual(self.git(upstream, "rev-parse", "HEAD"), manifest["commit"])
                    status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
                    self.assertNotEqual(status, 0)
                    self.assertFalse(sends)

    @unittest.skipUnless(os.name == "nt", "requires native Windows directory junctions")
    def test_windows_external_metadata_junctions_refuse_context_before_send(self):
        for location in ("objects", "gitdir", "commondir"):
            with self.subTest(location=location), self.external_fixture() as (repo, upstream, _, manifest):
                self.helper["external_source_binding"](repo, upstream)
                alias = repo.parent / "metadata-junction"
                if location == "objects":
                    alias = upstream / ".git/objects"
                    target = repo.parent / "external-objects"
                    alias.rename(target)
                elif location == "gitdir":
                    target = repo.parent / "external-metadata"
                    (upstream / ".git").rename(target)
                    (upstream / ".git").write_text("gitdir: " + str(alias) + "\n")
                else:
                    linked = repo.parent / "linked"
                    self.git(upstream, "worktree", "add", "--detach", str(linked), "HEAD")
                    pointer = Path(self.git(linked, "rev-parse", "--absolute-git-dir")) / "commondir"
                    target = upstream / ".git"
                    pointer.write_text(str(alias) + "\n")
                    upstream = linked
                    manifest["root"] = str(linked)
                    (repo / ".review/external.json").write_text(json.dumps(manifest))
                cmd = Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe"
                subprocess.run([str(cmd), "/d", "/c", "mklink", "/J", str(alias), str(target)],
                               check=True, capture_output=True, text=True)
                self.assertEqual(alias.lstat().st_reparse_tag, stat.IO_REPARSE_TAG_MOUNT_POINT)
                # The actual object store is unchanged and Git still reads it.
                # Reject the raw redirector rather than trusting resolved paths.
                self.assertEqual(self.git(upstream, "rev-parse", "HEAD"), manifest["commit"])
                self.assertEqual(self.git(upstream, "cat-file", "-t", manifest["commit"]), "commit")
                status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
                self.assertIn("refusing redirected evidence", str(status))
                self.assertFalse(sends)
                self.assertFalse((repo.parent / "result.json").exists())

    @unittest.skipIf(os.name == "nt", "requires POSIX whitespace directory names")
    def test_external_metadata_pointer_whitespace_matches_stock_git(self):
        for pointer in ("gitdir", "commondir"):
            for suffix in (" ", "\t", "\ninside"):
                with self.subTest(pointer=pointer, suffix=repr(suffix)), self.linked_external_fixture() as fixture:
                    repo, linked, git_dir, common, manifest = fixture
                    # Detach the admin directory from the common store so either
                    # pointer can name a path with meaningful trailing whitespace.
                    admin = repo.parent / ("linked-admin" + (suffix if pointer == "gitdir" else ""))
                    git_dir.rename(admin)
                    (linked / ".git").write_bytes(b"gitdir: " + os.fsencode(admin) + b"\r\n\n")
                    if pointer == "commondir":
                        moved_common = repo.parent / ("common-store" + suffix)
                        common.rename(moved_common)
                        common = moved_common
                    (admin / "commondir").write_bytes(os.fsencode(common) + b"\r\n\n")
                    # Do not use self.git here: its test convenience .strip()
                    # would reproduce the bug by hiding Git's exact path output.
                    for options, expected in ((("--absolute-git-dir",), admin),
                                              (("--git-common-dir",), common),
                                              (("--git-path", "objects"), common / "objects")):
                        actual = fixture_git(linked, "rev-parse", *options, check=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
                        self.assertEqual(actual, os.fsencode(expected) + b"\n")
                    self.assertEqual(self.git(linked, "rev-parse", "HEAD"), manifest["commit"])
                    status, sends, output = self.invoke(
                        repo, "--external-source-context-file", ".review/external.json",
                        "--dry-run", allocated=False,
                    )
                    self.assertEqual(status, 0, output)
                    self.assertFalse(sends)

    @unittest.skipIf(os.name == "nt", "requires POSIX trailing-space/tab directory names")
    def test_external_metadata_whitespace_sibling_cannot_escape_output_guard(self):
        for suffix in (" ", "\t"):
            with self.subTest(suffix=repr(suffix)), self.linked_external_fixture() as fixture:
                repo, linked, git_dir, common, manifest = fixture
                actual = repo.parent / ("linked-admin" + suffix)
                sibling = repo.parent / "linked-admin"
                git_dir.rename(actual)
                (actual / "commondir").write_bytes(os.fsencode(common) + b"\n")
                shutil.copytree(actual, sibling)
                (linked / ".git").write_bytes(b"gitdir: " + os.fsencode(actual) + b"\n")
                # Both admins share the same commit and common store. Trimming
                # both the gitfile and Git's stdout must not bind the sibling.
                selected = fixture_git(linked, "rev-parse", "--absolute-git-dir", check=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
                self.assertEqual(selected, os.fsencode(actual) + b"\n")
                self.assertEqual(self.git(linked, "rev-parse", "HEAD"), manifest["commit"])
                self.assertEqual(self.git(linked, "--git-dir=" + str(sibling), "rev-parse", "HEAD"),
                                 manifest["commit"])
                destination = actual / "HEAD"
                before = destination.read_bytes()
                identity = destination.stat()
                probe = mock.Mock(wraps=self.helper["require_output_ready"])
                with mock.patch.dict(self.helper["main_with_args"].__globals__, {"require_output_ready": probe}):
                    status, sends, _ = self.invoke(
                        repo, "--external-source-context-file", ".review/external.json",
                        "--status-output", str(destination), allocated=False,
                    )
                self.assertIn("--status-output must point outside", str(status))
                probe.assert_not_called()
                self.assertFalse(sends)
                self.assertEqual(destination.read_bytes(), before)
                self.assertEqual(destination.stat().st_ino, identity.st_ino)

    def test_external_source_never_gains_finding_authority(self):
        with self.external_fixture() as (repo, _, source, manifest):
            def outside(_count, report):
                report["findings"] = [{
                    "title": "External context defect", "body": "Not a selected change.",
                    "priority": "P2", "confidence": 1, "category": "bug",
                    "code_location": {"file_path": manifest["files"][0]["path"], "line": 1},
                }]
                report["overall_correctness"] = "patch is incorrect"
                return report
            status, _, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json", engine=outside)
            self.assertEqual(status, 2)
            result = json.loads((repo.parent / "result.json").read_text())
            self.assertEqual(result["findings"], [])
            self.assertTrue(result["scope_rejected_findings"])

    def test_external_source_budget_refuses_instead_of_truncating(self):
        with self.external_fixture(content=b"// required contract\n" * 5000) as (repo, _, _, _):
            status, sends, _ = self.invoke(repo, "--external-source-context-file", ".review/external.json")
            self.assertNotEqual(status, 0)
            self.assertFalse(sends)

    def test_whole_units_metadata_overlap_and_contracts_retain_full_range(self):
        with self.fixture() as repo:
            self.write_manifest(repo, self.manifest(repo))
            status, sends, output = self.invoke(repo)
            self.assertEqual(status, 0, output)
            self.assertEqual(len(sends), 2)
            report = json.loads((repo.parent / "result.json").read_bytes())
            allocation = report["review_allocation"]
            self.assertEqual(report["review_status"], "scoped-clean")
            self.assertEqual([row["label"] for row in report["pass_reports"]], ["first-owner", "integration"])
            capture = self.helper["branch_bundle"](repo, "HEAD^")
            original = capture.text.encode()
            reconstructed = original[:allocation["header_bytes"]]
            for unit in allocation["units"]:
                data = original[unit["byte_offset"]:unit["byte_offset"] + unit["bytes"]]
                self.assertEqual(hashlib.sha256(data).hexdigest(), unit["sha256"])
                reconstructed += data
                for prompt, batch in zip(sends, allocation["batches"]):
                    self.assertEqual(data.decode() in prompt, unit["path"] in batch["changes"])
            self.assertEqual(reconstructed, original)
            units = {unit["path"]: unit for unit in allocation["units"]}
            self.assertEqual(units["retired.py"]["after"]["mode"], "000000")
            self.assertEqual(units["second.py"]["after"]["mode"], "100755")
            self.assertEqual(allocation["omitted_paths"], [])
            for prompt in sends:
                self.assertEqual(prompt.count((repo / "contract.py").read_bytes().decode()), 1)
                self.assertEqual(prompt.count("GLOBAL WHOLE OWNER"), 1)
                self.assertIn("blob=" + self.git(repo, "rev-parse", "HEAD:contract.py"), prompt)

    def test_invalid_or_stale_manifest_has_zero_launches(self):
        mutations = {
            "base": lambda m: m.update(base="0" * 40),
            "head": lambda m: m.update(head="0" * 40),
            "bundle": lambda m: m.update(bundle_sha256="0" * 64),
            "context": lambda m: m["contexts"][0].update(blob="0" * 40),
            "mode": lambda m: m["contexts"][0].update(mode="100755"),
            "missing unit": lambda m: m["batches"][0]["changes"].remove("retired.py"),
            "unknown unit": lambda m: m["batches"][0]["changes"].append("contract.py"),
            "alias": lambda m: m["contexts"][0].update(path="./contract.py"),
            "duplicate context": lambda m: m["contexts"].append(m["contexts"][0]),
            "duplicate unit": lambda m: m["batches"][0]["changes"].append("first.py"),
            "no integration": lambda m: m["batches"][1].update(kind="owner"),
            "no obligation": lambda m: m["batches"][1].update(obligations=[]),
            "unknown field": lambda m: m.update(command="ignored"),
        }
        with self.fixture() as repo:
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    manifest = self.manifest(repo)
                    mutate(manifest)
                    self.write_manifest(repo, manifest)
                    status, sends, _ = self.invoke(repo)
                    self.assertNotEqual(status, 0)
                    self.assertFalse(sends)

    def test_omissions_and_unsupported_units_refuse_before_send(self):
        for kind in ("sensitive", "symlink", "gitlink", "binary"):
            with self.subTest(kind=kind), self.fixture() as repo:
                manifest = self.manifest(repo)
                if kind == "sensitive":
                    (repo / ".env").write_bytes(b"FAKE_TEST_VALUE=placeholder\n")
                    self.git(repo, "add", "-f", ".env")
                    expected = "cannot certify a range with omitted sensitive inputs"
                elif kind == "symlink":
                    # Git's link mode needs no host symlink privilege on Windows.
                    self.git(repo, "config", "core.symlinks", "false")
                    (repo / "link.py").write_bytes(b"first.py")
                    blob = self.git(repo, "hash-object", "-w", "link.py")
                    self.git(repo, "update-index", "--add", "--cacheinfo", "120000," + blob + ",link.py")
                    expected = "does not support binary, symlink or gitlink changes"
                elif kind == "gitlink":
                    self.git(repo, "update-index", "--add", "--cacheinfo",
                             "160000," + self.git(repo, "rev-parse", "HEAD") + ",vendor")
                    expected = "cannot reconstruct the original branch bundle"
                else:
                    (repo / "image.bin").write_bytes(b"\0binary")
                    self.git(repo, "add", "image.bin")
                    expected = "refusing unsupported or malformed image in branch diff"
                self.git(repo, "commit", "--amend", "--no-edit", "-q")
                # Binary capture itself refuses before a manifest can be bound.
                # Other cases use a fully valid allocation of the captured range.
                if kind != "binary":
                    manifest = self.manifest(repo)
                    manifest["batches"][0]["changes"].append(
                        {"sensitive": ".env", "symlink": "link.py", "gitlink": "vendor"}[kind])
                self.write_manifest(repo, manifest)
                status, sends, output = self.invoke(repo)
                self.assertNotEqual(status, 0)
                self.assertFalse(sends)
                self.assertIn(expected, str(status) + output)

    def test_distinct_whole_contexts_fit_assignments_when_the_union_cannot(self):
        with self.fixture() as repo:
            bodies = {name: (f"# {name} contract\n" * 3_000)
                      for name in ("owner.py", "integration.py")}
            for name, body in bodies.items():
                (repo / name).write_bytes(body.encode("utf-8"))
                self.git(repo, "add", name)
            self.git(repo, "commit", "--amend", "--no-edit", "-q")
            manifest = self.manifest(repo)
            manifest["contexts"] = [
                {"path": name, "blob": self.git(repo, "rev-parse", "HEAD:" + name), "mode": "100644"}
                for name in bodies
            ]
            for batch, name in zip(manifest["batches"], bodies):
                batch["changes"].append(name)
                batch["contexts"] = [name]
            self.write_manifest(repo, manifest)
            status, sends, output = self.invoke(repo, "--max-prompt-bytes", "190000")
            self.assertEqual(status, 0, output)
            self.assertEqual(len(sends), 2)
            for prompt, own in zip(sends, bodies):
                self.assertLessEqual(len(prompt.encode()), 190_000)
                for name, body in bodies.items():
                    if name == own:
                        self.assertIn(body, prompt)
                        self.assertIn("blob=" + self.git(repo, "rev-parse", "HEAD:" + name), prompt)
                    else:
                        self.assertNotIn(body, prompt)
                        self.assertGreater(len((prompt + body).encode()), 190_000)
            allocation = json.loads((repo.parent / "result.json").read_bytes())["review_allocation"]
            self.assertEqual({row["path"] for row in allocation["contexts"]}, bodies.keys())
            self.assertEqual([row["contexts"] for row in allocation["batches"]],
                             [[name] for name in bodies])

    def test_dry_live_plan_equal_and_all_capacity_checks_precede_send(self):
        with self.fixture() as repo:
            self.write_manifest(repo, self.manifest(repo))
            dry, sends, dry_output = self.invoke(repo, "--dry-run")
            live, _, live_output = self.invoke(repo)
            self.assertEqual((dry, live), (0, 0))
            self.assertFalse(sends)
            plan = lambda text: next(line for line in text.splitlines() if line.startswith("review plan:"))
            self.assertEqual(plan(dry_output), plan(live_output))
            for options in (("--max-review-passes", "1"), ("--max-prompt-bytes", "10000"),
                            ("--source-context", "contract.py"), ("--dataset", "global.md")):
                for dry_option in ((), ("--dry-run",)):
                    status, sends, _ = self.invoke(repo, *options, *dry_option)
                    self.assertNotEqual(status, 0)
                    self.assertFalse(sends)

    def test_late_incomplete_invalid_filtered_and_cross_boundary_findings_block_clean(self):
        for outcome in ("incomplete", "invalid", "filtered", "outside", "integration-finding"):
            with self.subTest(outcome=outcome), self.fixture() as repo:
                self.write_manifest(repo, self.manifest(repo))

                def engine(index, report):
                    if index != 2:
                        return report
                    if outcome == "incomplete":
                        report["review_completion"] = "incomplete"
                    elif outcome == "invalid":
                        report.pop("review_completion")
                    else:
                        report["findings"] = [{
                            "title": "Cross-owner contract is broken", "body": "The first owner hands the wrong value to its caller.",
                            "priority": "P3" if outcome == "filtered" else "P1", "confidence": 0.9,
                            "category": "regression", "source_attribution": None,
                            "code_location": {"file_path": "retired.py" if outcome == "outside" else "first.py", "line": 1},
                        }]
                    return report

                status, sends, output = self.invoke(repo, engine=engine)
                self.assertEqual(len(sends), 2)
                self.assertNotIn("scoped-clean:", output)
                if outcome != "filtered":
                    self.assertNotEqual(status, 0)
                if outcome not in {"invalid"}:
                    report = json.loads((repo.parent / "result.json").read_bytes())
                    expected = {"incomplete": "incomplete", "filtered": "filtered", "outside": "incomplete",
                                "integration-finding": "findings"}[outcome]
                    self.assertEqual(report["review_status"], expected)

    def test_manifest_and_context_topology_changes_stop_later_assignments(self):
        for mutation in ("manifest", "source", "topology"):
            with self.subTest(mutation=mutation), self.fixture() as repo:
                self.write_manifest(repo, self.manifest(repo))

                def engine(index, report):
                    if index == 1:
                        if mutation == "manifest":
                            (repo / ".review/batches.json").write_bytes(b"{}")
                        elif mutation == "source":
                            (repo / "contract.py").write_bytes(b"changed\n")
                        else:
                            data = (repo / ".review/batches.json").read_bytes()
                            (repo / ".review").rename(repo / ".review-old")
                            (repo / ".review").mkdir()
                            (repo / ".review/batches.json").write_bytes(data)
                    return report

                status, sends, output = self.invoke(repo, engine=engine)
                self.assertNotEqual(status, 0)
                self.assertEqual(len(sends), 1)
                self.assertNotIn("scoped-clean", output)

    def test_hardlinked_outputs_replace_only_their_selected_entries(self):
        with self.fixture() as repo:
            self.write_manifest(repo, self.manifest(repo))
            options = []
            originals = []
            for role in ("json-output", "output", "status-output", "preflight-output"):
                original = repo.parent / (role + ".original")
                destination = repo.parent / (role + ".published")
                content = (role + " original bytes\n").encode()
                original.write_bytes(content)
                os.link(original, destination)
                identity = original.stat()
                self.assertTrue(os.path.samefile(original, destination))
                originals.append((original, destination, content, identity))
                options.extend(("--" + role, str(destination)))
            # Exercise real admission, stale status/preflight removal and atomic
            # publication; only the reviewer transport is replaced by the fixture.
            status, sends, output = self.invoke(
                repo, *options, "--preflight-repo", "fixture/example",
            )
            self.assertEqual(status, 0, output)
            self.assertEqual(len(sends), 2)
            for original, destination, content, identity in originals:
                with self.subTest(destination=destination.name):
                    self.assertEqual(original.read_bytes(), content)
                    self.assertEqual((original.stat().st_dev, original.stat().st_ino),
                                     (identity.st_dev, identity.st_ino))
                    self.assertFalse(os.path.samefile(original, destination))
                    self.assertNotEqual(destination.read_bytes(), content)
            self.assertEqual(json.loads(originals[0][1].read_text())["review_status"], "scoped-clean")
            self.assertEqual(json.loads(originals[2][1].read_text())["status"], "scoped-clean")
            preflight = json.loads(originals[3][1].read_text().splitlines()[1])
            self.assertEqual(preflight["completion"], "complete")

    def test_native_preflight_requires_every_assignment_complete(self):
        for complete in (True, False):
            with self.subTest(complete=complete), self.fixture() as repo:
                self.write_manifest(repo, self.manifest(repo))
                preflight = repo.parent / "preflight.txt"

                def engine(index, report):
                    if index == 2 and not complete:
                        report["review_completion"] = "incomplete"
                    return report

                status, sends, output = self.invoke(
                    repo, "--preflight-output", str(preflight), "--preflight-repo", "fixture/example",
                    engine=engine,
                )
                self.assertEqual(len(sends), 2)
                self.assertEqual(status, 0 if complete else 2, output)
                payload = json.loads(preflight.read_bytes().split(b"\n")[1])
                self.assertEqual(payload["completion"], "complete" if complete else "partial")
                self.assertIn("status scoped-clean" if complete else "status incomplete", payload["summary"])


    def test_path_admission_rejects_source_root_replacement(self):
        with tempfile.TemporaryDirectory(prefix="autoreview-path-root-change-") as temporary:
            root = Path(temporary).resolve()
            repo = root / "repo"
            source = root / "external"
            trusted = root / "trusted-bin"
            for directory in (repo, source, trusted):
                directory.mkdir()
            boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
            token = boundary.set((source,))
            original_scandir = os.scandir

            def replace_root_during_scan(path):
                children = original_scandir(path)
                if Path(path) == trusted:
                    # A filesystem actor replaces the protected root after
                    # admission starts. No stale identity set may be published.
                    source.rename(root / "displaced-source")
                    source.mkdir()
                return children

            try:
                with mock.patch.dict(os.environ, {"PATH": str(trusted)}), mock.patch.dict(
                    self.helper["safe_engine_path"].__globals__, {"DEFAULT_ENGINE_PATHS": ()},
                ):
                    with mock.patch("os.scandir", side_effect=replace_root_during_scan):
                        with self.assertRaisesRegex(SystemExit, "source roots changed"):
                            self.helper["safe_engine_path"](repo)
                    # A subsequent admission must recapture the now-stable root.
                    self.assertEqual(self.helper["safe_engine_path"](repo), str(trusted))
            finally:
                boundary.reset(token)


@unittest.skipIf(os.name == "nt", "exercises POSIX env shebang execution")
class ExecutableSearchPathTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))
        temporary = tempfile.TemporaryDirectory(prefix="autoreview-child-path-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "reviewed"
        self.source = self.root / "external"
        self.contaminated = self.root / "operator-bin"
        self.trusted = self.root / "trusted-bin"
        for directory in (self.repo, self.source, self.contaminated, self.trusted):
            directory.mkdir()
        boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
        token = boundary.set((self.source,))
        self.addCleanup(boundary.reset, token)
        environment = mock.patch.dict(os.environ, {
            "PATH": os.pathsep.join(map(str, (self.contaminated, self.trusted))),
            "HOME": str(self.root),
        }, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        defaults = mock.patch.dict(self.helper["safe_engine_path"].__globals__, {"DEFAULT_ENGINE_PATHS": ()})
        defaults.start()
        self.addCleanup(defaults.stop)

    def executable(self, path, body):
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)
        return path

    def test_trusted_wrapper_child_lookup_stays_outside_sources(self):
        # Use an arbitrary command name: the boundary must cover future tools,
        # not an allowlist of known Python/Node interpreter names.
        command = "autoreview-fixture-interpreter"
        marker = self.root / "source-interpreter-ran"
        source_interpreter = self.executable(
            self.source / command, ": > " + shlex.quote(str(marker)) + "\nprintf 'source-selected\\n'\n",
        )
        (self.contaminated / command).symlink_to(source_interpreter)
        self.executable(self.trusted / command, "printf 'trusted-selected\\n'\n")
        wrapper_directory = self.root / "wrapper-bin"
        wrapper_directory.mkdir()
        wrapper = wrapper_directory / "reviewer"
        wrapper.write_text("#!/usr/bin/env " + command + "\n")
        wrapper.chmod(0o755)
        selected = self.helper["resolve_command"](str(wrapper), self.repo)
        env = self.helper["safe_engine_env"](self.repo, [wrapper.parent], engine="codex")
        result = subprocess.run([selected, "--version"], env=env, cwd=self.root,
                                capture_output=True, text=True, check=False)
        self.assertFalse(marker.exists(), "source-owned child interpreter executed")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "trusted-selected\n")
        self.assertNotIn(str(self.contaminated), env["PATH"].split(os.pathsep))

    def test_broken_and_nonexecutable_source_entries_exclude_the_whole_directory(self):
        for owner in (self.repo, self.source):
            for state in ("missing", "nonexecutable"):
                with self.subTest(owner=owner.name, state=state):
                    target = owner / state
                    if state == "nonexecutable":
                        target.write_text("not executable yet")
                        target.chmod(0o644)
                    link = self.contaminated / "future-command"
                    link.symlink_to(target)
                    try:
                        self.assertEqual(self.helper["safe_engine_path"](
                            self.repo, [self.contaminated]), str(self.trusted))
                    finally:
                        link.unlink()

    def test_later_admission_rechecks_retargeted_link(self):
        target = self.executable(self.trusted / "tool", "exit 0\n")
        source_target = self.executable(self.source / "tool", "exit 99\n")
        link = self.contaminated / "tool"
        link.symlink_to(target)
        self.assertEqual(self.helper["safe_engine_path"](self.repo),
                         os.pathsep.join(map(str, (self.contaminated, self.trusted))))
        link.unlink()
        link.symlink_to(source_target)
        self.assertEqual(self.helper["safe_engine_path"](self.repo), str(self.trusted))

    def test_admission_rejects_a_checked_link_retargeted_into_source(self):
        target = self.executable(self.trusted / "tool", "exit 0\n")
        source_target = self.executable(self.source / "tool", "exit 99\n")
        link = self.contaminated / "tool"
        link.symlink_to(target)
        original_scandir = os.scandir

        def retarget_after_first_directory(path):
            children = original_scandir(path)
            if Path(path) == self.trusted:
                # The first directory has already passed its raw link checks.
                # Its ownership observation must still agree at publication.
                link.unlink()
                link.symlink_to(source_target)
            return children

        with mock.patch("os.scandir", side_effect=retarget_after_first_directory):
            with self.assertRaisesRegex(SystemExit, "filesystem paths changed"):
                self.helper["safe_engine_path"](self.repo)
        self.assertEqual(self.helper["safe_engine_path"](self.repo), str(self.trusted))
        self.assertFalse(self.helper["external_env_path"](self.repo, str(link)))
        link.unlink()
        link.symlink_to(target)
        self.assertTrue(self.helper["external_env_path"](self.repo, str(link)))

    def test_admission_rechecks_missing_link_targets_before_publication(self):
        future = self.root / "future-tool"
        link = self.contaminated / "tool"
        link.symlink_to(future)
        source_target = self.executable(self.source / "tool", "exit 99\n")
        original_scandir = os.scandir

        def create_target_after_first_directory(path):
            children = original_scandir(path)
            if Path(path) == self.trusted:
                # A previously absent target becomes a source-selected link.
                future.symlink_to(source_target)
            return children

        with mock.patch("os.scandir", side_effect=create_target_after_first_directory):
            with self.assertRaisesRegex(SystemExit, "filesystem paths changed"):
                self.helper["safe_engine_path"](self.repo)
        self.assertEqual(self.helper["safe_engine_path"](self.repo), str(self.trusted))

    def test_admission_rechecks_component_topology_with_unchanged_referents(self):
        for mutation in ("prefix", "symlink", "missing"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(dir=self.root) as temporary:
                root = Path(temporary)
                dependencies = root / "dependencies"
                dependencies.mkdir()
                target = self.executable(dependencies / "tool", "exit 0\n")
                link = self.contaminated / "tool"
                future = root / "future"
                alias = self.source / mutation
                link.symlink_to(future / "tool" if mutation == "missing" else target)
                original_scandir = os.scandir

                def change_after_component_capture(path):
                    children = original_scandir(path)
                    if Path(path) == self.trusted:
                        # Followed identities remain unchanged, but a source-owned
                        # component now controls the already inspected lookup.
                        if mutation == "prefix":
                            displaced = root / "displaced"
                            dependencies.rename(displaced)
                            alias.symlink_to(displaced, target_is_directory=True)
                            dependencies.symlink_to(alias, target_is_directory=True)
                        elif mutation == "symlink":
                            alias.symlink_to(target)
                            link.unlink()
                            link.symlink_to(alias)
                        else:
                            # Both followed observations still report missing.
                            future.symlink_to(alias, target_is_directory=True)
                    return children

                try:
                    with mock.patch("os.scandir", side_effect=change_after_component_capture):
                        with self.assertRaisesRegex(SystemExit, "filesystem paths changed"):
                            self.helper["safe_engine_path"](self.repo)
                    self.assertFalse(self.helper["external_env_path"](self.repo, str(link)))
                finally:
                    link.unlink()
                    alias.unlink(missing_ok=True)

    def test_admission_rechecks_custody_metadata_after_component_capture(self):
        for mutation in ("mode", "hardlink"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(dir=self.root) as temporary:
                target = self.executable(Path(temporary) / "tool", "exit 0\n")
                link = self.contaminated / "tool"
                link.symlink_to(target)
                shared = self.source / "shared-tool"
                original_scandir = os.scandir

                def change_after_component_capture(path):
                    children = original_scandir(path)
                    if Path(path) == self.trusted:
                        # The inode is stable while metadata used by admission
                        # changes; a new source hardlink also removes custody.
                        if mutation == "mode":
                            target.chmod(0o555)
                        else:
                            os.link(target, shared)
                    return children

                try:
                    with mock.patch("os.scandir", side_effect=change_after_component_capture):
                        with self.assertRaisesRegex(SystemExit, "filesystem paths changed"):
                            self.helper["safe_engine_path"](self.repo)
                    if mutation == "hardlink":
                        self.assertFalse(self.helper["independent_file_custody"](target))
                finally:
                    link.unlink()
                    shared.unlink(missing_ok=True)

    def test_admission_allows_unrelated_sibling_changes(self):
        target = self.executable(self.root / "tool", "exit 0\n")
        (self.contaminated / "tool").symlink_to(target)
        original_scandir = os.scandir

        def create_sibling_after_component_capture(path):
            children = original_scandir(path)
            if Path(path) == self.trusted:
                # Shared ancestors can change their child inventory while all
                # consumed lookup entries and custody remain unchanged.
                sibling = self.root / "unrelated-directory"
                sibling.mkdir()
                (sibling / "note").write_text("unrelated activity\n")
            return children

        with mock.patch("os.scandir", side_effect=create_sibling_after_component_capture):
            self.assertEqual(self.helper["safe_engine_path"](self.repo),
                             os.pathsep.join(map(str, (self.contaminated, self.trusted))))


@unittest.skipIf(os.name == "nt", "POSIX executable and symlink fixtures")
class GitConsumerPathTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))
        temporary = tempfile.TemporaryDirectory(prefix="autoreview-git-consumer-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "reviewed"
        self.source = self.root / "external"
        self.home = self.root / "operator-home"
        for directory in (self.repo, self.source, self.home):
            directory.mkdir()
        boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
        token = boundary.set((self.source,))
        self.addCleanup(boundary.reset, token)
        env = {key: os.environ[key] for key in ("PATH", "DEVELOPER_DIR") if key in os.environ}
        env["HOME"] = str(self.home)
        environment = mock.patch.dict(os.environ, env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_pr_base_cannot_reinsert_contaminated_selected_git_directory(self):
        git_bin = self.root / "git-bin"
        gh_bin = self.root / "gh-bin"
        interpreters = self.root / "interpreters"
        for directory in (git_bin, gh_bin, interpreters):
            directory.mkdir()
        unsafe_marker = self.root / "source-interpreter-ran"
        trusted_marker = self.root / "trusted-interpreter-ran"
        command = "fixture-git-interpreter"
        selected_git = git_bin / "git"
        selected_git.write_text("#!/usr/bin/env " + command + "\n")
        selected_git.chmod(0o755)
        for interpreter, marker in ((self.source / command, unsafe_marker),
                                    (interpreters / command, trusted_marker)):
            interpreter.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\n")
            interpreter.chmod(0o755)
        link = git_bin / command
        link.symlink_to(self.source / command)
        gh = gh_bin / "gh"
        gh.write_text("#!/bin/sh\ngit --version || exit $?\nprintf 'maintenance\\n'\n")
        gh.chmod(0o755)
        path = os.pathsep.join(map(str, (git_bin, gh_bin, interpreters)))
        with mock.patch.dict(os.environ, {"PATH": path, "AUTOREVIEW_GIT": str(selected_git)}):
            failure = None
            try:
                self.helper["detect_pr_base"](self.repo)
            except SystemExit as exc:
                failure = str(exc)
            self.assertFalse(unsafe_marker.exists(), "PR discovery executed a source-owned interpreter")
            self.assertIsNotNone(failure, "unsafe selected Git must require an explicit base")
            self.assertIn("pass --base explicitly", failure)
            # Removing only the source-owned link restores the same approved
            # Git wrapper; a different system Git must not silently replace it.
            link.unlink()
            self.assertEqual(self.helper["detect_pr_base"](self.repo), "origin/maintenance")
            self.assertTrue(trusted_marker.exists())

    def test_source_owned_default_ignore_and_global_config_cannot_hide_local_work(self):
        fixture_git(self.repo, "init", "-q", check=True, capture_output=True)
        (self.repo / "visible.py").write_text("local_change = True\n")
        (self.repo / "local-ignored.py").write_text("ignored_by_repo = True\n")
        (self.repo / ".gitignore").write_text("local-ignored.py\n")
        fixture_git(self.repo, "add", ".gitignore", check=True, capture_output=True)
        config_dir = self.home / ".config" / "git"
        config_dir.mkdir(parents=True)
        excludes = self.home / "operator-ignore"
        excludes.write_text("visible.py\n")
        unsafe_ignore = self.source / "ignore"
        unsafe_ignore.write_text("visible.py\n")
        unsafe_config = self.source / "config"
        unsafe_config.write_text("[core]\n excludesFile = " + str(excludes) + "\n")
        # Exercise Git's actual default ignore and both global config entry
        # points; source-directed excludes must not turn local work into clean state.
        for leaf, target in ((config_dir / "ignore", unsafe_ignore),
                             (self.home / ".gitconfig", unsafe_config),
                             (config_dir / "config", unsafe_config)):
            with self.subTest(path=str(leaf.relative_to(self.home))):
                leaf.symlink_to(target)
                try:
                    try:
                        selected = self.helper["untracked_sources"](self.repo).files
                    except SystemExit as exc:
                        self.assertRegex(str(exc), "Git.*outside reviewed source roots")
                    else:
                        self.fail(f"source-owned Git input admitted; untracked files: {selected!r}")
                finally:
                    leaf.unlink()
        # Normal repository ignores and operator-owned global ignores retain
        # their usual effect once every effective path is outside source roots.
        self.assertEqual(set(self.helper["untracked_sources"](self.repo).files), {"visible.py"})
        (config_dir / "ignore").write_text("visible.py\n")
        self.assertFalse(self.helper["untracked_sources"](self.repo).files)
        (config_dir / "ignore").unlink()
        xdg = self.root / "operator-xdg"
        (xdg / "git").mkdir(parents=True)
        (xdg / "git" / "ignore").symlink_to(unsafe_ignore)
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg)}):
            with self.assertRaisesRegex(SystemExit, "Git.*outside reviewed source roots"):
                self.helper["safe_gh_env"](self.repo)

    def test_path_serialization_cannot_introduce_source_directories(self):
        marker = self.root / "serialized-source-interpreter-ran"
        command = "fixture-serialization-interpreter"
        interpreter = self.source / command
        interpreter.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\n")
        interpreter.chmod(0o755)
        clean_bin = self.root / "clean-bin"
        clean_bin.mkdir()
        clean = clean_bin / command
        clean.write_text("#!/bin/sh\nprintf 'trusted-interpreter\\n'\n")
        clean.chmod(0o755)
        # One valid directory spells two PATH components, the first of which
        # is the declared source. Its actual files are all outside that source.
        ambiguous = Path(str(self.source) + os.pathsep + str(self.root / "tail"))
        ambiguous.mkdir(parents=True)
        wrapper = ambiguous / "reviewer"
        wrapper.write_text("#!/usr/bin/env " + command + "\n")
        wrapper.chmod(0o755)
        alias = self.root / "ordinary-looking-bin"
        alias.symlink_to(ambiguous, target_is_directory=True)
        for use_alias in (False, True):
            with self.subTest(alias=use_alias):
                marker.unlink(missing_ok=True)
                caller_path = os.pathsep.join(map(str, (alias, clean_bin))) if use_alias else str(clean_bin)
                with mock.patch.dict(os.environ, {"PATH": caller_path}):
                    env = self.helper["safe_engine_env"](
                        self.repo, [] if use_alias else [ambiguous], engine="codex",
                    )
                result = subprocess.run([str(wrapper), "--version"], cwd=self.root,
                                        env=env, capture_output=True, text=True, check=False)
                self.assertFalse(marker.exists(), "PATH serialization introduced a source executable")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "trusted-interpreter\n")
                self.assertNotIn(str(self.source), env["PATH"].split(os.pathsep))

    def test_initial_lookup_keeps_source_link_provenance(self):
        marker = self.root / "source-selected-command-ran"
        installed = self.root / "installed"
        installed.mkdir()
        command = installed / "fixture-reviewer"
        command.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\n")
        command.chmod(0o755)
        selector = self.source / "selected-installation"
        selector.symlink_to(installed, target_is_directory=True)
        alias = self.root / "operator-alias"
        alias.symlink_to(selector, target_is_directory=True)
        with mock.patch.dict(os.environ, {"PATH": str(alias)}):
            selected = self.helper["find_command"](command.name, self.repo)
            if selected:
                subprocess.run([selected], check=True, env={"PATH": "/usr/bin:/bin"})
            self.assertFalse(marker.exists(), "initial lookup executed source-selected host code")
            self.assertIsNone(selected)
            # The same operator alias is valid when it no longer traverses a
            # source-owned selector; ordinary external symlinks remain supported.
            alias.unlink()
            alias.symlink_to(installed, target_is_directory=True)
            selected = self.helper["resolve_command"](command.name, self.repo)
            subprocess.run([selected], check=True, env={"PATH": "/usr/bin:/bin"})
            self.assertTrue(marker.exists())


@unittest.skipIf(os.name == "nt", "POSIX executable, list separator and custody fixtures")
class ExecutableCustodyTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))
        temporary = tempfile.TemporaryDirectory(prefix="autoreview-executable-custody-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "reviewed"
        self.source = self.root / "external"
        self.home = self.root / "home"
        self.installed = self.root / "installed"
        self.clean = self.root / "clean"
        for path in (self.repo, self.source, self.home, self.installed, self.clean):
            path.mkdir()
        boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
        token = boundary.set((self.source,))
        self.addCleanup(boundary.reset, token)
        environment = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "PATH": os.pathsep.join(map(str, (self.installed, self.clean))),
        }, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def executable(self, path, body):
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)
        return path

    def test_empty_vetted_path_cannot_run_a_checkout_interpreter(self):
        (self.repo / ".git").mkdir()
        marker = self.root / "checkout-interpreter-ran"
        command = "fixture-empty-path-interpreter"
        self.executable(self.repo / command, ": > " + shlex.quote(str(marker)) + "\n")
        wrapper = self.installed / "git-wrapper"
        wrapper.write_text("#!/usr/bin/env " + command + "\n")
        wrapper.chmod(0o755)
        boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
        token = boundary.set((self.source, *(Path(path) for path in self.helper["DEFAULT_ENGINE_PATHS"])))
        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            with mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin", "AUTOREVIEW_GIT": str(wrapper)}):
                with contextlib.redirect_stderr(io.StringIO()):
                    result = self.helper["preflight_git"]()
            self.assertFalse(marker.exists(), "empty child PATH searched the reviewed working directory")
            self.assertFalse(result)
            # A real, clean interpreter directory permits the same explicit wrapper.
            self.executable(self.clean / command, "exit 0\n")
            with mock.patch.dict(os.environ, {"PATH": str(self.clean), "AUTOREVIEW_GIT": str(wrapper)}):
                self.assertTrue(self.helper["preflight_git"]())
        finally:
            os.chdir(previous)
            boundary.reset(token)

    def test_certificate_and_openclaw_lists_preserve_single_path_members(self):
        self.executable(self.installed / "openclaw", "exit 0\n")
        ambiguous = Path(str(self.source) + os.pathsep + str(self.root / "tail"))
        ambiguous.mkdir(parents=True)
        alias = self.root / "ordinary-alias"
        alias.symlink_to(ambiguous, target_is_directory=True)
        for key in ("SSL_CERT_DIR", "OPENCLAW_INCLUDE_ROOTS"):
            with self.subTest(key=key):
                for trusted in (False, True):
                    value = os.pathsep.join(map(str, (self.clean, self.home))) if trusted else str(alias)
                    run_root = self.root / (key + str(trusted))
                    run_root.mkdir()
                    with mock.patch.dict(os.environ, {key: value}):
                        env = self.helper["openclaw_runtime_env"](
                            self.repo, str(self.installed / "openclaw"), run_root,
                        )
                    if trusted:
                        self.assertEqual(env[key].split(os.pathsep), [str(self.clean), str(self.home)])
                    else:
                        self.assertNotIn(key, env, "normalization introduced a source-owned list member")

    def test_writable_hardlink_cannot_supply_selected_or_child_executables(self):
        marker = self.root / "source-hardlink-ran"
        name = "fixture-hardlink-interpreter"
        source = self.executable(self.source / name, "exit 0\n")
        linked = self.installed / name
        os.link(source, linked)
        source.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\n")
        trusted = self.executable(self.clean / name, "printf 'trusted\\n'\n")
        wrapper = self.root / "wrapper"
        wrapper.write_text("#!/usr/bin/env " + name + "\n")
        wrapper.chmod(0o755)
        for mode in (0o755, 0o555, 0o644):
            with self.subTest(mode=oct(mode)):
                marker.unlink(missing_ok=True)
                source.chmod(mode)
                selected = self.helper["find_command"](str(linked), self.repo)
                if selected:
                    subprocess.run([selected], check=True)
                env = self.helper["safe_engine_env"](self.repo, engine="codex")
                result = subprocess.run([str(wrapper)], cwd=self.repo, env=env,
                                        capture_output=True, text=True, check=True)
                self.assertFalse(marker.exists(), "source writes changed an admitted executable")
                self.assertIsNone(selected)
                self.assertNotIn(str(self.installed), env["PATH"].split(os.pathsep),
                                 "shared nonexecutables also lack independent import custody")
                self.assertEqual(result.stdout, "trusted\n")
        source.chmod(0o755)
        # Copying the same bytes establishes independent custody and restores
        # ordinary operator-installed executable selection.
        linked.unlink()
        shutil.copy2(trusted, linked)
        self.assertEqual(self.helper["resolve_command"](str(linked), self.repo), str(linked))
        self.assertIn(str(self.installed), self.helper["safe_engine_path"](self.repo).split(os.pathsep))

    def test_immutable_system_hardlinks_remain_available(self):
        interpreter = Path("/usr/bin/perl")
        if not interpreter.is_file():
            self.skipTest("system Perl is unavailable")
        metadata = interpreter.stat()
        if (metadata.st_nlink < 2 or metadata.st_uid == os.geteuid()
                or metadata.st_mode & 0o022 or os.access(interpreter, os.W_OK)):
            self.skipTest("system Perl is not an independently owned immutable hardlink")
        # System installations legitimately share immutable executable inodes.
        # They must remain selectable and usable from the admitted system PATH.
        selected = self.helper["resolve_command"](str(interpreter), self.repo)
        env = self.helper["safe_engine_env"](self.repo, engine="codex")
        self.assertIn(str(interpreter.parent.resolve()), env["PATH"].split(os.pathsep))
        result = subprocess.run([selected, "-e", "print qq(trusted\\n)"], env=env,
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "trusted\n")

    def test_source_hardlink_cannot_supply_transport_configuration(self):
        source = self.source / "source-ca.pem"
        source.write_text("synthetic certificate fixture\n")
        certificate = self.root / "operator-ca.pem"
        os.link(source, certificate)
        with mock.patch.dict(os.environ, {"SSL_CERT_FILE": str(certificate)}):
            env = self.helper["safe_engine_env"](self.repo, engine="codex")
            self.assertNotIn("SSL_CERT_FILE", env)
            certificate.unlink()
            shutil.copy2(source, certificate)
            self.assertEqual(self.helper["safe_engine_env"](self.repo, engine="codex")["SSL_CERT_FILE"],
                             str(certificate))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux permitted capability boundary")
    def test_shared_file_custody_rejects_mutating_or_unreadable_capabilities(self):
        interpreter = Path("/usr/bin/perl")
        if not interpreter.is_file() or interpreter.stat().st_nlink < 2:
            self.skipTest("immutable system hardlink fixture unavailable")
        if not self.helper["independent_file_custody"](interpreter):
            self.skipTest("current process cannot establish independent system file custody")
        # Feed the kernel-status boundary, preserving real inode ownership and
        # access checks. Any permitted capability invalidates custody even when
        # CapEff is empty. Include SETUID/SETGID/SETPCAP and unknown future bits
        # so identity-changing and unclassified authority cannot evade the gate.
        for mask in (1 << 0, 1 << 1, 1 << 3, 1 << 6, 1 << 7, 1 << 8, 1 << 10, 1 << 63):
            with self.subTest(mask=mask), mock.patch.object(
                Path, "read_text", return_value=f"CapEff:\t0000000000000000\nCapPrm:\t{mask:016x}\n",
            ):
                self.assertFalse(self.helper["independent_file_custody"](interpreter))
        for content in ("", "CapEff: 0\n", "CapPrm:\tnot-hex\n", "CapPrm: 0\nCapPrm: 0\n"):
            with self.subTest(content=content), mock.patch.object(Path, "read_text", return_value=content):
                self.assertFalse(self.helper["independent_file_custody"](interpreter))
        with mock.patch.object(Path, "read_text", side_effect=FileNotFoundError):
            self.assertFalse(self.helper["independent_file_custody"](interpreter))
        with mock.patch.object(Path, "read_text", return_value="CapEff: 0\nCapPrm:\t0000000000000000\n"):
            self.assertTrue(self.helper["independent_file_custody"](interpreter))


@unittest.skipUnless(os.name == "nt", "requires native Windows ACL and hardlink behavior")
class WindowsHardlinkCustodyTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))

    def test_path_rejects_writable_and_readonly_source_hardlink(self):
        with tempfile.TemporaryDirectory(prefix="autoreview-windows-custody-") as directory:
            root = Path(directory).resolve()
            repo = root / "repo"
            source = root / "source"
            outside = root / "outside-bin"
            clean = root / "clean-bin"
            for child in (repo, source, outside, clean):
                child.mkdir()
            original = source / "dependency.dll"
            original.write_bytes(b"source-controlled dependency")
            alias = outside / "dependency.dll"
            os.link(original, alias)
            self.assertGreater(alias.stat().st_nlink, 1)
            self.assertTrue(os.path.samefile(original, alias))
            # A regular non-executable neighbor can carry DLL/import payloads.
            # Read-only attributes do not remove the owner's ACL mutation rights.
            source_roots = self.helper["UNTRUSTED_SOURCE_ROOTS"]
            token = source_roots.set((source,))
            try:
                for readonly in (False, True):
                    with self.subTest(readonly=readonly):
                        original.chmod(stat.S_IREAD if readonly else stat.S_IREAD | stat.S_IWRITE)
                        rejections = []
                        self.assertFalse(self.helper["windows_file_custody"](alias, on_rejection=rejections.append))
                        self.assertEqual(len(rejections), 1)
                        self.assertRegex(rejections[0], r"^primary token permits file mutation \(mask 0x[0-9a-f]+\)$")
                        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join(map(str, (outside, clean)))}):
                            admitted = self.helper["safe_engine_path"](repo).split(os.pathsep)
                        self.assertNotIn(str(outside), admitted)
                        self.assertIn(str(clean), admitted)
                self.assertEqual(alias.read_bytes(), b"source-controlled dependency")
                original.chmod(stat.S_IREAD | stat.S_IWRITE)
                alias.unlink()
                shutil.copyfile(original, alias)
                self.assertEqual(alias.read_bytes(), original.read_bytes())
                self.assertEqual(alias.stat().st_nlink, 1)
                # An ordinary independent user installation has no source-owned
                # inode alias and remains usable with identical file contents.
                with mock.patch.dict(os.environ, {"PATH": str(outside)}):
                    self.assertIn(str(outside), self.helper["safe_engine_path"](repo).split(os.pathsep))
            finally:
                original.chmod(stat.S_IREAD | stat.S_IWRITE)
                source_roots.reset(token)

    def system_library(self):
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetSystemDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
        kernel.GetSystemDirectoryW.restype = wintypes.UINT
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel.GetSystemDirectoryW(buffer, len(buffer))
        self.assertTrue(0 < length < len(buffer), "cannot identify the native Windows system directory")
        library = Path(buffer.value) / "kernel32.dll"
        self.assertGreater(library.stat().st_nlink, 1, "native CI must supply a serviced NTFS system DLL")
        return library

    @contextlib.contextmanager
    def system_custody_token(self, remove_privileges):
        import ctypes
        from ctypes import wintypes

        class Luid(ctypes.Structure):
            _fields_ = [("low", wintypes.DWORD), ("high", wintypes.LONG)]

        class LuidAndAttributes(ctypes.Structure):
            _fields_ = [("luid", Luid), ("attributes", wintypes.DWORD)]

        class TokenPrivilege(ctypes.Structure):
            _fields_ = [("count", wintypes.DWORD), ("privileges", LuidAndAttributes * 1)]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        security = ctypes.WinDLL("advapi32", use_last_error=True)
        for name in ("GetCurrentThread", "GetCurrentProcess"):
            function = getattr(kernel, name)
            function.argtypes = []
            function.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        security.OpenThreadToken.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, ctypes.POINTER(wintypes.HANDLE),
        ]
        security.OpenThreadToken.restype = wintypes.BOOL
        security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        security.OpenProcessToken.restype = wintypes.BOOL
        security.DuplicateTokenEx.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        security.DuplicateTokenEx.restype = wintypes.BOOL
        security.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(Luid)]
        security.LookupPrivilegeValueW.restype = wintypes.BOOL
        security.AdjustTokenPrivileges.argtypes = [
            wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(TokenPrivilege), wintypes.DWORD,
            ctypes.c_void_p, ctypes.c_void_p,
        ]
        security.AdjustTokenPrivileges.restype = wintypes.BOOL
        security.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
        ]
        security.GetTokenInformation.restype = wintypes.BOOL
        security.SetThreadToken.argtypes = [ctypes.c_void_p, wintypes.HANDLE]
        security.SetThreadToken.restype = wintypes.BOOL
        library = self.system_library()
        source = wintypes.HANDLE()
        prior_thread = wintypes.HANDLE()
        duplicate = wintypes.HANDLE()
        had_thread_token = False
        installed = False
        try:
            had_thread_token = bool(security.OpenThreadToken(
                kernel.GetCurrentThread(), 0x000E, True, ctypes.byref(prior_thread),
            ))
            if not had_thread_token:
                self.assertEqual(ctypes.get_last_error(), 1008)
            self.assertTrue(security.OpenProcessToken(
                kernel.GetCurrentProcess(), 0x000A, ctypes.byref(source),
            ))
            self.assertTrue(security.DuplicateTokenEx(source, 0x002E, None, 2, 2, ctypes.byref(duplicate)))
            ordinary = set()
            for name in ("SeChangeNotifyPrivilege", "SeShutdownPrivilege", "SeUndockPrivilege",
                         "SeIncreaseWorkingSetPrivilege", "SeTimeZonePrivilege"):
                luid = Luid()
                self.assertTrue(security.LookupPrivilegeValueW(None, name, ctypes.byref(luid)))
                ordinary.add((luid.low, luid.high))
            direct_mutation = set()
            for name in ("SeRestorePrivilege", "SeTakeOwnershipPrivilege"):
                luid = Luid()
                self.assertTrue(security.LookupPrivilegeValueW(None, name, ctypes.byref(luid)))
                direct_mutation.add((luid.low, luid.high))
            data = ctypes.create_string_buffer(65536)
            length = wintypes.DWORD()
            self.assertTrue(security.GetTokenInformation(duplicate, 3, data, len(data), ctypes.byref(length)))
            count = wintypes.DWORD.from_buffer(data).value
            offset = ctypes.sizeof(wintypes.DWORD)
            stride = ctypes.sizeof(LuidAndAttributes)
            self.assertLessEqual(offset + count * stride, length.value)
            available_privileges = []
            # Mutate only a disposable token. The original process/thread token
            # and filesystem ACLs remain unchanged throughout this fixture.
            for index in range(count):
                original = LuidAndAttributes.from_buffer(data, offset + index * stride)
                if (original.luid.low, original.luid.high) in ordinary:
                    continue
                available_privileges.append((original.luid.low, original.luid.high))
                state = TokenPrivilege()
                state.count = 1
                state.privileges[0].luid = original.luid
                # Remove the original two denylisted privileges in both cases;
                # the negative case must catch other authority such as Debug.
                remove = remove_privileges or (original.luid.low, original.luid.high) in direct_mutation
                state.privileges[0].attributes = 4 if remove else 0
                self.assertTrue(security.AdjustTokenPrivileges(duplicate, False, ctypes.byref(state), 0, None, None))
                self.assertEqual(ctypes.get_last_error(), 0)
            self.assertTrue(security.SetThreadToken(None, duplicate))
            installed = True
            yield library, available_privileges
        finally:
            try:
                if installed:
                    self.assertTrue(security.SetThreadToken(None, prior_thread if had_thread_token else None))
            finally:
                if duplicate.value:
                    kernel.CloseHandle(duplicate)
                if source.value:
                    kernel.CloseHandle(source)
                if prior_thread.value:
                    kernel.CloseHandle(prior_thread)

    def test_windows_system_hardlink_retains_trusted_custody(self):
        # This proof requires a standard-user primary process. Impersonating a
        # restricted token inside an elevated process does not satisfy it.
        library = self.system_library()
        before = library.stat()
        rejections = []
        self.assertTrue(self.helper["windows_file_custody"](library, on_rejection=rejections.append),
                        "run native positive proof with an unprivileged primary token")
        self.assertEqual(rejections, [])
        after = library.stat()
        self.assertEqual((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns),
                         (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns))
        # Exercise the mandatory native cleanup selection and the real system
        # search directory; accepting one DLL alone does not prove startup.
        with tempfile.TemporaryDirectory(prefix="autoreview-windows-system-") as directory:
            repo = Path(directory).resolve()
            binding = self.helper["_capture_windows_taskkill"](repo)
            with mock.patch.dict(os.environ, {"PATH": str(library.parent)}):
                admitted = self.helper["safe_engine_path"](repo).split(os.pathsep)
            self.assertIn(str(library.parent.resolve()), admitted)
            result = subprocess.run([str(binding.path), "/?"], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_descriptor_failure_reports_only_stage_and_error(self):
        with tempfile.TemporaryDirectory(prefix="autoreview-windows-custody-") as directory:
            missing = Path(directory) / "missing.dll"
            rejections = []
            self.assertFalse(self.helper["windows_file_custody"](missing, on_rejection=rejections.append))
            self.assertEqual(len(rejections), 1)
            self.assertRegex(rejections[0], r"^security descriptor unavailable \(error [0-9]+\)$")

    def test_windows_restricted_thread_cannot_hide_primary_authority(self):
        for remove in (False, True):
            with self.subTest(remove=remove), self.system_custody_token(remove) as (library, available):
                if not available:
                    self.skipTest("negative proof requires an available nonordinary primary privilege")
                # RevertToSelf can recover the original primary authority. The
                # original process token is never changed by this fixture.
                self.assertFalse(self.helper["windows_file_custody"](library))


@unittest.skipIf(os.name == "nt", "POSIX Python launcher and filesystem links")
class SelectedExecutableDirectoryTests(unittest.TestCase):
    @contextlib.contextmanager
    def in_repo(self):
        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            yield
        finally:
            os.chdir(previous)

    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))
        temporary = tempfile.TemporaryDirectory(prefix="autoreview-selected-directory-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "repo"
        self.source = self.root / "source"
        self.install = self.root / "install"
        self.aliases = self.root / "aliases"
        self.home = self.root / "home"
        for path in (self.repo, self.source, self.install, self.aliases, self.home):
            path.mkdir()
        (self.repo / ".git").mkdir()
        self.marker = self.root / "executed"
        self.payload = self.source / "adjacent_payload.py"
        self.payload.write_text("from pathlib import Path\nPath(" + repr(str(self.marker)) + ").write_text('source')\n")
        boundary = self.helper["UNTRUSTED_SOURCE_ROOTS"]
        token = boundary.set((self.source,))
        self.addCleanup(boundary.reset, token)
        environment = mock.patch.dict(os.environ, {
            "PATH": "/usr/bin:/bin", "HOME": str(self.home),
        }, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def launcher(self, directory, name="launcher"):
        executable = directory / name
        # The real interpreter adds the script directory independently of PATH.
        executable.write_text("#!" + sys.executable + " -S\n"
                              "import sys\nsys.dont_write_bytecode = True\n"
                              "import adjacent_payload\n"
                              "print('99.0.0 --safe-mode --setting-sources --strict-mcp-config --disallowedTools --tools')\n")
        executable.chmod(0o755)
        return executable

    def independent_payload(self, directory):
        (directory / "adjacent_payload.py").write_text(
            "from pathlib import Path\nPath(" + repr(str(self.marker)) + ").write_text('independent')\n")

    def test_git_probe_refuses_source_siblings_before_launch(self):
        executable = self.launcher(self.install, "git-wrapper")
        sibling = self.install / "adjacent_payload.py"
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                if kind == "symlink":
                    sibling.symlink_to(self.payload)
                else:
                    os.link(self.payload, sibling)
                try:
                    with mock.patch.dict(os.environ, {"AUTOREVIEW_GIT": str(executable)}), \
                            self.in_repo(), contextlib.redirect_stderr(io.StringIO()) as stderr:
                        with self.assertRaises(SystemExit) as rejected:
                            self.helper["safe_git_env"](self.repo)
                        message = str(rejected.exception)
                        self.assertIn(str(executable), message)
                        self.assertIn(str(sibling), message)
                        reason = "independent file custody required" if kind == "hardlink" else "path admission refused"
                        self.assertIn(reason, message)
                        self.assertFalse(self.helper["preflight_git"]())
                        self.assertIn(str(executable), stderr.getvalue())
                        self.assertIn(str(sibling), stderr.getvalue())
                        self.assertIn(reason, stderr.getvalue())
                    self.assertFalse(self.marker.exists(), "Git probe executed a source-owned sibling")
                finally:
                    sibling.unlink()
        self.independent_payload(self.install)
        with mock.patch.dict(os.environ, {"AUTOREVIEW_GIT": str(executable)}), self.in_repo():
            self.assertTrue(self.helper["preflight_git"]())
        self.assertEqual(self.marker.read_text(), "independent")

    def test_engine_probe_requires_lexical_and_resolved_installation_directories(self):
        target = self.launcher(self.install)
        selected = self.aliases / "reviewer"
        selected.symlink_to(target)
        args = argparse.Namespace(claude_bin=str(selected), model="fixture", fallback_model=None)
        for directory in (self.install, self.aliases):
            with self.subTest(directory=directory.name):
                if directory == self.aliases:
                    self.independent_payload(self.install)
                sibling = directory / "adjacent_payload.py"
                sibling.symlink_to(self.payload)
                try:
                    with self.assertRaisesRegex(SystemExit, "trusted installation directories"):
                        self.helper["ensure_claude_isolation_supported"](args, self.repo)
                    self.assertFalse(self.marker.exists())
                finally:
                    sibling.unlink()
        self.independent_payload(self.install)
        self.helper["ensure_claude_isolation_supported"](args, self.repo)
        self.assertEqual(self.marker.read_text(), "independent")

    def test_git_query_rechecks_selected_directory_with_prepared_environment(self):
        selected = self.launcher(self.install, "git-wrapper")
        self.independent_payload(self.install)
        with mock.patch.dict(os.environ, {"AUTOREVIEW_GIT": str(selected)}):
            env = self.helper["safe_git_env"](self.repo)
            result = self.helper["git_bytes"](self.repo, "--version", env=env)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(self.marker.read_text(), "independent")
            self.marker.unlink()
            sibling = self.install / "adjacent_payload.py"
            sibling.unlink()
            sibling.symlink_to(self.payload)
            with self.assertRaisesRegex(SystemExit, "trusted installation directories"):
                self.helper["git_bytes"](self.repo, "--version", env=env)
            self.assertFalse(self.marker.exists(), "prepared environment bypassed fresh launch admission")

    def test_explicit_separator_named_installation_can_launch_without_entering_path(self):
        directory = self.root / "install:slot"
        directory.mkdir()
        selected = self.launcher(directory)
        self.independent_payload(directory)
        args = argparse.Namespace(claude_bin=str(selected), model="fixture", fallback_model=None)
        self.helper["ensure_claude_isolation_supported"](args, self.repo)
        self.assertEqual(self.marker.read_text(), "independent")
        self.assertNotIn(str(directory), self.helper["safe_engine_path"](self.repo).split(os.pathsep))

    def test_provider_auth_command_refuses_source_sibling_before_staging(self):
        selected = self.launcher(self.install)
        sibling = self.install / "adjacent_payload.py"
        sibling.symlink_to(self.payload)
        flags = ["-c", "model_providers.fixture.auth.command=" + json.dumps(str(selected))]
        runtime = self.root / "runtime"
        runtime.mkdir()
        with self.assertRaisesRegex(SystemExit, "trusted installation directories"):
            self.helper["stage_codex_auth_helper"](self.repo, runtime, flags)
        self.assertEqual(list(runtime.iterdir()), [])
        self.assertFalse(self.marker.exists())
        sibling.unlink()
        self.independent_payload(self.install)
        staged = self.helper["stage_codex_auth_helper"](self.repo, runtime, flags)
        command = json.loads(staged[1].partition("=")[2])
        result = subprocess.run([command], cwd=runtime, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.marker.read_text(), "independent")


if __name__ == "__main__":
    unittest.main()
