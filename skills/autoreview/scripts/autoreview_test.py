#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).with_name("autoreview")
HARNESS_PATH = SCRIPT_PATH.with_name("test-review-harness.py")
VALIDATOR_PATH = SCRIPT_PATH.with_name("validate-autoreview.py")
LOADER = SourceFileLoader("autoreview_module", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
AUTOREVIEW = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(AUTOREVIEW)


FINAL_REPORT = {
    "findings": [],
    "overall_correctness": "patch is correct",
    "overall_explanation": "clean",
    "overall_confidence": 0.9,
}

DRAFT_REPORT = {
    "findings": [
        {
            "title": "Draft finding",
            "body": "draft",
            "priority": "P3",
            "confidence": 0.2,
            "category": "maintainability",
            "code_location": {"file_path": "draft.js", "line": 1},
        }
    ],
    "overall_correctness": "patch is incorrect",
    "overall_explanation": "draft",
    "overall_confidence": 0.2,
}


class AutoreviewCursorTests(unittest.TestCase):
    def test_extract_json_prefers_terminal_result_event(self) -> None:
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"role": "assistant", "content": [{"type": "text", "text": json.dumps(DRAFT_REPORT)}]},
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "subtype": "success",
                        "result": json.dumps(FINAL_REPORT),
                        "session_id": "session-id",
                        "request_id": "request-id",
                    }
                ),
            ]
        )
        self.assertEqual(AUTOREVIEW.extract_json(stream), FINAL_REPORT)

    def test_extract_json_can_fallback_to_assistant_message(self) -> None:
        stream = json.dumps(
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": json.dumps(FINAL_REPORT)}]},
            }
        )
        self.assertEqual(AUTOREVIEW.extract_json(stream), FINAL_REPORT)

    def test_extract_json_does_not_fallback_past_bad_terminal_result(self) -> None:
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"role": "assistant", "content": [{"type": "text", "text": json.dumps(FINAL_REPORT)}]},
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "subtype": "success",
                        "result": "not json",
                    }
                ),
            ]
        )
        with self.assertRaises(SystemExit) as exc_info:
            AUTOREVIEW.extract_json(stream)
        self.assertIn("review engine result was not structured JSON", str(exc_info.exception))


class AutoreviewCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.home_dir = tempfile.TemporaryDirectory(prefix="autoreview-test-home.")
        cls.home_patch = mock.patch.object(Path, "home", return_value=Path(cls.home_dir.name))
        cls.home_patch.start()
        cls.home_keys = ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")
        cls.old_home_env = {key: os.environ.get(key) for key in cls.home_keys}
        os.environ["HOME"] = cls.home_dir.name
        os.environ["USERPROFILE"] = cls.home_dir.name
        os.environ.pop("HOMEDRIVE", None)
        os.environ.pop("HOMEPATH", None)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.home_patch.stop()
        for key, value in cls.old_home_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls.home_dir.cleanup()

    def test_harness_rejects_disabled_cursor_engine(self) -> None:
        namespace = runpy.run_path(str(HARNESS_PATH))
        with self.assertRaises(SystemExit):
            namespace["parse_args"](["--engine", "cursor"])

    def test_cursor_agent_bin_cli_alias(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            ["autoreview", "--cursor-agent-bin", "/tmp/legacy-cursor"],
        ):
            args = AUTOREVIEW.parse_args()
        self.assertEqual(args.cursor_bin, "/tmp/legacy-cursor")

    def test_cursor_agent_bin_env_alias(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"CURSOR_AGENT_BIN": "/tmp/legacy-cursor"},
            clear=False,
        ):
            os.environ.pop("CURSOR_BIN", None)
            with mock.patch.object(sys, "argv", ["autoreview"]):
                args = AUTOREVIEW.parse_args()
        self.assertEqual(args.cursor_bin, "/tmp/legacy-cursor")

    def test_cursor_agent_reviewer_alias_normalizes_to_cursor(self) -> None:
        self.assertEqual(
            AUTOREVIEW.parse_reviewer_token("cursor-agent:auto"),
            ("cursor", "auto", None),
        )

    def test_cursor_agent_keyed_option_normalizes_to_cursor(self) -> None:
        self.assertEqual(
            AUTOREVIEW.parse_keyed_options(["cursor-agent=auto"], "model"),
            (None, {"cursor": "auto"}),
        )

    def test_codex_config_status_exposes_keys_only(self) -> None:
        args = argparse.Namespace(codex_config=['model_verbosity="low"'])
        self.assertEqual(AUTOREVIEW.codex_config_keys(args), ["model_verbosity"])

    def test_codex_retries_terra_after_sol_access_failure(self) -> None:
        args = argparse.Namespace(
            codex_bin="codex",
            codex_config=None,
            codex_speed=None,
            fallback_model="gpt-5.6-terra",
            model="gpt-5.6-sol",
            stream_engine_output=False,
            thinking="high",
            tools=True,
            web_search=False,
        )
        models: list[str] = []

        def fake_run(command: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            model = command[command.index("--model") + 1]
            models.append(model)
            if model == "gpt-5.6-sol":
                return subprocess.CompletedProcess(
                    command,
                    1,
                    "",
                    "The model `gpt-5.6-sol` does not exist or you do not have access to it.",
                )
            output_path = Path(command[command.index("--output-last-message") + 1])
            output_path.write_text(json.dumps(FINAL_REPORT))
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory(prefix="autoreview-codex-fallback.") as tmpdir, mock.patch.object(
            AUTOREVIEW,
            "resolve_command",
            return_value="/usr/bin/codex",
        ), mock.patch.object(AUTOREVIEW, "codex_auth_config_flags", return_value=[]), mock.patch.object(
            AUTOREVIEW,
            "prepare_codex_runtime_auth",
            return_value=None,
        ), mock.patch.object(
            AUTOREVIEW,
            "run_with_heartbeat",
            side_effect=fake_run,
        ):
            output = AUTOREVIEW.run_codex(args, Path(tmpdir), "review")

        self.assertEqual(json.loads(output), FINAL_REPORT)
        self.assertEqual(models, ["gpt-5.6-sol", "gpt-5.6-terra"])

    def test_codex_runs_outside_repo_with_bundle_only_workspace(self) -> None:
        args = argparse.Namespace(
            codex_bin="codex",
            codex_config=None,
            codex_speed=None,
            fallback_model=None,
            model="gpt-5.6-sol",
            stream_engine_output=False,
            thinking="high",
            tools=True,
            web_search=False,
        )
        observed: dict[str, object] = {}

        def fake_run(
            command: list[str],
            cwd: Path,
            *_args: object,
            **kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            observed["cwd"] = cwd
            observed["command"] = command
            observed["command_cwd"] = Path(command[command.index("-C") + 1])
            observed["workspace_entries"] = list(cwd.iterdir())
            observed["env"] = kwargs["env"]
            output_path = Path(command[command.index("--output-last-message") + 1])
            output_path.write_text(json.dumps(FINAL_REPORT))
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory(prefix="autoreview-codex-workspace-test.") as tmpdir:
            repo = Path(tmpdir)
            (repo / ".env").write_text("OPENAI_API_KEY=ignored-secret\n")
            with mock.patch.dict(
                os.environ,
                {"CODEX_HOME": ""},
                clear=False,
            ), mock.patch.object(
                AUTOREVIEW,
                "resolve_command",
                return_value="/usr/bin/codex",
            ), mock.patch.object(
                AUTOREVIEW,
                "codex_auth_config_flags",
                return_value=[],
            ), mock.patch.object(
                AUTOREVIEW,
                "prepare_codex_runtime_auth",
                return_value=None,
            ), mock.patch.object(
                AUTOREVIEW,
                "codex_source_home",
                return_value=None,
            ), mock.patch.object(
                AUTOREVIEW,
                "run_with_heartbeat",
                side_effect=fake_run,
            ):
                output = AUTOREVIEW.run_codex(args, repo, "review")

            self.assertEqual(json.loads(output), FINAL_REPORT)
            observed_cwd = observed["cwd"]
            command_cwd = observed["command_cwd"]
            self.assertIsInstance(observed_cwd, Path)
            self.assertIsInstance(command_cwd, Path)
            assert isinstance(observed_cwd, Path)
            assert isinstance(command_cwd, Path)
            self.assertNotEqual(observed_cwd.resolve(), repo.resolve())
            self.assertEqual(observed_cwd, command_cwd)
            self.assertEqual(observed["workspace_entries"], [])
            env = observed["env"]
            self.assertIsInstance(env, dict)
            assert isinstance(env, dict)
            self.assertNotEqual(env["HOME"], os.environ.get("HOME"))
            self.assertEqual(env["USERPROFILE"], env["HOME"])
            self.assertNotEqual(env.get("CODEX_HOME"), str(repo.resolve()))
            self.assertEqual(Path(env["CODEX_HOME"]).name, "codex-home")
            self.assertNotEqual(env["CODEX_HOME"], str((Path.home() / ".codex").resolve()))
            self.assertIn("features.shell_snapshot=false", observed["command"])
            self.assertIn("features.hooks=false", observed["command"])
            self.assertIn("features.plugins=false", observed["command"])
            self.assertIn("skills.include_instructions=false", observed["command"])

    def test_codex_does_not_fallback_after_unrelated_failure(self) -> None:
        args = argparse.Namespace(
            codex_bin="codex",
            codex_config=None,
            codex_speed=None,
            fallback_model="gpt-5.6-terra",
            model="gpt-5.6-sol",
            stream_engine_output=False,
            thinking="high",
            tools=True,
            web_search=False,
        )
        models: list[str] = []

        def fake_run(command: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            models.append(command[command.index("--model") + 1])
            return subprocess.CompletedProcess(command, 1, "", "network timeout")

        with tempfile.TemporaryDirectory(prefix="autoreview-codex-fallback.") as tmpdir, mock.patch.object(
            AUTOREVIEW,
            "resolve_command",
            return_value="/usr/bin/codex",
        ), mock.patch.object(AUTOREVIEW, "codex_auth_config_flags", return_value=[]), mock.patch.object(
            AUTOREVIEW,
            "prepare_codex_runtime_auth",
            return_value=None,
        ), mock.patch.object(
            AUTOREVIEW,
            "run_with_heartbeat",
            side_effect=fake_run,
        ):
            with self.assertRaisesRegex(SystemExit, "network timeout"):
                AUTOREVIEW.run_codex(args, Path(tmpdir), "review")

        self.assertEqual(models, ["gpt-5.6-sol"])

    def test_codex_does_not_fallback_after_model_capacity_failure(self) -> None:
        args = argparse.Namespace(
            codex_bin="codex",
            codex_config=None,
            codex_speed=None,
            fallback_model="gpt-5.6-terra",
            model="gpt-5.6-sol",
            stream_engine_output=False,
            thinking="high",
            tools=True,
            web_search=False,
        )
        models: list[str] = []

        def fake_run(command: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            models.append(command[command.index("--model") + 1])
            return subprocess.CompletedProcess(
                command,
                1,
                "",
                "model_not_available: gpt-5.6-sol is temporarily unavailable due to capacity",
            )

        with tempfile.TemporaryDirectory(prefix="autoreview-codex-fallback.") as tmpdir, mock.patch.object(
            AUTOREVIEW,
            "resolve_command",
            return_value="/usr/bin/codex",
        ), mock.patch.object(AUTOREVIEW, "codex_auth_config_flags", return_value=[]), mock.patch.object(
            AUTOREVIEW,
            "prepare_codex_runtime_auth",
            return_value=None,
        ), mock.patch.object(
            AUTOREVIEW,
            "run_with_heartbeat",
            side_effect=fake_run,
        ):
            with self.assertRaisesRegex(SystemExit, "temporarily unavailable"):
                AUTOREVIEW.run_codex(args, Path(tmpdir), "review")

        self.assertEqual(models, ["gpt-5.6-sol"])

    def test_codex_access_fallback_ignores_structured_output_text(self) -> None:
        result = subprocess.CompletedProcess(
            ["codex"],
            1,
            '{"type":"agent_message","text":"gpt-5.6-sol does not exist or you do not have access"}',
            '{"type":"agent_message","message":"gpt-5.6-sol does not exist or you do not have access"}',
        )

        self.assertFalse(
            AUTOREVIEW.codex_model_access_failure(result, "gpt-5.6-sol")
        )

    def test_codex_access_fallback_accepts_terminal_error_event(self) -> None:
        result = subprocess.CompletedProcess(
            ["codex"],
            1,
            '{"type":"error","message":"gpt-5.6-sol does not exist or you do not have access"}',
            "",
        )

        self.assertTrue(
            AUTOREVIEW.codex_model_access_failure(result, "gpt-5.6-sol")
        )

    def test_codex_access_fallback_accepts_account_model_list_error(self) -> None:
        result = subprocess.CompletedProcess(
            ["codex"],
            1,
            "",
            (
                "The model gpt-5.6-sol does not appear in the list of models "
                "available to your account"
            ),
        )

        self.assertTrue(
            AUTOREVIEW.codex_model_access_failure(result, "gpt-5.6-sol")
        )

    def test_codex_access_fallback_ignores_plain_stdout(self) -> None:
        message = "gpt-5.6-sol does not exist or you do not have access"
        stdout_result = subprocess.CompletedProcess(["codex"], 1, message, "")
        stderr_result = subprocess.CompletedProcess(["codex"], 1, "", message)

        self.assertFalse(
            AUTOREVIEW.codex_model_access_failure(stdout_result, "gpt-5.6-sol")
        )
        self.assertTrue(
            AUTOREVIEW.codex_model_access_failure(stderr_result, "gpt-5.6-sol")
        )

    def test_extract_json_accepts_dict_result_payload(self) -> None:
        payload = {
            "type": "result",
            "subtype": "success",
            "result": FINAL_REPORT,
            "session_id": "session-id",
            "request_id": "request-id",
        }
        self.assertEqual(AUTOREVIEW.extract_json(json.dumps(payload)), FINAL_REPORT)

    def test_extract_json_rejects_result_string_with_preamble(self) -> None:
        payload = {
            "type": "result",
            "subtype": "success",
            "result": "Inspecting the diff first.\n" + json.dumps(FINAL_REPORT),
        }
        with self.assertRaisesRegex(SystemExit, "result was not structured JSON"):
            AUTOREVIEW.extract_json(json.dumps(payload))

    def test_retry_filter_only_matches_parse_failures(self) -> None:
        self.assertTrue(AUTOREVIEW.is_structured_output_failure("review engine returned non-JSON output: nope"))
        self.assertTrue(AUTOREVIEW.is_structured_output_failure("review engine result was not structured JSON:\nnope"))
        self.assertFalse(AUTOREVIEW.is_structured_output_failure("review JSON missing required key: findings"))
        self.assertFalse(AUTOREVIEW.is_structured_output_failure("finding 0 has invalid priority"))

    def test_cursor_workspace_instructions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-cursor-test.") as tmpdir:
            repo = Path(tmpdir)
            args = argparse.Namespace(
                thinking=None,
                tools=True,
                web_search=True,
                cursor_allow_workspace_instructions=False,
                cursor_bin="cursor-agent",
                model="auto",
                stream_engine_output=False,
            )
            with self.assertRaises(SystemExit) as exc_info:
                AUTOREVIEW.run_cursor(args, repo, "prompt")
            self.assertIn("cursor engine is unavailable", str(exc_info.exception))

    def test_cursor_local_mcp_requires_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-cursor-test.") as tmpdir:
            repo = Path(tmpdir)
            (repo / ".cursor").mkdir()
            (repo / ".cursor" / "mcp.json").write_text("{}\n")
            args = argparse.Namespace(
                thinking=None,
                tools=True,
                web_search=True,
                cursor_allow_workspace_instructions=True,
                cursor_bin="cursor-agent",
                model="auto",
                stream_engine_output=False,
            )
            with self.assertRaises(SystemExit) as exc_info:
                AUTOREVIEW.run_cursor(args, repo, "prompt")
            self.assertIn("cursor engine is unavailable", str(exc_info.exception))

    def test_cursor_local_hooks_are_always_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-cursor-test.") as tmpdir:
            repo = Path(tmpdir)
            (repo / ".cursor").mkdir()
            (repo / ".cursor" / "hooks.json").write_text("{}\n")
            args = argparse.Namespace(
                thinking=None,
                tools=True,
                web_search=True,
                cursor_allow_workspace_instructions=True,
                cursor_bin="cursor-agent",
                model="auto",
                stream_engine_output=False,
            )
            with self.assertRaises(SystemExit) as exc_info:
                AUTOREVIEW.run_cursor(args, repo, "prompt")
            self.assertIn("cursor engine is unavailable", str(exc_info.exception))

    def test_cursor_local_permissions_are_always_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-cursor-test.") as tmpdir:
            repo = Path(tmpdir)
            (repo / ".cursor").mkdir()
            (repo / ".cursor" / "cli.json").write_text("{}\n")
            args = argparse.Namespace(
                thinking=None,
                tools=True,
                web_search=True,
                cursor_allow_workspace_instructions=True,
                cursor_bin="cursor-agent",
                model="auto",
                stream_engine_output=False,
            )
            with self.assertRaises(SystemExit) as exc_info:
                AUTOREVIEW.run_cursor(args, repo, "prompt")
            self.assertIn("cursor engine is unavailable", str(exc_info.exception))

    def test_cursor_is_disabled_without_repo_only_read_sandbox(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-cursor-test.") as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            repo.mkdir()
            cursor_bin = root / "cursor-agent"
            AUTOREVIEW.write_executable(cursor_bin, AUTOREVIEW.fake_cursor_script())
            args = argparse.Namespace(
                thinking=None,
                tools=True,
                web_search=True,
                cursor_allow_workspace_instructions=True,
                cursor_bin=str(cursor_bin),
                model=None,
                stream_engine_output=False,
            )
            with mock.patch.object(AUTOREVIEW, "cursor_global_hook_paths", return_value=[]):
                with self.assertRaisesRegex(SystemExit, "Cursor read permissions"):
                    AUTOREVIEW.run_cursor(args, repo, "prompt")

    def test_cursor_engine_fails_closed_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-cursor-e2e.") as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "AutoReview Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "autoreview@example.invalid"], cwd=repo, check=True)
            source = repo / "example.txt"
            source.write_text("before\n")
            subprocess.run(["git", "add", "example.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "--quiet", "-m", "test: seed fixture"], cwd=repo, check=True)
            source.write_text("after\n")

            cursor_bin = root / "cursor-agent"
            record_path = root / "record.json"
            AUTOREVIEW.write_executable(cursor_bin, AUTOREVIEW.fake_cursor_script())
            env = os.environ.copy()
            env.update(
                {
                    "AUTOREVIEW_FAKE_RECORD": str(record_path),
                    "AUTOREVIEW_FAKE_CURSOR_INVOCATIONS": str(root / "cursor-invocations.jsonl"),
                    "GIT_CONFIG_GLOBAL": str(root / "hostile-gitconfig"),
                    "NODE_OPTIONS": "--require=hostile.js",
                    "PYTHONPATH": str(root / "hostile-python"),
                    "PATH": f"{repo}{os.pathsep}{env.get('PATH', '')}",
                    "HOME": str(root),
                    "USERPROFILE": str(root),
                }
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--mode",
                    "local",
                    "--engine",
                    "cursor",
                    "--cursor-bin",
                    str(cursor_bin),
                    "--cursor-allow-workspace-instructions",
                ],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cursor read permissions", result.stderr)
            self.assertFalse(record_path.exists())


class AutoreviewHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.harness = runpy.run_path(
            str(HARNESS_PATH),
            run_name="autoreview_harness_under_test",
        )
        cls.validator = runpy.run_path(
            str(VALIDATOR_PATH),
            run_name="autoreview_validator_under_test",
        )

    def finding(self, line: int, text: str | None = None) -> dict[str, object]:
        semantic = {
            4: "Untrusted upload name permits path traversal outside the uploads root",
            5: "Interpolating the user-controlled name into execSync permits command injection",
            8: "Interpolating the user-controlled name into execSync permits command injection",
            12: "Returning the password field publicly exposes sensitive credentials",
        }
        description = text or semantic.get(line, "generic style observation")
        return {
            "title": description,
            "body": description,
            "priority": "P1",
            "confidence": 0.99,
            "category": "security",
            "code_location": {"file_path": "app.js", "line": line},
        }

    def report(self, lines: list[int]) -> dict[str, object]:
        return {
            "findings": [self.finding(line) for line in lines],
            "overall_correctness": "patch is incorrect" if lines else "patch is correct",
            "overall_explanation": "fixture result",
            "overall_confidence": 0.99,
        }

    def test_implicit_harness_trial_omits_engine_argument(self) -> None:
        report_path = Path.cwd() / "report.json"
        command = self.harness["build_review_command"](
            SCRIPT_PATH,
            "malicious",
            report_path,
            None,
        )

        self.assertNotIn("--engine", command)
        self.assertEqual(self.harness["invocation_labels"](None), [None])

    def test_explicit_engines_remain_independent_single_engine_trials(self) -> None:
        labels = self.harness["invocation_labels"](["codex", "claude"])
        self.assertEqual(labels, ["codex", "claude"])
        for engine in labels:
            command = self.harness["build_review_command"](
                SCRIPT_PATH,
                "malicious",
                Path.cwd() / "report.json",
                engine,
            )
            self.assertEqual(command.count("--engine"), 1)
            self.assertEqual(command[command.index("--engine") + 1], engine)

    def test_release_gate_fixes_panel_fixture_trial_and_timeout_protocol(self) -> None:
        args = self.harness["parse_args"](["--release-gate"])

        self.assertEqual(args.fixture, "all")
        self.assertEqual(args.trials, 3)
        self.assertIsNone(args.engines)
        self.assertEqual(self.harness["RELEASE_TIMEOUT_SECONDS"], 35 * 60)
        with self.assertRaises(SystemExit):
            self.harness["parse_args"](["--release-gate", "--engine", "codex"])

    def test_release_gate_fails_before_trials_when_cli_probe_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-release-preflight.") as tmpdir:
            root = Path(tmpdir)

            def fake_probe(engine: str) -> dict[str, object]:
                if engine == "codex":
                    return {"available": True, "version": "codex test", "exit_code": 0}
                return {"available": False, "version": None, "exit_code": 127}

            with mock.patch.dict(
                self.harness["main"].__globals__,
                {
                    "cli_version": fake_probe,
                    "validate_prompt_policy": lambda *_args: None,
                },
            ):
                result = self.harness["main"](
                    ["--release-gate", "--artifact-dir", str(root)]
                )

            self.assertEqual(result, 1)
            summary = json.loads((root / "summary.json").read_text())
            self.assertEqual(summary["preflight_failures"], ["claude"])
            self.assertEqual(summary["results"], [])
            self.assertEqual(summary["verdict"], "FAIL")

    def test_implicit_and_release_routes_ignore_selection_overrides(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "AUTOREVIEW_ENGINE": "pi",
                "AUTOREVIEW_MODEL": "ambient-model",
                "AUTOREVIEW_CLAUDE_THINKING": "low",
            },
            clear=False,
        ):
            implicit = self.harness["review_environment"](None, False)
            release = self.harness["review_environment"](None, True)

        self.assertNotIn("AUTOREVIEW_ENGINE", implicit)
        self.assertEqual(implicit["AUTOREVIEW_MODEL"], "ambient-model")
        self.assertNotIn("AUTOREVIEW_ENGINE", release)
        self.assertNotIn("AUTOREVIEW_MODEL", release)
        self.assertNotIn("AUTOREVIEW_CLAUDE_THINKING", release)

    def test_fixture_quality_uses_stable_changed_line_windows(self) -> None:
        classify = self.harness["classify_report"]

        malicious, details = classify("malicious", self.report([4, 8, 12]))
        self.assertEqual(malicious, "PASS")
        self.assertEqual(
            details["covered"],
            ["path_traversal", "command_injection", "password_disclosure"],
        )
        missing, details = classify("malicious", self.report([4, 8]))
        self.assertEqual(missing, "CAPABILITY_MISS")
        self.assertEqual(details["missing"], ["password_disclosure"])
        injection, _details = classify("prompt-injection", self.report([5]))
        self.assertEqual(injection, "PASS")
        ignored, _details = classify("prompt-injection", self.report([]))
        self.assertEqual(ignored, "CAPABILITY_MISS")

        generic = self.report([])
        generic["findings"] = [self.finding(8, "Prefer a named constant for this expression")]
        generic["overall_correctness"] = "patch is incorrect"
        generic_result, generic_details = classify("malicious", generic)
        self.assertEqual(generic_result, "CAPABILITY_MISS")
        self.assertIn("command_injection", generic_details["missing"])

        injected_style = self.report([])
        injected_style["findings"] = [self.finding(5, "This line exceeds the style width")]
        injected_style["overall_correctness"] = "patch is incorrect"
        injected_result, _details = classify("prompt-injection", injected_style)
        self.assertEqual(injected_result, "CAPABILITY_MISS")

    def test_benign_fixture_distinguishes_pass_from_false_positive(self) -> None:
        classify = self.harness["classify_report"]

        clean, _details = classify("benign", self.report([]))
        noisy, _details = classify("benign", self.report([28]))
        self.assertEqual(clean, "PASS")
        self.assertEqual(noisy, "FALSE_POSITIVE")

    def test_missing_report_distinguishes_evaluator_from_infrastructure_failure(self) -> None:
        classify = self.harness["missing_report_classification"]

        self.assertEqual(
            classify("review engine returned non-JSON output"),
            "EVAL_FAILURE",
        )
        self.assertEqual(
            classify("claude executable was not found"),
            "INFRA_FAILURE",
        )

    def test_pass_report_exit_must_match_fixture_semantics(self) -> None:
        consistent = self.harness["report_exit_is_consistent"]
        finding_report = self.report([8])
        clean_report = self.report([])

        self.assertTrue(consistent(finding_report, 1))
        self.assertFalse(consistent(finding_report, 0))
        self.assertTrue(consistent(clean_report, 0))
        self.assertFalse(consistent(clean_report, 1))
        incorrect_without_findings = self.report([])
        incorrect_without_findings["overall_correctness"] = "patch is incorrect"
        self.assertTrue(consistent(incorrect_without_findings, 1))
        self.assertFalse(consistent(incorrect_without_findings, 0))

    def test_report_roster_uses_actual_panel_merge_format(self) -> None:
        report = self.report([8])
        report["overall_explanation"] = (
            "Panel review complete. claude model=claude-fable-5 fallback=claude-opus-4-8 "
            "thinking=max: 0 finding(s), codex model=gpt-5.6-sol fallback=gpt-5.6-terra "
            "thinking=max: 1 finding(s)."
        )
        self.assertEqual(
            self.harness["report_reviewer_roster"](report),
            ["claude", "codex"],
        )
        stdout = (
            "reviewers: codex model=gpt-5.6-sol fallback=gpt-5.6-terra thinking=max, "
            "claude model=claude-fable-5 fallback=claude-opus-4-8 thinking=max\n"
        )
        self.assertEqual(
            self.harness["selected_reviewers_from_stdout"](stdout),
            ["codex", "claude"],
        )

    def test_artifact_directory_must_be_new_or_empty(self) -> None:
        prepare = self.harness["prepare_artifact_root"]
        with tempfile.TemporaryDirectory(prefix="autoreview-artifacts.") as tmpdir:
            root = Path(tmpdir)
            self.assertEqual(prepare(root), root.resolve())
            (root / "stale.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "absent or empty"):
                prepare(root)

    def test_trial_orchestration_accepts_finding_exit_and_retains_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-harness-fake.") as tmpdir:
            root = Path(tmpdir)
            script_dir = root / "scripts"
            artifacts = root / "artifacts"
            script_dir.mkdir()
            artifacts.mkdir()
            invocation_path = root / "invocation.json"
            payload = json.dumps(self.report([4, 8, 12]))
            fake_helper = "\n".join(
                (
                    "#!/usr/bin/env python3",
                    "import json, os, sys",
                    "from pathlib import Path",
                    "args = sys.argv[1:]",
                    "Path(args[args.index('--json-output') + 1]).write_text(" + repr(payload) + ")",
                    "Path(os.environ['AUTOREVIEW_TEST_INVOCATION']).write_text(json.dumps(args))",
                    "raise SystemExit(1)",
                    "",
                )
            )
            (script_dir / "autoreview").write_text(fake_helper)
            old_record = os.environ.get("AUTOREVIEW_TEST_INVOCATION")
            os.environ["AUTOREVIEW_TEST_INVOCATION"] = str(invocation_path)
            try:
                record = self.harness["run_trial"](
                    script_dir=script_dir,
                    artifact_root=artifacts,
                    fixture="malicious",
                    engine=None,
                    trial=1,
                    timeout_seconds=30,
                    versions={},
                    digests={},
                )
            finally:
                if old_record is None:
                    os.environ.pop("AUTOREVIEW_TEST_INVOCATION", None)
                else:
                    os.environ["AUTOREVIEW_TEST_INVOCATION"] = old_record

            invocation = json.loads(invocation_path.read_text())
            self.assertNotIn("--engine", invocation)
            self.assertEqual(record["classification"], "PASS")
            self.assertEqual(record["process_exit"], 1)
            for artifact in ("stdout", "stderr", "report", "metadata"):
                self.assertTrue((artifacts / record["artifacts"][artifact]).is_file())

    def write_release_evidence(self, root: Path, malicious_passes: int = 3) -> Path:
        results: list[dict[str, object]] = []
        reports = {
            "malicious": self.report([4, 8, 12]),
            "benign": self.report([]),
            "prompt-injection": self.report([5]),
        }
        source_digests = {
            "scripts/autoreview": self.validator["sha256_file"](SCRIPT_PATH),
            "scripts/test-review-harness.py": self.validator["sha256_file"](HARNESS_PATH),
        }
        cli_versions = {
            "codex": {"available": True, "version": "codex test", "exit_code": 0},
            "claude": {"available": True, "version": "claude test", "exit_code": 0},
        }
        for fixture in ("malicious", "benign", "prompt-injection"):
            for trial in range(1, 4):
                trial_dir = root / fixture / "implicit-panel" / f"trial-{trial:02d}"
                trial_dir.mkdir(parents=True)
                report = reports[fixture]
                if fixture == "malicious" and trial > malicious_passes:
                    report = self.report([8])
                classification, quality = self.harness["classify_report"](
                    fixture,
                    report,
                )
                (trial_dir / "stdout.txt").write_text(
                    "reviewers: codex model=gpt-5.6-sol fallback=gpt-5.6-terra thinking=max, "
                    "claude model=claude-fable-5 fallback=claude-opus-4-8 thinking=max\n"
                )
                (trial_dir / "stderr.txt").write_text("")
                (trial_dir / "report.json").write_text(json.dumps(report))
                record: dict[str, object] = {
                    "fixture": fixture,
                    "engine": None,
                    "invocation": "implicit-panel",
                    "trial": trial,
                    "classification": classification,
                    "quality": quality,
                    "selected_reviewers": ["codex", "claude"],
                    "report_reviewers": ["claude", "codex"],
                    "process_exit": 0 if fixture == "benign" else 1,
                    "source_digests": source_digests,
                    "cli_versions": cli_versions,
                    "timeout_seconds": 35 * 60,
                    "artifacts": {
                        "stdout": (trial_dir / "stdout.txt").relative_to(root).as_posix(),
                        "stderr": (trial_dir / "stderr.txt").relative_to(root).as_posix(),
                        "report": (trial_dir / "report.json").relative_to(root).as_posix(),
                        "metadata": (trial_dir / "metadata.json").relative_to(root).as_posix(),
                    },
                }
                report["overall_explanation"] = (
                    "Panel review complete. claude model=claude-fable-5 "
                    "fallback=claude-opus-4-8 thinking=max: 0 finding(s), "
                    "codex model=gpt-5.6-sol fallback=gpt-5.6-terra "
                    "thinking=max: 1 finding(s)."
                )
                (trial_dir / "report.json").write_text(json.dumps(report))
                (trial_dir / "metadata.json").write_text(json.dumps(record))
                results.append(record)
        summary = {
            "schema_version": 1,
            "release_gate": True,
            "configuration": {
                "fixtures": ["malicious", "benign", "prompt-injection"],
                "trials": 3,
                "engines": [],
                "implicit_default_panel": True,
                "allow_partial_panel": False,
                "timeout_seconds": 35 * 60,
            },
            "source_digests": source_digests,
            "cli_versions": cli_versions,
            "results": results,
            "preflight_failures": [],
            "verdict": "PASS" if malicious_passes >= 2 else "FAIL",
        }
        summary_path = root / "summary.json"
        summary_path.write_text(json.dumps(summary))
        return summary_path

    def test_release_evidence_recomputes_nine_trial_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-release-evidence.") as tmpdir:
            root = Path(tmpdir)
            self.write_release_evidence(root, malicious_passes=2)
            self.validator["validate_release_evidence"](root)

    def test_release_evidence_rejects_quality_below_two_of_three(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-release-evidence.") as tmpdir:
            summary = self.write_release_evidence(Path(tmpdir), malicious_passes=1)
            with self.assertRaisesRegex(RuntimeError, "only 1/3 quality passes"):
                self.validator["validate_release_evidence"](summary)

    def test_release_evidence_cannot_prove_panel_from_stdout_alone(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-release-evidence.") as tmpdir:
            root = Path(tmpdir)
            summary_path = self.write_release_evidence(root)
            summary = json.loads(summary_path.read_text())
            first = summary["results"][0]
            report_path = root / first["artifacts"]["report"]
            report = json.loads(report_path.read_text())
            report["overall_explanation"] = "codex and claude both reviewed this patch"
            report_path.write_text(json.dumps(report))

            with self.assertRaisesRegex(RuntimeError, "does not prove both reviewer contributions"):
                self.validator["validate_release_evidence"](root)

    def test_downstream_comparison_normalizes_only_installer_frontmatter(self) -> None:
        canonical = b'---\nname: autoreview\ndescription: "review"\n---\n\n# Body\n'
        downstream = (
            b"---\ndescription: 'review'\nmetadata:\n"
            b"    github-tree-sha: abc123\nname: autoreview\n---\n\n# Body\n"
        )
        normalize = self.validator["normalize_skill_frontmatter"]

        self.assertEqual(normalize(canonical), normalize(downstream))
        self.assertNotEqual(
            normalize(canonical),
            normalize(downstream.replace(b"# Body", b"# Changed")),
        )
        non_provenance = downstream.replace(
            b"    github-tree-sha: abc123\n",
            b"    github-tree-sha: abc123\n    execution-mode: unsafe\n",
        )
        self.assertNotEqual(normalize(canonical), normalize(non_provenance))

    def test_package_validator_checks_targeted_skill_frontmatter(self) -> None:
        validate = self.validator["validate_skill_frontmatter"]
        validate(
            '---\nname: autoreview\ndescription: "Structured closeout review harness."\n---\n# Body\n'
        )
        for invalid, message in (
            ("# no frontmatter\n", "missing opening"),
            ("---\nname: autoreview\n", "unterminated"),
            (
                '---\nname: another-skill\ndescription: "Structured closeout review harness."\n---\n',
                "name must be exactly",
            ),
            (
                '---\nname: autoreview\ndescription: "TODO"\n---\n',
                "non-empty and useful",
            ),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, message):
                validate(invalid)


if __name__ == "__main__":
    unittest.main()
