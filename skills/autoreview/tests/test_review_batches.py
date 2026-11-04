"""Explicit allocations retain one range, whole contracts and aggregate refusals."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
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

    def invoke(self, repo, *options, engine=None, allocated=True, real_engine_probe=False):
        argv = [str(SCRIPT), "--mode", "branch", "--base", "HEAD^", "--engine", "codex",
                "--max-priority", "P2", "--review-batches", ".review/batches.json",
                "--source-context-file", "global.md", "--max-prompt-bytes", "80000",
                "--max-review-passes", "2", "--json-output", str(repo.parent / "result.json"),
                *options]
        if not allocated:
            offset = argv.index("--review-batches")
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
        with mock.patch.dict(self.helper["main_with_args"].__globals__, {
            "repo_root": lambda: repo, "run_engine": run,
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
            trusted = repo.parent / "trusted-codex"
            shutil.copy2(binary, trusted)
            config = repo.parent / "operator-config"
            config.mkdir()
            (upstream / "config.toml").write_text('cli_auth_credentials_store="keyring"\n')
            (config / "config.toml").symlink_to(upstream / "config.toml")
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(config)}):
                status, sends, _ = self.invoke(
                    repo, "--external-source-context-file", ".review/external.json",
                    "--codex-bin", str(trusted), "--dry-run", real_engine_probe=True,
                )
            self.assertNotEqual(status, 0)
            self.assertFalse(sends)
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
                wrapper = repo.parent / "trusted-login-wrapper"
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
                boundary.reset(token)

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
            wrapper = repo.parent / "trusted-git-wrapper"
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
                self.assertIn(str(upstream), prompt)
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


if __name__ == "__main__":
    unittest.main()
