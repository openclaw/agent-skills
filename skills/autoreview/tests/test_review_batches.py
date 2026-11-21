"""Explicit allocations retain one range, whole contracts and aggregate refusals."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "autoreview"
fixture_git = runpy.run_path(str(SCRIPT.with_name("test-review-harness.py")))["fixture_git"]


class LosslessFramingTests(unittest.TestCase):
    def setUp(self):
        self.helper = runpy.run_path(str(SCRIPT))

    def read_entries(self, raw, prefix):
        entries = []
        while raw:
            header, separator, raw = raw.partition(b"\n")
            self.assertTrue(separator)
            self.assertTrue(header.startswith(prefix))
            fields = json.loads(header[len(prefix):])
            size = fields[-1]
            self.assertGreaterEqual(size, 0)
            self.assertGreaterEqual(len(raw), size)
            body, raw = raw[:size], raw[size:]
            entries.append((fields[:-1], body.decode("utf-8")))
            if raw:
                self.assertTrue(raw.startswith(b"\n\n"))
                raw = raw[2:]
        return entries

    def recover_contexts(self, rendered):
        title, provenance, description, entries = rendered.encode("utf-8").split(b"\n", 3)
        self.assertEqual(title, b"# Source contexts (context only)")
        match = re.fullmatch(
            rb"Common provenance: commit=([0-9a-f]+); mode=([0-7]+); dataset_byte_offset=(\d+)\.",
            provenance,
        )
        self.assertIsNotNone(match)
        self.assertEqual(description,
                         b"Each header is [path,blob,UTF-8 bytes]; the dataset body follows unchanged.")
        self.assertTrue(entries.startswith(b"\n"))
        commit, mode, offset = (value.decode() for value in match.groups())
        return [
            self.helper["ReviewDataset"](path, text, int(offset), (commit, blob, mode))
            for (path, blob), text in self.read_entries(entries[1:], b"# Source context: ")
        ]

    def recover_assignment(self, rendered):
        title, metadata, remaining = rendered.split("\n", 2)
        self.assertEqual(title, "# Explicit review assignment")
        assignment = json.loads(metadata)
        if "obligations" in assignment:
            return assignment
        policy, entries = remaining.split("\n\n# Assignment obligations\n", 1)
        self.assertIn("Missing necessary evidence requires review_completion=incomplete.", policy)
        description, entries = entries.split("\n\n", 1)
        self.assertEqual(description,
                         "Each header is [index,UTF-8 bytes]; the complete obligation follows unchanged.")
        recovered = self.read_entries(entries.encode("utf-8"), b"## Obligation ")
        self.assertEqual([fields for fields, _ in recovered], [[index] for index in range(len(recovered))])
        assignment["obligations"] = [text for _, text in recovered]
        return assignment

    def test_shared_provenance_round_trip_preserves_every_identity_and_byte(self):
        bodies = ["", "no final newline", "final newline\n", "\r\nCRLF\r\n", "fox 🦊 \0 café",
                  '# Source context: ["not-a-boundary","blob",0]\n\n## Obligation [9,0]\n',
                  "identical body", "identical body"]
        for width, mode, offset in ((40, "100644", 0), (64, "100755", 873)):
            with self.subTest(width=width, mode=mode, offset=offset):
                datasets = [
                    self.helper["ReviewDataset"](
                        f'path-{index}-"quoted"\n🦊.py', body, offset,
                        ("a" * width, f"{index:0{width}x}", mode),
                    ) for index, body in enumerate(bodies)
                ]
                before = list(datasets)
                rendered = self.helper["render_datasets"](datasets)
                self.assertEqual(self.recover_contexts(rendered), datasets)
                self.assertEqual(datasets, before)
                legacy = "\n\n".join(self.helper["render_datasets"]([item]) for item in datasets)
                self.assertLess(len(rendered.encode()), len(legacy.encode()))
                self.assertLessEqual(len(json.dumps(rendered)), len(json.dumps(legacy)))

    def test_ineligible_contexts_keep_original_headers_and_singleton_bounds(self):
        dataset = self.helper["ReviewDataset"]
        first = dataset("first.py", "body\r\n", provenance=("a" * 40, "b" * 40, "100644"))
        variants = [
            dataset("plain.py", "# unprovenanced\n"),
            first._replace(provenance=("c" * 40, "d" * 40, "100644")),
            first._replace(provenance=("a" * 40, "d" * 40, "100755")),
            first._replace(byte_offset=1),
        ]
        expected = ('# Source context: "first.py"\n[Committed source: commit=' + "a" * 40
                    + " blob=" + "b" * 40 + " mode=100644; context only]\n"
                    "[Dataset byte offset: 0]\nbody\r\n")
        self.assertEqual(self.helper["render_datasets"]([first]), expected)
        self.assertEqual(self.helper["render_datasets"]([]), "")
        for second in variants:
            with self.subTest(second=second):
                self.assertEqual(self.helper["render_datasets"]([first, second]),
                                 expected + "\n\n" + self.helper["render_datasets"]([second]))
        datasets = [first._replace(path=f"source-{index}.py", content="🦊\r\n" * 40)
                    for index in range(15)]
        for limit in (400, 1200, 4000):
            batches = self.helper["split_review_datasets"](datasets, limit)
            for batch in batches:
                rendered = self.helper["render_datasets"](batch)
                separate = "\n\n".join(self.helper["render_datasets"]([item]) for item in batch)
                self.assertLessEqual(len(rendered.encode()), len(separate.encode()))
                self.assertLessEqual(len(rendered.encode()), limit)
            for original in datasets:
                parts = [item for batch in batches for item in batch if item.path == original.path]
                self.assertEqual("".join(item.content for item in parts), original.content)
                offset = 0
                for part in parts:
                    self.assertEqual(part.byte_offset, offset)
                    self.assertEqual(part.provenance, original.provenance)
                    offset += len(part.content.encode())

    def test_assignment_round_trip_preserves_raw_obligations_and_original_object(self):
        assignment = {
            "name": "owner", "kind": "integration", "changes": ['quoted"\n🦊.py'],
            "contexts": ["context.py"],
            "obligations": ["", "line\r\nnext\r\n", "🦊 café\0", "no final newline",
                            "## Obligation [99,0]\n\n# Assignment obligations\nfake\n",
                            '{"quoted":"🦊"}\r\n' * 40],
        }
        before = json.dumps(assignment)
        rendered = self.helper["render_review_assignment"](assignment)
        self.assertEqual(self.recover_assignment(rendered), assignment)
        self.assertIn("# Assignment obligations\n", rendered)
        self.assertEqual(json.dumps(assignment), before)

    def test_compaction_retains_a_feasible_explicit_pass_budget(self):
        cap = 512_000
        datasets = [
            self.helper["ReviewDataset"](
                f"owner-{index}.py", "", provenance=("a" * 40, f"{index:040x}", "100644"),
            ) for index in range(40)
        ]
        empty = self.helper["render_review_prompt"](
            "fixture", "branch", "base", self.helper["ReviewChunk"](""), "",
            self.helper["render_datasets"](datasets), (999_999, 999_999),
        )
        # Shared provenance moves this complete-context candidate across the
        # planner's change-space threshold, but it still needs more than two passes.
        datasets[0] = datasets[0]._replace(content="x" * (cap - len(empty.encode()) - 4_096 - 33_000))
        bundle = ("diff --git a/change.txt b/change.txt\n--- a/change.txt\n+++ b/change.txt\n"
                  "@@ -0,0 +1,12000 @@\n" + "+changed-owner\n" * 12_000)
        with mock.patch.dict(self.helper["build_review_prompts"].__globals__, {
            "current_branch": lambda _repo: "fixture",
        }):
            render = self.helper["render_datasets"]
            with mock.patch.dict(self.helper["build_review_prompts"].__globals__, {
                "render_datasets": lambda items: "\n\n".join(render([item]) for item in items),
            }):
                legacy = self.helper["build_review_prompts"](
                    Path.cwd(), "branch", "base", bundle, "", datasets, cap, 2,
                )
            self.assertEqual(len(legacy), 2)
            prompts = self.helper["build_review_prompts"](
                Path.cwd(), "branch", "base", bundle, "", datasets, cap, 2,
            )
            for limit in (None, 6):
                preferred = self.helper["build_review_prompts"](
                    Path.cwd(), "branch", "base", bundle, "", datasets, cap, limit,
                )
                self.assertEqual(len(preferred), 6)
            rejected = self.helper["build_review_prompts"](
                Path.cwd(), "branch", "base", bundle, "", datasets, cap, 1,
            )
            with self.assertRaisesRegex(SystemExit, "--max-review-passes allows 1"):
                self.helper["check_review_pass_budget"](1, len(rejected))
        self.assertEqual(len(prompts), 2)
        for prompt in prompts:
            self.assertLessEqual(len(prompt.encode()), cap)
            self.assertEqual(prompt.rsplit("\n\n# Change Bundle\n", 1)[1], bundle)
        for item in datasets:
            self.assertTrue(any(item.path in prompt and item.provenance[1] in prompt for prompt in prompts))
        self.assertEqual("".join(part for prompt in prompts for part in re.findall(r"x{100,}", prompt)),
                         datasets[0].content)
        for item in datasets[1:]:
            self.assertEqual(sum(prompt.count(json.dumps(item.path)) for prompt in prompts), 1)

    def test_assignment_keeps_a_fitting_native_request_with_escaped_unicode(self):
        assignment = {"name": "owner", "kind": "owner", "changes": ["a.py"],
                      "contexts": [], "obligations": ["雪" * 40]}
        render = self.helper["render_review_assignment"]
        title, _metadata, rest = render(assignment).split("\n", 2)
        policy = rest.split("\n\n# Assignment obligations\n", 1)[0]

        def legacy():
            return title + "\n" + json.dumps(assignment, ensure_ascii=True) + "\n" + policy

        def prompt(text):
            return self.helper["render_review_prompt"](
                "fixture", "branch", "base", self.helper["ReviewChunk"]("+x\n"), text, "",
            )

        # Exercise the unchanged wire encoder at its actual limit, without
        # creating a handoff directory or launching a reviewer.
        handoff = object.__new__(self.helper["NativeHandoff"])
        handoff.run_id, handoff.pass_count = "0" * 32, 1
        handoff.model, handoff.thinking, handoff.timeout = "fixture/reviewer", "high", None
        initial = prompt(legacy())
        encoded, _ = handoff.encode_request(1, initial)
        padding = handoff.MAX_REQUEST_BYTES - len(encoded.encode())
        padding -= len(str(len(initial.encode()) + padding)) - len(str(len(initial.encode())))
        assignment["obligations"][0] = "x" * padding + assignment["obligations"][0]
        expected = prompt(legacy())
        actual = prompt(render(assignment))
        encoded, _ = handoff.encode_request(1, expected)
        self.assertEqual(len(encoded.encode()), handoff.MAX_REQUEST_BYTES)
        self.assertTrue(actual == expected, "the fitting native request must retain legacy framing")
        self.assertEqual(self.recover_assignment(render(assignment)), assignment)
        handoff.encode_request(1, actual)
        with self.assertRaisesRegex(SystemExit, "exceeds 4000000 bytes"):
            handoff.encode_request(1, actual + "x")

    def test_fallback_prefers_a_complete_plan_within_the_requested_pass_count(self):
        datasets = []
        for index, size in enumerate((39_000, 16_000, 22_000)):
            item = self.helper["ReviewDataset"](f"evidence-{index}", "")
            overhead = len(self.helper["render_datasets"]([item]).encode())
            datasets.append(item._replace(content=chr(65 + index) * (size - overhead)))
        empty = self.helper["render_review_prompt"](
            "fixture", "branch", "base", self.helper["ReviewChunk"](""), "", "",
            (999_999, 999_999),
        )
        cap = 100_000 + len(empty.encode()) + 4_096
        bundle = "+x\n" * (309_400 // 3) + "x" * (309_400 % 3)
        with mock.patch.dict(self.helper["build_review_prompts"].__globals__, {
            "current_branch": lambda _repo: "fixture",
        }):
            unlimited = self.helper["build_review_prompts"](
                Path.cwd(), "branch", "base", bundle, "", datasets, cap,
            )
            limited = self.helper["build_review_prompts"](
                Path.cwd(), "branch", "base", bundle, "", datasets, cap, 11,
            )
            impossible = self.helper["build_review_prompts"](
                Path.cwd(), "branch", "base", bundle, "", datasets, cap, 1,
            )
        self.assertEqual(len(unlimited), 14)
        self.assertEqual(len(limited), 11)
        self.helper["check_review_pass_budget"](11, len(limited))
        with self.assertRaisesRegex(SystemExit, "--max-review-passes allows 1"):
            self.helper["check_review_pass_budget"](1, len(impossible))
        batches, fragments = {}, {item.path: {} for item in datasets}
        for prompt in limited:
            self.assertLessEqual(len(prompt.encode()), cap)
            context, change = prompt.rsplit("\n\n# Change Bundle\n", 1)
            batch = re.search(r"Evidence batch: (\d+)/(\d+)", context).group(1)
            batches.setdefault(batch, []).append(change)
            for path, offset, text in re.findall(
                r"# Dataset: (evidence-\d+)\n\[Dataset byte offset: (\d+)\]\n([ABC]+)",
                context,
            ):
                prior = fragments[path].setdefault(int(offset), text)
                self.assertEqual(prior, text)
        self.assertTrue(batches)
        for changes in batches.values():
            self.assertEqual("".join(changes), bundle)
        for item in datasets:
            offset = 0
            for start, text in sorted(fragments[item.path].items()):
                self.assertEqual(start, offset)
                offset += len(text.encode())
            self.assertEqual("".join(text for _, text in sorted(fragments[item.path].items())),
                             item.content)

    def test_prompt_pipes_deliver_exact_bytes_without_changing_output_decoding(self):
        prompt = 'first\nCRLF\r\nbare\rfox 🦊\n## Obligation [0,0]\nno final newline'
        real_popen = subprocess.Popen
        for route in ("run", "heartbeat", "stream", "authentication"):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                children = []

                def crlf_pipe(*args, **kwargs):
                    proc = real_popen(*args, **kwargs)
                    if args[0] == command:
                        children.append(proc)
                        # Exercise real TextIOWrapper translation on every host;
                        # this is portable transport proof, not native Windows proof.
                        proc.stdin.reconfigure(newline="\r\n")
                    return proc

                command = [sys.executable, "-c",
                           "import sys; print(sys.stdin.buffer.read().hex()); "
                           "sys.stderr.buffer.write(b'output\\x90\\r\\n'); sys.exit(7)"]
                with mock.patch.object(subprocess, "Popen", side_effect=crlf_pipe):
                    if route == "run":
                        result = self.helper["run"](
                            command, Path(directory), input_text=prompt, check=False,
                        )
                    else:
                        result = self.helper["run_with_heartbeat"](
                            command, Path(directory), input_text=prompt, label="prompt-bytes",
                            heartbeat_seconds=1, max_runtime_seconds=10,
                            stream_output=route == "stream", stream_display=lambda *_: None,
                            stop_on_output=(lambda *_: False) if route == "authentication" else None,
                        )
                self.assertEqual(result.returncode, 7)
                self.assertEqual(bytes.fromhex(result.stdout.strip()), prompt.encode("utf-8"))
                self.assertEqual(result.stderr, "output\ufffd\n")
                self.assertEqual(len(children), 1)
                for proc in children:
                    self.assertIsNotNone(proc.returncode)
                    self.assertTrue(all(stream.closed for stream in (proc.stdin, proc.stdout, proc.stderr)))
                    self.assertNotIn(proc.pid, self.helper["_OWNED_PROCESSES"])

    def test_run_retains_capture_binary_input_and_error_contracts(self):
        payload = b"binary\x00\xff\r\nnext\n"
        command = [sys.executable, "-c",
                   "import sys; print(sys.stdin.buffer.read().hex()); "
                   "sys.stderr.buffer.write(b'failure\\x90\\r\\n'); sys.exit(7)"]
        for capture in (False, True):
            with self.subTest(capture=capture), tempfile.TemporaryDirectory() as directory, \
                    tempfile.TemporaryFile() as source:
                source.write(payload)
                source.seek(0)
                root = Path(directory)
                result = self.helper["run"](
                    command, root, stdin=source, check=False, capture_dir=root if capture else None,
                )
                self.assertEqual(result.returncode, 7)
                self.assertEqual(result.stdout, payload.hex() + "\n")
                self.assertEqual(result.stderr, "failure\ufffd\n")
                self.assertFalse(source.closed)
                self.assertEqual(source.tell(), len(payload))
                with self.assertRaisesRegex(ValueError, "stdin and input"):
                    self.helper["run"](command, root, stdin=source, input_text="")
                with self.assertRaises(SystemExit) as error:
                    self.helper["run"](command, root, input_text="text", capture_dir=root if capture else None)
                self.assertIn("command failed (7)", str(error.exception))
                self.assertIn("failure\ufffd", str(error.exception))

    def test_input_configuration_failure_keeps_process_cleanup(self):
        for route in ("run", "heartbeat", "stream"):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                failure = OSError("input configuration failed")
                children = []

                def fail(proc):
                    children.append(proc)
                    raise failure

                command = [sys.executable, "-c", "import time; time.sleep(30)"]
                with mock.patch.dict(self.helper["run"].__globals__, {"preserve_prompt_input": fail}), \
                        self.assertRaises(OSError) as error:
                    if route == "run":
                        self.helper["run"](command, Path(directory), input_text="prompt")
                    else:
                        self.helper["run_with_heartbeat"](
                            command, Path(directory), input_text="prompt", label="input-failure",
                            stream_output=route == "stream",
                        )
                self.assertIs(error.exception, failure)
                self.assertEqual(len(children), 1)
                proc = children[0]
                self.assertIsNotNone(proc.returncode)
                self.assertTrue(all(stream.closed for stream in (proc.stdin, proc.stdout, proc.stderr)))
                self.assertNotIn(proc.pid, self.helper["_OWNED_PROCESSES"])


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

    def test_rfc_contract_change_reaches_allocated_review_whole(self):
        for root in ("specs/rfcs", "docs/rfcs"):
            with self.subTest(root=root), self.fixture() as repo:
                rel = f"{root}/0042-credential-lifecycle/contracts.md"
                path = repo / rel
                path.parent.mkdir(parents=True)
                body = "# Service admission\n\nOnly the selected service may request this operation.\n"
                path.write_bytes(body.encode("utf-8"))
                self.git(repo, "add", rel)
                self.git(repo, "commit", "--amend", "--no-edit", "-q")
                manifest = self.manifest(repo)
                blob = self.git(repo, "rev-parse", "HEAD:" + rel)
                manifest["contexts"].append({"path": rel, "blob": blob, "mode": "100644"})
                for batch in manifest["batches"]:
                    batch["changes"].append(rel)
                    batch["contexts"].append(rel)
                self.write_manifest(repo, manifest)
                status, sends, output = self.invoke(repo)
                self.assertEqual(status, 0, output)
                self.assertEqual(len(sends), 2)
                for prompt in sends:
                    self.assertIn(rel, prompt)
                    self.assertEqual(prompt.count(body), 1)
                    self.assertIn("# Source context: " + json.dumps(
                        [rel, blob, len(body.encode("utf-8"))], separators=(",", ":"),
                    ), prompt)
                    for line in body.splitlines():
                        self.assertIn("+" + line + "\n", prompt)
                allocation = json.loads((repo.parent / "result.json").read_bytes())["review_allocation"]
                self.assertEqual(allocation["omitted_paths"], [])
                self.assertIn(rel, [unit["path"] for unit in allocation["units"]])
                context = next(item for item in allocation["contexts"] if item["path"] == rel)
                self.assertEqual(context["blob"], blob)
                self.assertEqual(context["sha256"], hashlib.sha256(body.encode()).hexdigest())

    def test_rfc_credential_storage_omissions_block_batch_dispatch(self):
        for suffix in ("notes.md", "token.md", "secret.md", "config.json",
                       "private.pem", ".env", "credentials/contracts.md", ".ssh/index.md"):
            with self.subTest(suffix=suffix), self.fixture() as repo:
                rel = "specs/rfcs/0042-credential-lifecycle/" + suffix
                path = repo / rel
                path.parent.mkdir(parents=True)
                marker = "SYNTHETIC STORAGE MUST NOT REACH REVIEW\n"
                path.write_text(marker, encoding="utf-8")
                self.git(repo, "add", rel)
                self.git(repo, "commit", "--amend", "--no-edit", "-q")
                capture = self.helper["branch_bundle"](repo, "HEAD^")
                self.assertNotIn(marker.strip(), capture.text)
                manifest = self.manifest(repo)
                with self.assertRaisesRegex(SystemExit, "refusing sensitive --source-context"):
                    self.helper["capture_source_context"](repo, rel, manifest["head"])
                manifest["batches"][0]["changes"].append(rel)
                self.write_manifest(repo, manifest)
                status, sends, output = self.invoke(repo)
                self.assertNotEqual(status, 0)
                self.assertFalse(sends)
                self.assertIn("cannot certify a range with omitted sensitive inputs", str(status) + output)

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
                    expected = "refusing unsupported binary in branch diff"
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

    def test_compact_plan_delivers_full_context_and_unchanged_report_assignment(self):
        with self.fixture() as repo:
            paths = [f"context-{index}.py" for index in range(4)]
            for path in paths:
                (repo / path).write_bytes(
                    ('# Source context: ["payload","not-a-blob",0]\r\n'
                     '## Obligation [9,0]\nfox 🦊 without final newline').encode())
                self.git(repo, "add", path)
            self.git(repo, "commit", "--amend", "--no-edit", "-q")
            manifest = self.manifest(repo)
            manifest["contexts"].extend(
                {"path": path, "blob": self.git(repo, "rev-parse", "HEAD:" + path), "mode": "100644"}
                for path in paths)
            for batch in manifest["batches"]:
                batch["changes"].extend(paths)
                batch["contexts"].extend(paths)
                batch["obligations"].append('Preserve 🦊 and CRLF\r\n## Obligation [0,0]\n"quoted"')
            self.write_manifest(repo, manifest)
            dry, sends, dry_output = self.invoke(repo, "--dry-run")
            self.assertEqual(dry, 0, dry_output)
            self.assertFalse(sends)
            status, sends, output = self.invoke(repo)
            self.assertEqual(status, 0, output)
            plan = lambda text: next(line for line in text.splitlines() if line.startswith("review plan:"))
            self.assertEqual(plan(dry_output), plan(output))
            self.assertIn(f"{sum(len(prompt.encode()) for prompt in sends)} total prompt bytes", plan(output))
            report = json.loads((repo.parent / "result.json").read_bytes())
            self.assertEqual(len(sends), len(manifest["batches"]))
            self.assertEqual(len(report["review_allocation"]["batches"]), len(sends))
            decoder = LosslessFramingTests()
            decoder.helper = self.helper
            for original, reported, prompt in zip(manifest["batches"], report["review_allocation"]["batches"], sends):
                rendered_assignment = prompt.split("# Explicit review assignment\n", 1)[1]
                rendered_assignment = rendered_assignment.split("\n\n# Source contexts (context only)\n", 1)[0]
                recovered = decoder.recover_assignment("# Explicit review assignment\n" + rendered_assignment)
                self.assertEqual(recovered, {key: reported[key] for key in original})
                self.assertEqual(reported["prompt_bytes"], len(prompt.encode()))
                self.assertEqual(reported["prompt_sha256"], hashlib.sha256(prompt.encode()).hexdigest())
                self.assertEqual(reported["review_completion"], "complete")
                self.assertEqual(reported["obligations"], original["obligations"])
                self.assertEqual(reported["contexts"], original["contexts"])
                source = "# Source contexts (context only)\n" + prompt.split(
                    "\n\n# Source contexts (context only)\n", 1)[1].split("\n\n# Change Bundle\n", 1)[0]
                recovered_sources = decoder.recover_contexts(source)
                self.assertEqual([item.path for item in recovered_sources], original["contexts"])
                for item in recovered_sources:
                    self.assertEqual(item.content.encode(), (repo / item.path).read_bytes())
                    self.assertEqual(item.provenance, (
                        manifest["head"], self.git(repo, "rev-parse", "HEAD:" + item.path), "100644"))

    def test_manifest_surrogate_escapes_retain_legacy_assignment_and_reports(self):
        with self.fixture() as repo:
            manifest = self.manifest(repo)
            manifest["batches"][0]["obligations"] = ["high \ud800", "low \udfff"]
            # Escaping-heavy valid pairs profit from raw framing; lone surrogates cannot.
            manifest["batches"][1]["obligations"] = ["valid pair 🦊\r\nunchanged\n" * 40]
            self.write_manifest(repo, manifest)
            raw = (repo / ".review/batches.json").read_bytes()
            self.assertIn(b"\\ud800", raw)
            self.assertIn(b"\\udfff", raw)
            self.assertIn(b"\\ud83e\\udd8a", raw)
            dry, sends, dry_output = self.invoke(repo, "--dry-run")
            self.assertEqual(dry, 0, dry_output)
            self.assertFalse(sends)
            status, sends, output = self.invoke(repo)
            self.assertEqual(status, 0, output)
            self.assertEqual(len(sends), 2)
            plan = lambda text: next(line for line in text.splitlines() if line.startswith("review plan:"))
            self.assertEqual(plan(dry_output), plan(output))
            self.assertNotIn("# Assignment obligations\n", sends[0])
            self.assertIn(json.dumps(manifest["batches"][0], ensure_ascii=True), sends[0])
            self.assertIn("## Obligation [0,", sends[1])
            self.assertIn(manifest["batches"][1]["obligations"][0], sends[1])
            report = json.loads((repo.parent / "result.json").read_bytes())
            self.assertEqual(len(report["review_allocation"]["batches"]), 2)
            for original, actual in zip(manifest["batches"], report["review_allocation"]["batches"]):
                self.assertEqual(actual["obligations"], original["obligations"])

    def test_small_assignment_keeps_legacy_fit_and_exact_budget_boundary(self):
        with self.fixture() as repo:
            self.write_manifest(repo, self.manifest(repo))
            render = self.helper["render_review_assignment"]

            def legacy_assignment(assignment):
                title, _metadata, rest = render(assignment).split("\n", 2)
                policy = rest.split("\n\n# Assignment obligations\n", 1)[0]
                return title + "\n" + json.dumps(assignment, ensure_ascii=True) + "\n" + policy

            with mock.patch.dict(render.__globals__, {"render_review_assignment": legacy_assignment}):
                status, sends, output = self.invoke(repo)
            self.assertEqual(status, 0, output)
            limit = max(len(prompt.encode()) for prompt in sends)
            for options in ((), ("--dry-run",)):
                status, actual, output = self.invoke(repo, "--max-prompt-bytes", str(limit), *options)
                self.assertEqual(status, 0, output)
                if not options:
                    self.assertEqual(actual, sends)
                status, actual, _ = self.invoke(repo, "--max-prompt-bytes", str(limit - 1), *options)
                self.assertNotEqual(status, 0)
                self.assertFalse(actual)

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
