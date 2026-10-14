"""Exercise the real helper and the documented Code Mode consumer without a provider."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "autoreview"
REFERENCE = SCRIPT.parents[1] / "references" / "openclaw.md"
CLEAN = {"findings": [], "overall_correctness": "patch is correct",
         "overall_explanation": "Complete review of the supplied pass.",
         "overall_confidence": 0.9, "review_completion": "complete"}
FINDING = {"title": "[P2] Restore free shipping at the threshold",
           "body": "An order of exactly 100 now pays shipping despite the inclusive threshold.",
           "priority": "P2", "confidence": 0.99, "category": "regression",
           "code_location": {"file_path": "shipping.py", "line": 1}, "source_attribution": None}


@unittest.skipUnless(os.name == "posix", "native handoff uses POSIX custody")
class NativeHandoffTests(unittest.TestCase):
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

    def tearDown(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.process.communicate(timeout=5)
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, env=self.env, text=True)

    def start(self, *options, timeout="8"):
        self.process = subprocess.Popen([
            sys.executable, str(SCRIPT), "--mode", "branch", "--base", self.base,
            "--engine", "openclaw", "--native-handoff", str(self.handoff),
            "--engine-timeout-seconds", timeout, "--json-output", str(self.report),
            "--status-output", str(self.status), *options],
            cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        self.assertEqual(result["prompt_bytes"], len(result["prompt"].encode()))
        self.assertEqual(result["prompt_sha256"], hashlib.sha256(result["prompt"].encode()).hexdigest())
        self.assertEqual(self.handoff.stat().st_mode & 0o777, 0o700)
        return result

    def deliver(self, request, report=None, *, modify=None, raw=None, commit=True):
        response = {"run_id": request["run_id"], "pass": request["pass"],
                    "prompt_sha256": request["prompt_sha256"], "status": "done",
                    "report": copy.deepcopy(CLEAN if report is None else report)}
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

    def consumer(self, request, report=CLEAN, *, failure=False, page_size=67):
        """Run the exact shipped cell, substituting only its three documented inputs."""
        if not shutil.which("node"):
            self.fail("Node is required for the documented consumer contract test")
        cell = re.search(r"```javascript\n(.*?)\n```", REFERENCE.read_text(), re.S).group(1)
        cell = cell.replace('"/absolute/private/task/handoff"', json.dumps(str(self.handoff)))
        cell = cell.replace("const passNumber = 1;", f'const passNumber = {request["pass"]};')
        harness = r'''
const fs = require("node:fs");
const crypto = require("node:crypto");
const supplied = JSON.parse(process.env.NATIVE_FIXTURE);
let launches = 0;
async function read(input) {
  const data = fs.readFileSync(input.path, "utf8");
  const offset = Number(input.cursor || 0), end = Math.min(offset + supplied.pageSize, data.length);
  return {kind: end < data.length ? "truncated" : "text", content: data.slice(offset, end),
    ...(end < data.length ? {continuation: {offset: 1, cursor: String(end)}} : {})};
}
async function write(input) { fs.writeFileSync(input.path, input.content); }
const agents = {async run(prompt, options) {
  launches++;
  const start = "<autoreview-pass>\n", end = "\n</autoreview-pass>";
  if (!prompt.startsWith(start) || !prompt.endsWith(end)) throw Error("missing wrapper");
  const exact = prompt.slice(start.length, -end.length);
  if (crypto.createHash("sha256").update(exact).digest("hex") !== supplied.digest)
    throw Error("prompt bytes changed");
  if (options.agentId !== "existing-restricted-reviewer" || !options.schema.required.includes("review_completion"))
    throw Error("collector contract changed");
  if (options.model !== supplied.model || options.thinking !== supplied.thinking)
    throw Error("explicit model/effort lost");
  if (supplied.failure) throw Error("terminal collector failure");
  return supplied.report;
}};
'''
        harness += "(async () => {\n" + cell + "\n})().then(result => console.log(JSON.stringify({result, launches}))).catch(error => {console.log(JSON.stringify({error: error.message, launches})); process.exitCode = 1;});"
        env = self.env | {"NATIVE_FIXTURE": json.dumps({"digest": request["prompt_sha256"],
            "report": report, "failure": failure, "pageSize": page_size,
            **({"model": request["model"]} if request["model"] is not None else {}),
            **({"thinking": request["thinking"]} if request["thinking"] is not None else {})})}
        result = subprocess.run(["node", "-e", harness], env=env, text=True, capture_output=True, timeout=6)
        self.assertEqual(json.loads(result.stdout)["launches"], 1, result.stderr)
        return result

    def test_documented_consumer_complete_and_explicit_model(self):
        self.start("--model", "openai/gpt-6-astra", "--thinking", "high")
        request = self.request()
        self.assertEqual(request["model"], "openai/gpt-6-astra")
        self.assertEqual(self.consumer(request).returncode, 0)
        self.finish(0)
        self.assertEqual(json.loads(self.report.read_text())["review_status"], "scoped-clean")

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
            self.assertEqual(self.consumer(req, page_size=31_000).returncode, 0)
        self.finish(0)
        report = json.loads(self.report.read_text())
        self.assertEqual(len(report["pass_reports"]), first["passes"])
        self.assertEqual(report["review_status"], "scoped-clean")

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
        self.assertEqual(self.consumer(self.request(), failure=True).returncode, 1)
        self.finish(1)
        self.assertFalse(self.report.exists())

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
