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
        self.config = self.root / "operator.json"
        self.home = self.root / "home"
        self.home.mkdir()
        (self.home / "auth.json").write_text('{"fixture":"stored-login"}')
        self.config.write_text(json.dumps({"agents": {
            "defaults": {"systemAgent": {"agentId": "review"},
                         "model": {"primary": "fixture/default", "fallbacks": ["fixture/backup"]}},
            "entries": {"review": {"skills": ["ambient"], "contextInjection": "always", "nativeRuntimeConsent": ["codex"],
                                   "tools": {"alsoAllow": ["autoreview"], "byProvider": {"fixture": {"allow": ["read"]}}, "sandbox": {"tools": {"alsoAllow": ["read"]}}}},
                        "string-model": {"model": "fixture/string"},
                        "object-model": {"model": {"primary": "fixture/object", "fallbacks": ["fixture/backup"]}}}},
            "tools": {"allow": ["read"], "byProvider": {"fixture": {"alsoAllow": ["read"]}}, "sandbox": {"tools": {"allow": ["read"]}}},
            "models": {"providers": {"fixture": {"apiKey": "${CUSTOM_PROVIDER_KEY}", "models": [{"id": "default"}]}}},
            "gateway": {"auth": {"token": "${OPENCLAW_GATEWAY_TOKEN}"}}}))
        self.binary.write_text("#!" + sys.executable + "\n" + r'''
import json, os, pathlib, signal, sys
args = sys.argv[1:]
if args == ["agent", "exec", "--help"]:
    print("--message-file --config --config-override --cwd --model --thinking --json")
    raise SystemExit()
config_path = pathlib.Path(args[args.index("--config") + 1] if "--config" in args else os.environ["OPENCLAW_CONFIG_PATH"])
try:
    base = json.loads(config_path.read_text())
    if "${CUSTOM_PROVIDER_KEY}" in json.dumps(base) and os.environ.get("CUSTOM_PROVIDER_KEY") != "fixture-custom-key":
        raise ValueError("missing native environment interpolation input")
except (OSError, ValueError):
    print(json.dumps({"ok": False, "error": {"type": "cli_error", "message": "invalid configuration"}}))
    raise SystemExit(1)
if len(args) == 4 and args[:2] == ["config", "get"] and args[-1] == "--json":
    section = args[2]
    if section not in base:
        print(json.dumps({"ok": False, "error": {"type": "cli_error", "message": f"Config path is valid but unset: {section}. The runtime default applies until you set an authored value."}}))
        raise SystemExit(1)
    print(json.dumps(base[section]))
    raise SystemExit()
assert args[:2] == ["agent", "exec"]
assert args[args.index("--message-file") + 1] == "-"
prompt = sys.stdin.read()
override = json.loads(args[args.index("--config-override") + 1])
assert "review_completion" in prompt
assert prompt not in " ".join(args)
default = base.get("agents", {}).get("defaults", {}).get("model", "fixture/default")
model = args[args.index("--model") + 1] if "--model" in args else default
if isinstance(model, dict): model = model["primary"]
record = {"args": args, "override": override, "config_path": str(config_path),
          "cwd": os.getcwd(), "pid": os.getpid(), "prompt": prompt,
          "home": os.environ["HOME"], "stored_auth": (pathlib.Path(os.environ["HOME"]) / "auth.json").exists(),
          "provider_key_present": os.environ.get("OPENAI_API_KEY") == "fixture-key",
          "custom_key_present": os.environ.get("CUSTOM_PROVIDER_KEY") == "fixture-custom-key",
          "gateway_key_present": os.environ.get("OPENCLAW_GATEWAY_TOKEN") == "fixture-gateway-key",
          "repo_auth_present": "CODEX_HOME" in os.environ,
          "unsafe_env_present": any(x in os.environ for x in ["NODE_OPTIONS", "NODE_PATH", "BUN_OPTIONS", "BASH_ENV"])}
with open(os.environ["AUTOREVIEW_FAKE_CAPTURE"], "a") as f:
    f.write(json.dumps(record) + "\n")
case = os.environ.get("AUTOREVIEW_FAKE_CASE", "clean")
if case == "wait": signal.pause()
report = {"findings": [], "overall_correctness": "patch is correct", "overall_explanation": "Complete review of supplied scope.", "overall_confidence": 0.9, "review_completion": "complete"}
if case == "incomplete": report["review_completion"] = "incomplete"
if case == "invalid": report = {"review_completion": "complete"}
provider, model_id = model.split("/", 1)
envelope = {"ok": True, "status": "ok", "final": json.dumps(report), "provider": provider, "model": model_id}
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
                        HOME=str(self.home), OPENCLAW_CONFIG_PATH=str(self.config),
                        CUSTOM_PROVIDER_KEY="fixture-custom-key", OPENCLAW_GATEWAY_TOKEN="fixture-gateway-key",
                        NODE_OPTIONS="--trace-warnings", NODE_PATH=str(self.repo),
                        BUN_OPTIONS="--preload=hostile.js", BASH_ENV=str(self.repo / "hostile.sh"),
                        CODEX_HOME=str(self.repo / "hostile-auth"))

    def start_direct(self, *options, case="clean", timeout="8"):
        self.env["AUTOREVIEW_FAKE_CASE"] = case
        self.process = subprocess.Popen([
            sys.executable, str(native.SCRIPT), "--mode", "branch", "--base", self.base,
            "--engine", "openclaw", "--openclaw-bin", str(self.binary),
            "--engine-timeout-seconds", timeout, "--json-output", str(self.report),
            "--status-output", str(self.status), *options],
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

    def test_direct_inherits_native_selection_and_auth_with_sparse_restrictions(self):
        original = self.config.read_bytes()
        self.start_direct()
        records, output = self.finish_direct(0)
        self.assertEqual(len(records), 1)
        record = records[0]
        empty_grants = {"allow": [], "alsoAllow": [], "sandbox": {"tools": {"allow": [], "alsoAllow": []}}}
        provider_grants = empty_grants | {"byProvider": {"fixture": {"allow": [], "alsoAllow": []}}}
        self.assertEqual(record["override"], {
            "tools": provider_grants | {"deny": ["*"], "toolSearch": False, "codeMode": {"enabled": False}},
            "agents": {"defaults": {"skills": [], "contextInjection": "never", "model": {"fallbacks": []}},
                       "entries": {"review": {"skills": [], "contextInjection": "never", "nativeRuntimeConsent": [], "tools": provider_grants},
                                   "string-model": {"skills": [], "contextInjection": "never", "nativeRuntimeConsent": [], "tools": empty_grants},
                                   "object-model": {"skills": [], "contextInjection": "never", "model": {"fallbacks": []}, "nativeRuntimeConsent": [], "tools": empty_grants}}}})
        for option in ("--model", "--thinking", "--config", "--state-dir", "--isolated"):
            self.assertNotIn(option, record["args"])
        self.assertEqual(record["home"], str(self.home.resolve()))
        self.assertTrue(record["stored_auth"])
        self.assertTrue(record["provider_key_present"])
        self.assertTrue(record["custom_key_present"])
        self.assertTrue(record["gateway_key_present"])
        self.assertFalse(record["repo_auth_present"])
        self.assertFalse(record["unsafe_env_present"])
        self.assertEqual(self.config.read_bytes(), original)
        self.assertIn("effective model: fixture/default", output)
        self.assertEqual(json.loads(self.status.read_text())["status"], "scoped-clean")
        self.assertEqual(json.loads(self.status.read_text())["effective_models"], ["fixture/default"])

    def test_explicit_options_override_canonical_environment_and_select_native_config(self):
        selected = self.root / "selected.json"
        selected.write_text('{"agents":{"defaults":{"model":"fixture/selected"}}}')
        self.env.update(AUTOREVIEW_OPENCLAW_MODEL="fixture/configured", AUTOREVIEW_OPENCLAW_THINKING="low")
        self.start_direct("--openclaw-config", str(selected), "--model", "fixture/explicit", "--thinking", "high")
        records, output = self.finish_direct(0)
        record = records[0]
        self.assertEqual(record["config_path"], str(selected))
        self.assertEqual(record["override"]["agents"]["defaults"], {"skills": [], "contextInjection": "never"})
        self.assertEqual(record["args"][record["args"].index("--thinking") + 1], "high")
        self.assertIn("effective model: fixture/explicit", output)

    def test_terminal_failures_never_retry_or_salvage_a_report(self):
        for case in ("malformed", "empty", "wrong-model", "invalid", "failed-envelope", "oversized", "exit-failure", "incomplete"):
            with self.subTest(case=case):
                self.capture.unlink(missing_ok=True)
                self.report.unlink(missing_ok=True)
                self.status.unlink(missing_ok=True)
                self.start_direct("--model", "fixture/reviewer", case=case)
                records, output = self.finish_direct(2 if case == "incomplete" else 1)
                self.assertEqual(len(records), 1)
                self.assertNotIn("sensitive fixture diagnostic", output)
                status = json.loads(self.status.read_text())
                self.assertEqual(status["status"], "incomplete" if case == "incomplete" else "reviewer_unavailable")
                self.assertEqual(status["report_produced"], case == "incomplete")
                if case == "wrong-model":
                    self.assertNotIn("effective_models", status)

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

    def test_repository_config_and_native_config_failure_prevent_execution(self):
        for candidate, message in ((self.repo / "config.json", "outside the reviewed repository"),
                                   (self.root / "missing.json", "configuration could not be read")):
            with self.subTest(config=candidate):
                self.start_direct("--openclaw-config", str(candidate))
                records, output = self.finish_direct(1)
                self.assertEqual(records, [])
                self.assertIn(message, output)

    def test_only_native_valid_unset_agents_uses_configless_defaults(self):
        self.config.write_text("{}")
        self.start_direct()
        records, _ = self.finish_direct(0)
        self.assertEqual(records[0]["override"]["agents"], {"defaults": {"skills": [], "contextInjection": "never", "model": {"fallbacks": []}}})

    def test_direct_config_environment_does_not_change_other_routes(self):
        parse = runpy.run_path(str(native.SCRIPT))["parse_args"]
        with mock.patch.dict(os.environ, {"AUTOREVIEW_OPENCLAW_CONFIG": str(self.config)}):
            for arguments, expected in ((["--engine", "codex"], None),
                                        (["--engine", "openclaw"], str(self.config)),
                                        (["--engine", "openclaw", "--native-handoff", str(self.handoff)], None)):
                with mock.patch.object(sys, "argv", [str(native.SCRIPT), *arguments]):
                    self.assertEqual(parse().openclaw_config, expected)

    def test_direct_dry_run_probes_without_model_launch(self):
        self.start_direct("--dry-run")
        records, _ = self.finish_direct(0)
        self.assertEqual(records, [])
        self.assertFalse(self.report.exists())
        self.binary.write_text(self.binary.read_text().replace("--config --config-override --cwd", "--config --cwd"))
        self.start_direct("--dry-run")
        records, output = self.finish_direct(1)
        self.assertEqual(records, [])
        self.assertIn("--config-override", output)


if __name__ == "__main__":
    unittest.main()
