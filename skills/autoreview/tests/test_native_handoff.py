"""Exercise real helper capture, raw completion submission and lifecycle boundaries."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "autoreview"
CLEAN = {"findings": [], "overall_correctness": "patch is correct",
         "overall_explanation": "Complete review of the supplied pass.",
         "overall_confidence": 0.9, "review_completion": "complete"}
FINDING = {"title": "[P2] Restore free shipping at the threshold",
           "body": "An order of exactly 100 now pays shipping despite the inclusive threshold.",
           "priority": "P2", "confidence": 0.99, "category": "regression",
           "code_location": {"file_path": "shipping.py", "line": 1}, "source_attribution": None}


class ReviewFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="autoreview-native-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("AUTOREVIEW_", "CODEX_", "GIT_"))}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        self.git("init", "-q")
        (self.repo / "shipping.py").write_text("def shipping(total): return 0 if total >= 100 else 5\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        (self.repo / "shipping.py").write_text("def shipping(total): return 0 if total > 100 else 5\n")
        self.git("commit", "-qam", "candidate")
        self.handoff = self.root / "handoff"
        self.report = self.root / "report.json"
        self.status = self.root / "status.json"
        self.process = None
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=5)
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, env=self.env, text=True)


@unittest.skipUnless(os.name == "posix", "native handoff uses POSIX custody")
class NativeHandoffTests(ReviewFixture):
    def start(self, *options, timeout="8"):
        self.process = subprocess.Popen([
            sys.executable, str(SCRIPT), "--mode", "branch", "--base", self.base,
            "--engine", "openclaw", "--native-handoff", str(self.handoff),
            *(["--engine-timeout-seconds", timeout] if timeout else []), "--json-output", str(self.report),
            "--status-output", str(self.status), *options],
            cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(self.process)
        return self.process

    def request(self, number=1):
        path = self.handoff / f"{number}.request.json"
        deadline = time.monotonic() + 6
        while not path.exists() and self.process.poll() is None and time.monotonic() < deadline:
            time.sleep(.01)
        if not path.exists():
            out, err = self.process.communicate(timeout=3)
            self.fail(f"no request {number}, exit {self.process.returncode}: {out}\n{err}")
        result = json.loads(path.read_text())
        self.assertEqual(result["protocol"], "autoreview-exec-v1")
        self.assertNotIn("output_schema", result)
        self.assertEqual(result["prompt_bytes"], len(result["prompt"].encode()))
        self.assertEqual(result["prompt_sha256"], hashlib.sha256(result["prompt"].encode()).hexdigest())
        self.assertEqual(self.handoff.stat().st_mode & 0o777, 0o700)
        return result

    def deliver(self, request, report=None, *, modify=None, raw=None, commit=True):
        response = {"run_id": request["run_id"], "pass": request["pass"],
                    "prompt_sha256": request["prompt_sha256"], "status": "done",
                    "output": self.completion(request, CLEAN if report is None else report)}
        if modify:
            modify(response)
        data = json.dumps(response).encode() if raw is None else raw
        (self.handoff / f'{request["pass"]}.result.json').write_bytes(data)
        if commit:
            (self.handoff / f'{request["pass"]}.ready').write_text(json.dumps({
                "run_id": request["run_id"], "pass": request["pass"], "bytes": len(data)}))

    def finish(self, code):
        out, err = self.process.communicate(timeout=10)
        self.assertEqual(self.process.returncode, code, out + "\n" + err)
        self.assertFalse(self.handoff.exists(), "helper did not clean its exchange")
        return out + err

    @staticmethod
    def completion(request, report):
        model = request["model"] or "fixture/reviewer"
        provider, _, model_id = model.partition("/")
        return json.dumps({"ok": True, "status": "ok", "final": json.dumps(report),
                           "model": model_id or model, "provider": provider})

    def consumer(self, request, report=CLEAN, *, failure=False, delay=0):
        # Simulate only the remote execution boundary; invoke the real submit
        # command and preserve its complete bytes and one-shot commit custody.
        if delay:
            time.sleep(delay / 1000)
        response = {"run_id": request["run_id"], "pass": request["pass"],
                    "prompt_sha256": request["prompt_sha256"],
                    "status": "failed" if failure else "done",
                    "output": None if failure else self.completion(request, report)}
        spool = self.root / f"handoff.{request['run_id']}.{request['pass']}.response.json"
        spool.write_text(json.dumps(response))
        return subprocess.run([sys.executable, str(SCRIPT), "--native-submit",
                               str(self.handoff), str(spool)],
                              cwd=self.repo, env=self.env, text=True, capture_output=True, timeout=15)

    def test_complete_raw_output_and_explicit_model(self):
        self.start("--model", "openai/gpt-6-astra", "--thinking", "high")
        request = self.request()
        self.assertEqual(request["model"], "openai/gpt-6-astra")
        self.assertEqual(self.consumer(request).returncode, 0)
        self.finish(0)
        self.assertEqual(json.loads(self.report.read_text())["review_status"], "scoped-clean")

    def test_request_carries_canonical_options_without_host_configuration(self):
        self.env.update(AUTOREVIEW_OPENCLAW_MODEL="fixture/configured",
                        AUTOREVIEW_OPENCLAW_THINKING="low")
        self.start("--thinking", "high", timeout=None)
        request = self.request()
        self.assertEqual(request["model"], "fixture/configured")
        self.assertEqual(request["thinking"], "high")
        self.assertIsNone(request["engine_timeout_seconds"])
        self.assertIs(request["admitted_model"], True)
        self.assertNotIn("config_override", request)
        self.assertNotIn("agent_override", request)
        self.assertEqual(self.consumer(request).returncode, 0)
        self.finish(0)

    def test_explicit_budget_preserves_native_request_limit(self):
        context = self.repo / "context.txt"
        for count, accepted in ((275_000, True), (350_000, False)):
            with self.subTest(accepted=accepted):
                self.report.unlink(missing_ok=True)
                content = "😀" * count
                context.write_text(content, encoding="utf-8")
                self.start("--prompt-file", "context.txt", "--max-prompt-bytes", "1500000")
                if accepted:
                    request = self.request()
                    self.assertIn(content, request["prompt"])
                    self.assertGreater(request["prompt_bytes"], 1_000_000)
                    self.assertLessEqual((self.handoff / "1.request.json").stat().st_size, 4_000_000)
                    result = self.consumer(request)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.finish(0)
                else:
                    output = self.finish(1)
                    self.assertIn("native handoff request 1/1 exceeds 4000000 bytes", output)
                    self.assertNotIn("native pass ready", output)
                    self.assertFalse(self.report.exists())

    def test_later_oversized_request_refuses_before_exchange_creation(self):
        helper = runpy.run_path(str(SCRIPT))
        args = argparse.Namespace(native_handoff=str(self.handoff), engine_timeout_seconds=8)
        reviewer = argparse.Namespace(model="fixture/reviewer", thinking="high", openclaw_models=[])
        oversized = "😀" * 350_000
        for prompt in (oversized, helper["ReviewPass"](oversized, helper["ReviewChunk"](""))):
            with self.subTest(prompt=type(prompt).__name__):
                handoff = None
                try:
                    with self.assertRaisesRegex(SystemExit, "native handoff request 2/2 exceeds 4000000 bytes"):
                        handoff = helper["NativeHandoff"](args, reviewer, ["first pass", prompt])
                finally:
                    if handoff is not None:
                        handoff.close()
                self.assertFalse(self.handoff.exists())

    def test_encoded_request_boundary_includes_envelope_and_escaping(self):
        helper = runpy.run_path(str(SCRIPT))
        args = argparse.Namespace(native_handoff=str(self.handoff), engine_timeout_seconds=8)
        reviewer = argparse.Namespace(model="fixture/reviewer", thinking="high", openclaw_models=[])
        handoff = helper["NativeHandoff"](args, reviewer, ["small"])
        try:
            prompt = '😀\\"\n'
            encoded, digest = handoff.encode_request(1, prompt)
            size = len(encoded.encode("utf-8"))
            self.assertGreater(size, len(prompt.encode("utf-8")))
            self.assertEqual(json.loads(encoded)["prompt"], prompt)
            self.assertEqual(digest, hashlib.sha256(prompt.encode()).hexdigest())
            with mock.patch.object(type(handoff), "MAX_REQUEST_BYTES", size):
                self.assertEqual(handoff.encode_request(1, prompt), (encoded, digest))
            with mock.patch.object(type(handoff), "MAX_REQUEST_BYTES", size - 1):
                with self.assertRaisesRegex(SystemExit, "native handoff request 1/1 exceeds"):
                    handoff.encode_request(1, prompt)
        finally:
            handoff.close()

    def test_admitted_model_is_validated_and_reported_without_a_default_timeout(self):
        for actual in ("fixture/permitted", "fixture/unselected"):
            with self.subTest(actual=actual):
                self.report.unlink(missing_ok=True)
                self.start("--model", "fixture/configured", timeout=None)
                request = self.request()
                self.deliver(request, modify=lambda response: response.update(
                    model="fixture/permitted",
                    output=self.completion(request | {"model": actual}, CLEAN)))
                output = self.finish(0 if actual == "fixture/permitted" else 1)
                if actual == "fixture/permitted":
                    self.assertIn("effective model: fixture/permitted", output)
                    self.assertEqual(json.loads(self.report.read_text())["review_status"], "scoped-clean")
                    self.assertEqual(json.loads(self.status.read_text())["effective_models"], ["fixture/permitted"])
                else:
                    self.assertFalse(self.report.exists())
                    self.assertNotIn("effective_models", json.loads(self.status.read_text()))

    def test_real_finding_and_priority_filter_preserved(self):
        for threshold, code, status in (("P2", 1, "findings"), ("P0", 1, "filtered")):
            with self.subTest(threshold=threshold):
                self.start("--max-priority", threshold)
                report = copy.deepcopy(CLEAN)
                report.update(findings=[FINDING], overall_correctness="patch is incorrect")
                self.consumer(self.request(), report)
                self.finish(code)
                self.assertEqual(json.loads(self.report.read_text())["review_status"], status)

    def test_multipass_consumes_full_near_limit_inputs(self):
        (self.repo / "large.txt").write_text("".join(f"row {n}: retained evidence 😀 " + "x" * 90 + "\n" for n in range(6500)))
        self.git("add", ".")
        self.git("commit", "-qm", "large candidate")
        self.start(timeout="15")
        first = self.request()
        self.assertGreater(first["passes"], 1)
        self.assertGreater(first["prompt_bytes"], 490_000)
        for number in range(1, first["passes"] + 1):
            req = first if number == 1 else self.request(number)
            self.assertLessEqual(req["prompt_bytes"], 512_000)
            self.assertEqual(self.consumer(req).returncode, 0)
        self.finish(0)
        report = json.loads(self.report.read_text())
        self.assertEqual(len(report["pass_reports"]), first["passes"])
        self.assertEqual(report["review_status"], "scoped-clean")
        self.assertEqual(json.loads(self.status.read_text())["effective_models"], ["fixture/reviewer"])

    def test_response_larger_than_exec_output_budget_stays_complete(self):
        report = copy.deepcopy(CLEAN)
        report.update(overall_correctness="patch is incorrect", findings=[
            FINDING | {"title": f"[P2] Complete finding {number}",
                       "body": "é🙂\\\"\n" * 250} for number in range(150)])
        self.start("--max-priority", "P2", timeout="15")
        result = self.consumer(self.request(), report)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.finish(1)
        validated = json.loads(self.report.read_text())
        self.assertEqual(len(validated["findings"]), 150)
        self.assertEqual(validated["findings"][-1]["body"], report["findings"][-1]["body"])

    def test_source_change_prevents_publication(self):
        self.start()
        req = self.request()
        (self.repo / "shipping.py").write_text("changed while reviewing\n")
        self.deliver(req)
        self.assertIn("source changed", self.finish(1))
        self.assertFalse(self.report.exists())
        self.assertFalse(self.status.exists())

    def test_invalid_missing_incomplete_and_terminal_failure(self):
        cases = [
            ("malformed", {"raw": b'{"truncated":'}, 1),
            ("wrong run", {"modify": lambda x: x.update(run_id="stale")}, 1),
            ("wrong pass", {"modify": lambda x: x.update(pass_number=2)}, 1),
            ("wrong input", {"modify": lambda x: x.update(prompt_sha256="0" * 64)}, 1),
            ("invalid schema", {"report": {"review_completion": "complete"}}, 1),
            ("missing completion", {"report": {k: v for k, v in CLEAN.items() if k != "review_completion"}}, 1),
            ("incomplete", {"report": CLEAN | {"review_completion": "incomplete"}}, 2),
            ("failed after report", {"modify": lambda x: x.update(status="failed")}, 1),
            ("over limit", {"raw": b" " * 2_000_001}, 1),
            ("truncated stdout", {"modify": lambda x: x.update(output='{"ok":true')}, 1),
            ("failed envelope", {"modify": lambda x: x.update(output=json.dumps({"ok": False, "status": "error", "final": json.dumps(CLEAN)}))}, 1),
            ("earlier valid payload", {"modify": lambda x: x.update(output=json.dumps({"ok": True, "status": "ok", "final": "", "payloads": [{"text": json.dumps(CLEAN)}]}))}, 1),
        ]
        for name, kwargs, code in cases:
            with self.subTest(name=name):
                self.report.unlink(missing_ok=True)
                self.start()
                self.deliver(self.request(), **kwargs)
                self.finish(code)
                state = json.loads(self.status.read_text())
                self.assertEqual(state["status"], "incomplete" if code == 2 else "reviewer_unavailable")
                self.assertEqual(self.report.exists(), code == 2)

    def test_uncommitted_response_and_missing_response_timeout(self):
        for response in (False, True):
            with self.subTest(uncommitted=response):
                self.start(timeout=".3")
                req = self.request()
                if response:
                    self.deliver(req, commit=False)
                self.finish(1)
                state = json.loads(self.status.read_text())
                self.assertTrue(state["timed_out"])
                self.assertFalse(state["report_produced"])
                self.assertFalse(self.report.exists())

    def test_consumer_terminal_failure_is_not_retried(self):
        self.start()
        self.assertEqual(self.consumer(self.request(), failure=True).returncode, 0)
        self.finish(1)
        self.assertFalse(self.report.exists())

    def test_late_collector_cannot_recreate_retired_exchange(self):
        self.start(timeout=".3")
        result = self.consumer(self.request(), delay=800)
        self.assertEqual(result.returncode, 1)
        self.finish(1)
        self.assertTrue(json.loads(self.status.read_text())["timed_out"])
        self.assertFalse(self.report.exists())
        self.assertEqual(list(self.root.glob("*.response.json")), [])

    def test_output_descendant_aliases_are_rejected_before_review(self):
        import argparse
        import runpy
        helper = runpy.run_path(str(SCRIPT))
        for exchange, output in (("handoff", "HANDOFF"), ("r\u00e9view", "re\u0301view")):
            with self.subTest(exchange=exchange):
                args = argparse.Namespace(native_handoff=str(self.root / exchange),
                    json_output=str(self.root / output / "report.json"))
                with self.assertRaisesRegex(SystemExit, "outside --native-handoff"):
                    helper["prepare_output_paths"](args, self.repo)
                self.assertFalse((self.root / exchange).exists())

    def assert_retirement_waits_for_submission(self, interrupt):
        ready = self.root / "submitter-ready"
        job = self.root / "submission.json"
        marker = self.root / "submission-entered"
        release = self.root / "submission-release"
        code = '''import json, os, runpy, sys, time
from pathlib import Path
module = runpy.run_path(sys.argv[1])
original = os.replace
def delayed(source, destination, **options):
    Path(sys.argv[4]).touch()
    deadline = time.monotonic() + 10
    while not Path(sys.argv[5]).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("submission was not released")
        time.sleep(.01)
    return original(source, destination, **options)
os.replace = delayed
Path(sys.argv[3]).touch()
while not Path(sys.argv[2]).exists():
    time.sleep(.01)
job = json.loads(Path(sys.argv[2]).read_text())
module["submit_native_response"](Path(job["root"]), Path(job["source"]))
'''
        sender = subprocess.Popen([sys.executable, "-c", code, str(SCRIPT),
            str(job), str(ready), str(marker), str(release)], env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # Import before the helper's short deadline starts, then hold its
            # active writer until timeout cleanup is actually waiting on it.
            deadline = time.monotonic() + 6
            while not ready.exists() and sender.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(ready.exists(), "submission process did not initialize")
            self.start(timeout=".6")
            request = self.request()
            spool = self.root / f"handoff.{request['run_id']}.1.response.json"
            spool.write_text(json.dumps({"run_id": request["run_id"], "pass": 1,
                "prompt_sha256": request["prompt_sha256"], "status": "done", "output": self.completion(request, CLEAN)}))
            pending_job = job.with_suffix(".tmp")
            pending_job.write_text(json.dumps({"root": str(self.handoff), "source": str(spool)}))
            pending_job.replace(job)
            deadline = time.monotonic() + 3
            while not marker.exists() and sender.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(marker.exists(), "submission did not reach the locked write")
            deadline = time.monotonic() + 3
            while not self.status.exists() and self.process.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(self.status.exists(), "helper did not reach timeout cleanup")
            self.assertIsNone(self.process.poll(), "helper exited before its active writer")
            if interrupt:
                self.process.send_signal(signal.SIGTERM)
            release.touch()
            out, err = sender.communicate(timeout=5)
            self.assertEqual(sender.returncode, 0, out + err)
            self.finish(143 if interrupt else 1)
            self.assertTrue(json.loads(self.status.read_text())["timed_out"])
            self.assertFalse(spool.exists())
            self.assertFalse(self.report.exists())
        finally:
            if sender.poll() is None:
                sender.terminate()
            sender.communicate(timeout=5)

    def test_response_commit_and_file_custody(self):
        for case in ("byte mismatch", "symlink"):
            with self.subTest(case=case):
                self.start()
                req = self.request()
                self.deliver(req, commit=False)
                result = self.handoff / "1.result.json"
                size = result.stat().st_size
                if case == "symlink":
                    external = self.root / "external.json"
                    result.rename(external)
                    result.symlink_to(external)
                (self.handoff / "1.ready").write_text(json.dumps({
                    "run_id": req["run_id"], "pass": 1,
                    "bytes": size + (1 if case == "byte mismatch" else 0)}))
                self.finish(1)
                self.assertFalse(self.report.exists())
                self.assertEqual(json.loads(self.status.read_text())["reason"], "invalid_report")

    def test_retirement_waits_for_an_active_submission(self):
        self.assert_retirement_waits_for_submission(False)

    def test_signal_during_retirement_still_joins_submission(self):
        self.assert_retirement_waits_for_submission(True)

    def test_concurrent_exchange_cannot_consume_another_reviews_completion(self):
        self.start()
        first_process, first_handoff = self.process, self.handoff
        first_request = self.request()
        self.handoff = self.root / "second-handoff"
        second_report = self.root / "second-report.json"
        second_status = self.root / "second-status.json"
        self.start("--json-output", str(second_report), "--status-output", str(second_status))
        second_request = self.request()
        self.assertNotEqual(first_request["run_id"], second_request["run_id"])
        self.deliver(first_request)
        self.finish(1)
        self.assertFalse(second_report.exists())
        self.assertTrue(first_handoff.exists())
        self.process, self.handoff = first_process, first_handoff
        self.deliver(first_request)
        self.finish(0)
        self.assertEqual(json.loads(self.report.read_text())["review_status"], "scoped-clean")

    def test_signal_cleans_helper_without_publishing(self):
        self.start()
        self.request()
        self.process.send_signal(signal.SIGTERM)
        self.finish(143)
        self.assertFalse(self.report.exists())

    def test_existing_exchange_and_explicit_cli_are_not_replaced(self):
        self.handoff.mkdir()
        sentinel = self.handoff / "owned-elsewhere"
        sentinel.write_text("keep")
        self.start()
        self.process.communicate(timeout=6)
        self.assertNotEqual(self.process.returncode, 0)
        self.assertEqual(sentinel.read_text(), "keep")
        result = subprocess.run([sys.executable, str(SCRIPT), "--engine", "codex",
            "--native-handoff", str(self.handoff)], cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("never switches an explicit engine", result.stderr)

    def test_image_native_route_refused_before_request(self):
        from PIL import Image
        Image.new("RGB", (1, 1), "white").save(self.repo / "image.png")
        self.git("add", ".")
        self.git("commit", "-qm", "image")
        self.start()
        out, err = self.process.communicate(timeout=6)
        self.assertNotEqual(self.process.returncode, 0, out + err)
        self.assertIn("image review is currently supported only by the Codex engine", err)
        self.assertFalse(self.handoff.exists())
        self.assertFalse(self.report.exists())


if __name__ == "__main__":
    unittest.main()
