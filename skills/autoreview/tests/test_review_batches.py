"""Explicit allocations retain one range, whole contracts and aggregate refusals."""
from __future__ import annotations

import contextlib
import hashlib
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

    def invoke(self, repo, *options, engine=None):
        argv = [str(SCRIPT), "--mode", "branch", "--base", "HEAD^", "--engine", "codex",
                "--max-priority", "P2", "--review-batches", ".review/batches.json",
                "--source-context-file", "global.md", "--max-prompt-bytes", "80000",
                "--max-review-passes", "2", "--json-output", str(repo.parent / "result.json"),
                *options]
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
            "resolve_engine_binary": lambda *_: (True, None),
        }), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                status = self.helper["main_with_args"](args)
            except SystemExit as exc:
                status = exc.code
            except self.helper["ReviewerUnavailable"] as exc:
                status = str(exc)
        return status, sends, output.getvalue()

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
