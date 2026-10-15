"""Run the real helper against a terminal CLI fixture, without a provider."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import runpy
import subprocess
import sys
import time
import unittest
from unittest import mock

from skills.autoreview.tests import test_native_handoff as native


@unittest.skipUnless(os.name == "posix", "OpenClaw execution uses POSIX custody")
class OpenClawExecTests(native.ReviewFixture):
    def setUp(self):
        super().setUp()
        self.binary = self.root / "openclaw"
        self.capture = self.root / "invocations.jsonl"
        self.config = self.root / "models.json"
        self.provider = {"baseUrl": "https://example.invalid/v1", "api": "openai-completions",
                         "apiKey": "${OPENAI_API_KEY}", "models": [{"id": "reviewer", "name": "Review"}]}
        self.config.write_text(json.dumps({"models": {"providers": {"fixture": self.provider}}}))
        self.binary.write_text("#!" + sys.executable + "\n" + r'''
import json, os, pathlib, signal, subprocess, sys, time
args = sys.argv[1:]
if args == ["agent", "exec", "--help"]:
    print("--message-file --config --cwd --model --thinking --json")
    raise SystemExit()
assert args[:2] == ["agent", "exec"]
assert args[args.index("--message-file") + 1] == "-"
prompt = sys.stdin.read()
config = json.loads(pathlib.Path(args[args.index("--config") + 1]).read_text())
for provider in config["models"]["providers"].values():
    service = provider.get("localService")
    if service:
        subprocess.run([service["command"], *service.get("args", [])],
                       cwd=service.get("cwd"), env=service.get("env"), check=True)
assert "review_completion" in prompt
assert prompt not in " ".join(args)
record = {"args": args, "config": config, "cwd": os.getcwd(), "pid": os.getpid(),
          "prompt": prompt, "home": os.environ["HOME"],
          "provider_key_present": os.environ.get("OPENAI_API_KEY") == "fixture-key",
          "ambient_present": any(x in os.environ for x in ["NODE_OPTIONS", "OPENCLAW_CONFIG_PATH", "OPENCLAW_GATEWAY_TOKEN"])}
with open(os.environ["AUTOREVIEW_FAKE_CAPTURE"], "a") as f:
    f.write(json.dumps(record) + "\n")
case = os.environ.get("AUTOREVIEW_FAKE_CASE", "clean")
if case == "wait":
    signal.pause()
report = {"findings": [], "overall_correctness": "patch is correct", "overall_explanation": "Complete review of supplied scope.", "overall_confidence": 0.9, "review_completion": "complete"}
if case == "incomplete": report["review_completion"] = "incomplete"
if case == "invalid": report = {"review_completion": "complete"}
envelope = {"ok": True, "status": "ok", "final": json.dumps(report), "provider": "fixture", "model": "reviewer"}
if case == "wrong-model": envelope["model"] = "substitute"
if case == "empty": envelope["final"] = ""
if case == "failed-envelope": envelope["ok"], envelope["status"] = False, "error"
if case == "oversized": envelope["padding"] = "x" * 2_000_000
print("not JSON" if case == "malformed" else json.dumps(envelope))
if case == "exit-failure":
    print("sensitive fixture diagnostic", file=sys.stderr)
    raise SystemExit(7)
''')
        self.binary.chmod(0o700)
        self.env.update(AUTOREVIEW_FAKE_CAPTURE=str(self.capture), OPENAI_API_KEY="fixture-key",
                        OPENCLAW_CONFIG_PATH=str(self.root / "ambient.json"),
                        OPENCLAW_GATEWAY_TOKEN="must-not-forward", NODE_OPTIONS="--trace-warnings")

    def start_direct(self, *options, case="clean", timeout="8"):
        self.env["AUTOREVIEW_FAKE_CASE"] = case
        self.process = subprocess.Popen([
            sys.executable, str(native.SCRIPT), "--mode", "branch", "--base", self.base,
            "--engine", "openclaw", "--openclaw-bin", str(self.binary), "--openclaw-config", str(self.config),
            "--model", "fixture/reviewer", "--thinking", "high", "--engine-timeout-seconds", timeout,
            "--json-output", str(self.report), "--status-output", str(self.status), *options],
            cwd=self.repo, env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.processes.append(self.process)
        return self.process

    def finish_direct(self, code):
        stdout, stderr = self.process.communicate(timeout=12)
        self.assertEqual(self.process.returncode, code, stdout + stderr)
        records = [json.loads(line) for line in self.capture.read_text().splitlines()] if self.capture.exists() else []
        for record in records:
            self.assertFalse(Path(record["cwd"]).parent.exists(), "private runtime leaked")
        return records, stdout + stderr

    def test_direct_cli_keeps_prompt_private_and_owns_restrictions(self):
        config = self.root / "operator.json"
        sentinel = self.root / "must-not-start-service"
        unsafe_provider = self.provider | {
            "localService": {"command": sys.executable,
                             "args": ["-c", "from pathlib import Path; Path(" + repr(str(sentinel)) + ").touch()"],
                             "cwd": str(self.repo)},
            "agentRuntime": {"id": "external-runtime"},
            "models": [self.provider["models"][0] | {"agentRuntime": {"id": "external-runtime"}}],
        }
        config.write_text(json.dumps({"models": {"providers": {"fixture": unsafe_provider, "unused": {"models": [{"id": "other"}]}}}, "tools": {"allow": ["*"]},
                                     "agents": {"entries": {"unsafe": {"skills": ["all"]}}},
                                     "plugins": {"allow": ["unsafe"]}, "env": {"UNSAFE": "value"}}))
        self.start_direct("--openclaw-config", str(config))
        records, _ = self.finish_direct(0)
        self.assertEqual(len(records), 1)
        self.assertFalse(sentinel.exists(), "provider command escaped restricted configuration")
        record = records[0]
        self.assertEqual(record["config"]["tools"], {"deny": ["*"], "codeMode": {"enabled": False}})
        self.assertEqual(record["config"]["agents"]["entries"], {"main": {"skills": [], "contextInjection": "never"}})
        self.assertEqual(record["config"]["agents"]["defaults"]["model"], {"primary": "fixture/reviewer", "fallbacks": []})
        self.assertEqual(record["config"]["agents"]["defaults"]["models"]["fixture/reviewer"], {"agentRuntime": {"id": "openclaw"}})
        self.assertEqual(record["config"]["plugins"], {"allow": []})
        self.assertEqual(record["config"]["models"], {"providers": {"fixture": self.provider}})
        self.assertFalse(record["ambient_present"])
        self.assertTrue(record["provider_key_present"])
        self.assertEqual(record["args"][record["args"].index("--thinking") + 1], "high")
        self.assertEqual(json.loads(self.status.read_text())["status"], "scoped-clean")

    def test_terminal_failures_never_retry_or_salvage_a_report(self):
        for case in ("malformed", "empty", "wrong-model", "invalid", "failed-envelope", "oversized", "exit-failure", "incomplete"):
            with self.subTest(case=case):
                self.capture.unlink(missing_ok=True)
                self.report.unlink(missing_ok=True)
                self.status.unlink(missing_ok=True)
                self.start_direct(case=case)
                records, output = self.finish_direct(2 if case == "incomplete" else 1)
                self.assertEqual(len(records), 1)
                self.assertNotIn("sensitive fixture diagnostic", output)
                status = json.loads(self.status.read_text())
                self.assertEqual(status["status"], "incomplete" if case == "incomplete" else "reviewer_unavailable")
                self.assertEqual(status["report_produced"], case == "incomplete")

    def test_timeout_and_cancellation_settle_child_and_remove_runtime(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                self.capture.unlink(missing_ok=True)
                self.status.unlink(missing_ok=True)
                self.start_direct(case="wait", timeout="8" if cancel else ".4")
                if cancel:
                    deadline = time.monotonic() + 5
                    while not self.capture.exists() and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertTrue(self.capture.exists())
                    self.process.send_signal(signal.SIGTERM)
                records, _ = self.finish_direct(143 if cancel else 1)
                self.assertEqual(len(records), 1)
                with self.assertRaises(ProcessLookupError):
                    os.kill(records[0]["pid"], 0)
                self.assertFalse(self.report.exists())

    def test_missing_catalog_and_repository_config_fail_before_cli_launch(self):
        config = self.repo / "models.json"
        config.write_text('{"models":{}}')
        missing = self.root / "missing-model.json"
        missing.write_text('{"models":{"providers":{}}}')
        for candidate, message in ((str(config), "outside the reviewed repository"),
                                   ("", "requires --openclaw-config"),
                                   (str(missing), "selected models.providers catalog entry")):
            with self.subTest(config=candidate):
                self.start_direct("--openclaw-config", candidate)
                records, output = self.finish_direct(1)
                self.assertEqual(records, [])
                self.assertIn(message, output)

    def test_direct_config_environment_does_not_change_other_routes(self):
        parse = runpy.run_path(str(native.SCRIPT))["parse_args"]
        with mock.patch.dict(os.environ, {"AUTOREVIEW_OPENCLAW_CONFIG": str(self.config)}):
            for arguments, expected in ((["--engine", "codex"], None),
                                        (["--engine", "openclaw"], str(self.config)),
                                        (["--engine", "openclaw", "--native-handoff", str(self.handoff),
                                          "--engine-timeout-seconds", "10"], None)):
                with mock.patch.object(sys, "argv", [str(native.SCRIPT), *arguments]):
                    self.assertEqual(parse().openclaw_config, expected)

    def test_direct_dry_run_probes_without_model_launch(self):
        self.start_direct("--dry-run")
        records, _ = self.finish_direct(0)
        self.assertEqual(records, [])
        self.assertFalse(self.report.exists())


if __name__ == "__main__":
    unittest.main()
