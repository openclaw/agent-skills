#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
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


class AutoreviewPriorityTests(unittest.TestCase):
    def test_default_priority_is_p0(self) -> None:
        with mock.patch.object(sys, "argv", ["autoreview"]):
            args = AUTOREVIEW.parse_args()
        self.assertEqual(args.max_priority, "P0")

    def test_priority_filter_omits_lower_findings_and_cleans_verdict(self) -> None:
        report = copy.deepcopy(DRAFT_REPORT)
        AUTOREVIEW.filter_findings_by_priority(report, "P0")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["overall_correctness"], "patch is correct")
        self.assertIn("below the requested P0", report["overall_explanation"])


class AutoreviewSecretScannerTests(unittest.TestCase):
    def test_boolean_declarations_are_not_credential_material(self) -> None:
        secret_field = "is" + "Secret"
        client_secret_field = "hasClient" + "Secret"
        cases = (
            (f"val {secret_field}: Boolean? = null,", None),
            (f"var {client_secret_field}: Boolean = false", None),
            (f"abstract val {secret_field}: Boolean?", None),
            (f"val {secret_field}: Boolean?", None),
            (f"const {client_secret_field}: boolean = true;", "typescript"),
            (f"declare const {client_secret_field}: boolean;", "typescript"),
            (f"let {secret_field}: Bool? = nil", None),
            (f"let {secret_field}: Bool?", None),
        )

        for content, javascript_dialect in cases:
            with self.subTest(content=content):
                self.assertFalse(
                    AUTOREVIEW.secret_text_risk(
                        content,
                        javascript_dialect=javascript_dialect,
                    )
                )

    def test_boolean_and_null_literal_values_are_not_credentials(self) -> None:
        cases = (
            ("is" + "Secret", "true"),
            ("requires" + "Password", "false"),
            ("access" + "Token", "null"),
        )
        for field_name, literal in cases:
            content = f"{field_name} = {literal}"
            with self.subTest(content=content):
                self.assertFalse(AUTOREVIEW.secret_text_risk(content))

    def test_boolean_annotation_does_not_hide_real_credential_literal(self) -> None:
        literal_value = "actual-production-" + "secret"
        secret_field = "is" + "Secret"
        client_secret_field = "hasClient" + "Secret"
        cases = (
            (f'val {secret_field}: Boolean? = "{literal_value}",', None),
            (f'var {client_secret_field}: Boolean = "{literal_value}"', None),
            (
                f'const {client_secret_field}: boolean = "{literal_value}";',
                "typescript",
            ),
            (f'let {secret_field}: Bool? = "{literal_value}"', None),
        )

        for content, javascript_dialect in cases:
            with self.subTest(content=content):
                self.assertTrue(
                    AUTOREVIEW.secret_text_risk(
                        content,
                        javascript_dialect=javascript_dialect,
                    )
                )

    def test_boolean_prefix_values_remain_credentials(self) -> None:
        field_name = "client" + "Secret"
        for prefix in ("Boolean", "boolean", "Bool"):
            literal_value = prefix + "-prod-credential"
            content = f"{field_name}: {literal_value}"
            with self.subTest(content=content):
                self.assertTrue(AUTOREVIEW.secret_text_risk(content))

    def test_boolean_type_tokens_in_config_remain_credentials(self) -> None:
        field_name = "client" + "Secret"
        for literal_value in ("Boolean?", "Boolean?=abc1234"):
            content = f"{field_name}: {literal_value}"
            with self.subTest(content=content):
                self.assertTrue(AUTOREVIEW.secret_text_risk(content))


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
        harness_path = SCRIPT_PATH.with_name("test-review-harness.py")
        namespace = runpy.run_path(str(harness_path))
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

    def test_claude_auth_env_does_not_block_explicit_non_claude_engine(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"AUTOREVIEW_CLAUDE_AUTH": "subscription"},
            clear=False,
        ):
            with mock.patch.object(sys, "argv", ["autoreview", "--engine", "cursor"]):
                reviewers = AUTOREVIEW.reviewer_args(AUTOREVIEW.parse_args())
        self.assertEqual([reviewer.engine for reviewer in reviewers], ["cursor"])

    def test_explicit_claude_auth_rejects_non_claude_engine(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "autoreview",
                "--engine",
                "cursor",
                "--claude-auth",
                "subscription",
            ],
        ):
            args = AUTOREVIEW.parse_args()
        with self.assertRaisesRegex(SystemExit, "only supported for claude"):
            AUTOREVIEW.reviewer_args(args)

    def test_explicit_codex_auth_rejects_non_codex_engine(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "autoreview",
                "--engine",
                "claude",
                "--codex-auth",
                "chatgpt",
            ],
        ):
            args = AUTOREVIEW.parse_args()
        with self.assertRaisesRegex(SystemExit, "only supported for codex"):
            AUTOREVIEW.reviewer_args(args)

    def test_mixed_chatgpt_and_bedrock_auth_is_preserved(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "autoreview",
                "--panel",
                "--codex-auth",
                "chatgpt",
                "--claude-auth",
                "bedrock",
                "--claude-bedrock-region",
                "us-east-1",
            ],
        ):
            reviewers = AUTOREVIEW.reviewer_args(AUTOREVIEW.parse_args())
        self.assertEqual([reviewer.engine for reviewer in reviewers], ["codex", "claude"])
        self.assertEqual(reviewers[0].codex_auth, "chatgpt")
        self.assertEqual(reviewers[1].claude_auth, "bedrock")
        self.assertEqual(reviewers[1].claude_bedrock_region, "us-east-1")
        self.assertEqual(
            reviewers[1].model,
            "global.anthropic.claude-opus-4-8",
        )
        self.assertEqual(reviewers[1].thinking, "xhigh")

    def test_chatgpt_codex_defaults_to_fast_without_overriding_explicit_tier(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            implicit = AUTOREVIEW.reviewer_test_args(codex_auth="chatgpt")
            raw_tier = AUTOREVIEW.reviewer_test_args(
                codex_auth="chatgpt",
                codex_config=['service_tier="flex"'],
            )
            explicit = AUTOREVIEW.reviewer_test_args(
                codex_auth="chatgpt",
                codex_speed="default",
            )
            self.assertEqual(AUTOREVIEW.codex_speed_value(implicit), "fast")
            self.assertIsNone(AUTOREVIEW.codex_speed_override(raw_tier))
            self.assertEqual(AUTOREVIEW.codex_speed_value(raw_tier), "flex")
            self.assertEqual(AUTOREVIEW.codex_speed_value(explicit), "default")

    def test_codex_provider_profile_does_not_inherit_fast_default(self) -> None:
        args = AUTOREVIEW.reviewer_test_args(
            codex_auth="default",
            codex_profile="bedrock",
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(AUTOREVIEW.codex_speed_value(args))

    def test_run_telemetry_persists_private_bundle_report_and_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-telemetry-test.") as tempdir:
            root = Path(tempdir)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Test"],
                check=True,
            )
            (repo / "example.txt").write_text("example\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "example.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-m", "initial"],
                check=True,
            )
            logs = root / "logs"
            logs.mkdir(mode=0o755)
            logs.chmod(0o755)
            args = AUTOREVIEW.reviewer_test_args(
                codex_auth="chatgpt",
                model="gpt-5.6-sol",
                thinking="high",
                fallback_model="gpt-5.6-terra",
                web_search=True,
                stream_engine_output=False,
                parallel_tests=None,
                run_log_dir=str(logs),
                log_bundle=True,
            )
            telemetry = AUTOREVIEW.RunTelemetry(
                args,
                repo,
                "branch",
                "origin/main",
                [args],
            )
            self.assertEqual(logs.stat().st_mode & 0o777, 0o755)
            self.assertEqual((logs / "runs").stat().st_mode & 0o777, 0o700)
            args.run_telemetry = telemetry
            telemetry.record_bundle(
                "diff --git a/example.txt b/example.txt\n",
                truncated=False,
                changed_paths={"example.txt"},
                prompts=["review prompt"],
            )
            reviewer_id = telemetry.start_reviewer(args)
            attempt_id = telemetry.start_attempt(args)
            telemetry.finish_attempt(attempt_id, status="completed", returncode=0)
            telemetry.finish_reviewer(reviewer_id, status="completed", findings=0)
            telemetry.record_result(FINAL_REPORT, tests_status=0, outcome="clean")
            telemetry.finish(0)

            metadata = json.loads(telemetry.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["reviewers"][0]["speed_requested"], "fast")
            self.assertEqual(metadata["bundle"]["changed_paths"], ["example.txt"])
            self.assertEqual(metadata["attempts"][0]["status"], "completed")
            self.assertEqual(metadata["result"]["outcome"], "clean")
            self.assertEqual((telemetry.run_dir / "bundle.txt").read_text(), "diff --git a/example.txt b/example.txt\n")
            self.assertTrue((telemetry.run_dir / "report.json").is_file())
            history = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH.with_name("autoreview-history")),
                    "--log-dir",
                    str(logs),
                    "--json",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            summary = json.loads(history.stdout)
            self.assertEqual(summary["runs"], 1)
            self.assertEqual(
                summary["configurations"][0]["speed_requested"],
                "fast",
            )

            args.log_bundle = False
            metadata_only = AUTOREVIEW.RunTelemetry(
                args,
                repo,
                "branch",
                "origin/main",
                [args],
            )
            metadata_only.record_result(
                FINAL_REPORT,
                tests_status=0,
                outcome="clean",
            )
            metadata_only.finish(0)
            self.assertFalse((metadata_only.run_dir / "report.json").exists())
            self.assertEqual(
                json.loads(metadata_only.metadata_path.read_text())["artifacts"],
                {"metadata": "metadata.json"},
            )

    def test_run_log_root_rejects_paths_inside_reviewed_repo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-log-root-test.") as tempdir:
            repo = Path(tempdir).resolve()
            args = argparse.Namespace(run_log_dir=str(repo / "review-history"))
            with self.assertRaisesRegex(SystemExit, "must be outside"):
                AUTOREVIEW.run_log_root(args, repo)

    def test_implicit_history_root_falls_back_outside_home_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-home-repo-test.") as tempdir:
            root = Path(tempdir).resolve()
            repo = root / "home-repo"
            fallback_parent = root / "system-temp"
            repo.mkdir()
            (repo / ".git").mkdir()
            fallback_parent.mkdir()
            args = argparse.Namespace(run_log_dir=None)
            with (
                mock.patch.object(Path, "home", return_value=repo),
                mock.patch.object(tempfile, "gettempdir", return_value=str(fallback_parent)),
                mock.patch.dict(os.environ, {}, clear=True),
            ):
                history_root = AUTOREVIEW.run_log_root(args, repo)
                (history_root / "runs").mkdir(parents=True)
                history = runpy.run_path(
                    str(SCRIPT_PATH.with_name("autoreview-history"))
                )
                reader_root = history["default_log_dir"]()
            self.assertTrue(history_root.is_relative_to(fallback_parent))
            self.assertFalse(history_root.is_relative_to(repo))
            self.assertEqual(reader_root, history_root)

    def test_history_runs_directory_must_not_overlap_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-log-overlap-test.") as tempdir:
            root = Path(tempdir).resolve()
            repo = root / "runs"
            repo.mkdir()
            args = argparse.Namespace(run_log_dir=str(root))
            with self.assertRaisesRegex(SystemExit, "must be outside"):
                AUTOREVIEW.run_log_root(args, repo)

    def test_existing_history_directory_must_not_be_shared_writable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-history-mode-test.") as tempdir:
            shared = Path(tempdir) / "shared"
            shared.mkdir(mode=0o777)
            shared.chmod(0o777)
            with self.assertRaisesRegex(SystemExit, "group/world-writable"):
                AUTOREVIEW.ensure_private_directory(shared)
            self.assertEqual(shared.stat().st_mode & 0o777, 0o777)

    def test_codex_setup_failure_finishes_telemetry_attempt(self) -> None:
        args = AUTOREVIEW.reviewer_test_args(
            codex_bin="codex",
            codex_auth="chatgpt",
            model="gpt-5.6-sol",
            thinking="high",
            fallback_model=None,
        )
        telemetry = mock.Mock(spec=AUTOREVIEW.RunTelemetry)
        telemetry.start_attempt.return_value = 7
        args.run_telemetry = telemetry
        with tempfile.TemporaryDirectory(prefix="autoreview-codex-setup-test.") as tempdir, (
            mock.patch.object(
                AUTOREVIEW,
                "prepare_codex_runtime_auth",
                return_value=False,
            )
        ), mock.patch.object(
            AUTOREVIEW,
            "prepare_codex_runtime_profile",
            return_value=False,
        ), mock.patch.object(
            AUTOREVIEW,
            "codex_source_home",
            return_value=None,
        ), mock.patch.object(
            AUTOREVIEW,
            "codex_command",
            side_effect=OSError("setup failed"),
        ):
            with self.assertRaisesRegex(OSError, "setup failed"):
                AUTOREVIEW.run_codex(args, Path(tempdir), "review")
        telemetry.finish_attempt.assert_called_once_with(7, status="failed")

    def test_bundle_history_is_opt_in(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(
                AUTOREVIEW.run_log_bundle_enabled(
                    argparse.Namespace(log_bundle=None)
                )
            )
            os.environ["AUTOREVIEW_RUN_LOG_BUNDLE"] = "1"
            self.assertTrue(
                AUTOREVIEW.run_log_bundle_enabled(
                    argparse.Namespace(log_bundle=None)
                )
            )
            self.assertFalse(
                AUTOREVIEW.run_log_bundle_enabled(
                    argparse.Namespace(log_bundle=False)
                )
            )
            os.environ["AUTOREVIEW_RUN_LOG_BUNDLE"] = "typo"
            with self.assertRaisesRegex(SystemExit, "invalid AUTOREVIEW_RUN_LOG_BUNDLE"):
                AUTOREVIEW.run_log_bundle_enabled(
                    argparse.Namespace(log_bundle=None)
                )

    def test_default_history_setup_falls_back_without_failing_review(self) -> None:
        args = AUTOREVIEW.reviewer_test_args(run_log_dir=None, log_bundle=False)
        fallback = mock.Mock(strict=True)
        with mock.patch.object(
            AUTOREVIEW,
            "RunTelemetry",
            side_effect=[OSError("read only"), fallback],
        ) as constructor:
            result = AUTOREVIEW.create_run_telemetry(
                args,
                Path("/repo"),
                "local",
                None,
                [args],
            )
        self.assertIs(result, fallback)
        self.assertFalse(fallback.strict)
        self.assertEqual(constructor.call_count, 2)

    def test_default_history_fallback_does_not_follow_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-history-symlink-test.") as tempdir:
            root = Path(tempdir)
            state_home = root / "blocked-state-home"
            state_home.write_text("not a directory", encoding="utf-8")
            fallback_parent = root / "system-temp"
            fallback_parent.mkdir()
            target = root / "owned-target"
            target.mkdir()
            fallback = fallback_parent / f"autoreview-state-{os.getuid()}"
            fallback.symlink_to(target, target_is_directory=True)
            args = AUTOREVIEW.reviewer_test_args(
                run_log_dir=None,
                log_bundle=False,
            )
            with (
                mock.patch.object(
                    AUTOREVIEW.tempfile,
                    "gettempdir",
                    return_value=str(fallback_parent),
                ),
                mock.patch.dict(
                    os.environ,
                    {"XDG_STATE_HOME": str(state_home)},
                    clear=True,
                ),
            ):
                telemetry = AUTOREVIEW.create_run_telemetry(
                    args,
                    root / "repo",
                    "local",
                    None,
                    [args],
                )
            self.assertIsNone(telemetry)
            self.assertFalse((target / "runs").exists())

    def test_explicit_history_setup_failure_remains_strict(self) -> None:
        args = AUTOREVIEW.reviewer_test_args(
            run_log_dir="/explicit/history",
            log_bundle=False,
        )
        with mock.patch.object(
            AUTOREVIEW,
            "RunTelemetry",
            side_effect=OSError("read only"),
        ), self.assertRaisesRegex(OSError, "read only"):
            AUTOREVIEW.create_run_telemetry(
                args,
                Path("/repo"),
                "local",
                None,
                [args],
            )

    def test_default_history_write_failure_disables_logging_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-history-write-test.") as tempdir:
            repo = Path(tempdir) / "repo"
            repo.mkdir()
            args = AUTOREVIEW.reviewer_test_args(
                run_log_dir=str(Path(tempdir) / "history"),
                log_bundle=False,
            )
            telemetry = AUTOREVIEW.RunTelemetry(
                args,
                repo,
                "local",
                None,
                [args],
                strict=False,
            )
            with mock.patch.object(
                AUTOREVIEW,
                "atomic_write_text",
                side_effect=OSError("read only"),
            ):
                attempt_id = telemetry.start_attempt(args)
            self.assertEqual(attempt_id, 1)
            self.assertFalse(telemetry.logging_available)

    def test_explicit_history_write_failure_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-history-write-test.") as tempdir:
            repo = Path(tempdir) / "repo"
            repo.mkdir()
            args = AUTOREVIEW.reviewer_test_args(
                run_log_dir=str(Path(tempdir) / "history"),
                log_bundle=False,
            )
            telemetry = AUTOREVIEW.RunTelemetry(
                args,
                repo,
                "local",
                None,
                [args],
                strict=True,
            )
            with mock.patch.object(
                AUTOREVIEW,
                "atomic_write_text",
                side_effect=OSError("read only"),
            ), self.assertRaisesRegex(OSError, "read only"):
                telemetry.start_attempt(args)

    def test_telemetry_finalization_is_idempotent_after_strict_write_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autoreview-history-finish-test.") as tempdir:
            repo = Path(tempdir) / "repo"
            repo.mkdir()
            args = AUTOREVIEW.reviewer_test_args(
                run_log_dir=str(Path(tempdir) / "history"),
                log_bundle=False,
            )
            telemetry = AUTOREVIEW.RunTelemetry(
                args,
                repo,
                "local",
                None,
                [args],
                strict=True,
            )
            attempt_id = telemetry.start_attempt(args)
            reviewer_id = telemetry.start_reviewer(args)
            with mock.patch.object(
                AUTOREVIEW,
                "atomic_write_text",
                side_effect=OSError("read only"),
            ):
                with self.assertRaisesRegex(OSError, "read only"):
                    telemetry.finish_attempt(attempt_id, status="completed")
                telemetry.finish_attempt(attempt_id, status="failed")
                with self.assertRaisesRegex(OSError, "read only"):
                    telemetry.finish_reviewer(reviewer_id, status="completed")
                telemetry.finish_reviewer(reviewer_id, status="failed")

    def test_pi_records_model_attempt_separately_from_review_validation(self) -> None:
        args = AUTOREVIEW.reviewer_test_args(
            engine="pi",
            model="openai/gpt-4o",
            thinking="high",
        )
        telemetry = mock.Mock(spec=AUTOREVIEW.RunTelemetry)
        telemetry.start_attempt.return_value = 3
        args.run_telemetry = telemetry
        with tempfile.TemporaryDirectory(prefix="autoreview-pi-telemetry-test.") as tempdir, (
            mock.patch.object(
                AUTOREVIEW,
                "ensure_pi_isolation_supported",
                return_value="pi",
            )
        ), mock.patch.object(
            AUTOREVIEW,
            "safe_temp_root",
            return_value=tempdir,
        ), mock.patch.object(
            AUTOREVIEW,
            "run_with_heartbeat",
            return_value=subprocess.CompletedProcess(["pi"], 0, "{}", ""),
        ):
            self.assertEqual(AUTOREVIEW.run_pi(args, Path(tempdir), "review"), "{}")
        telemetry.start_attempt.assert_called_once_with(args)
        telemetry.finish_attempt.assert_called_once_with(
            3,
            status="completed",
            returncode=0,
        )

    def test_history_uses_reviewer_runs_for_pi_and_preserves_inherited_speed(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        summary = history["summarize"](
            [
                {
                    "status": "completed",
                    "result": {"outcome": "clean"},
                    "attempts": [
                        {
                            "engine": "codex",
                            "model": "gpt-5.6-sol",
                            "thinking": "high",
                            "auth": "default",
                            "profile": None,
                            "speed_requested": None,
                            "pass": 1,
                            "status": "completed",
                            "duration_seconds": 2.0,
                            "reason": "primary",
                            "refusal": False,
                        }
                    ],
                    "reviewer_runs": [
                        {
                            "engine": "codex",
                            "model": "gpt-5.6-sol",
                            "thinking": "high",
                            "auth": "default",
                            "profile": None,
                            "speed_requested": None,
                            "pass": 1,
                            "status": "failed",
                            "duration_seconds": 2.1,
                        },
                        {
                            "engine": "pi",
                            "model": "openai/gpt-4o",
                            "thinking": "high",
                            "pass": 1,
                            "status": "completed",
                            "duration_seconds": 3.0,
                        }
                    ],
                }
            ],
            None,
        )
        by_engine = {
            row["engine"]: row for row in summary["configurations"]
        }
        self.assertEqual(
            by_engine["codex"]["speed_requested"],
            "inherited",
        )
        self.assertEqual(by_engine["codex"]["completed"], 1)
        self.assertEqual(by_engine["codex"]["review_failures"], 1)
        self.assertEqual(by_engine["pi"]["attempts"], 0)
        self.assertEqual(by_engine["pi"]["review_completed"], 1)
        self.assertEqual(by_engine["pi"]["speed_requested"], "n/a")

    def test_history_loads_runs_by_high_resolution_start_time(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        with tempfile.TemporaryDirectory(prefix="autoreview-history-order-test.") as tempdir:
            root = Path(tempdir)
            for directory, run_id, started in (
                ("z-random", "newer", 20),
                ("a-random", "older", 10),
            ):
                run_dir = root / "runs" / directory
                run_dir.mkdir(parents=True)
                (run_dir / "metadata.json").write_text(
                    json.dumps(
                        {
                            "run_id": run_id,
                            "started_at_unix_ns": started,
                        }
                    ),
                    encoding="utf-8",
                )
            runs = history["load_runs"](root)
            self.assertEqual([run["run_id"] for run in runs], ["older", "newer"])

    def test_history_reader_detects_repository_below_default_runs_root(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        with tempfile.TemporaryDirectory(prefix="autoreview-history-fallback-test.") as tempdir:
            root = Path(tempdir).resolve()
            state_home = root / "state"
            repo = state_home / "autoreview" / "runs" / "project"
            fallback_parent = root / "system-temp"
            (repo / ".git").mkdir(parents=True)
            fallback = fallback_parent / f"autoreview-state-{os.getuid()}"
            (fallback / "runs").mkdir(parents=True)
            with (
                mock.patch.object(Path, "cwd", return_value=repo),
                mock.patch.object(
                    tempfile,
                    "gettempdir",
                    return_value=str(fallback_parent),
                ),
                mock.patch.dict(
                    os.environ,
                    {"XDG_STATE_HOME": str(state_home)},
                    clear=True,
                ),
            ):
                resolved = history["default_log_dir"]()
            self.assertTrue(resolved.is_relative_to(fallback_parent))

    def test_history_reader_uses_populated_fallback_when_default_is_unavailable(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        with tempfile.TemporaryDirectory(prefix="autoreview-history-reader-test.") as tempdir:
            root = Path(tempdir)
            home = root / "home"
            fallback_parent = root / "system-temp"
            fallback = fallback_parent / f"autoreview-state-{os.getuid()}"
            (fallback / "runs").mkdir(parents=True)
            home.mkdir()
            with (
                mock.patch.object(Path, "home", return_value=home),
                mock.patch.object(
                    history["tempfile"],
                    "gettempdir",
                    return_value=str(fallback_parent),
                ),
                mock.patch.dict(os.environ, {}, clear=True),
            ):
                resolved = history["default_log_dir"]()
            self.assertEqual(resolved, fallback.resolve())

    def test_history_reader_rejects_insecure_default_before_preferring_it(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        with tempfile.TemporaryDirectory(prefix="autoreview-history-reader-test.") as tempdir:
            root = Path(tempdir)
            state_home = root / "state"
            candidate = state_home / "autoreview"
            fallback_parent = root / "system-temp"
            fallback = fallback_parent / f"autoreview-state-{os.getuid()}"
            (candidate / "runs").mkdir(parents=True)
            candidate.chmod(0o775)
            (fallback / "runs").mkdir(parents=True)
            with (
                mock.patch.object(
                    history["tempfile"],
                    "gettempdir",
                    return_value=str(fallback_parent),
                ),
                mock.patch.dict(
                    os.environ,
                    {"XDG_STATE_HOME": str(state_home)},
                    clear=True,
                ),
            ):
                resolved = history["default_log_dir"]()
            self.assertEqual(resolved, fallback.resolve())

    def test_history_reader_ignores_untrusted_implicit_fallback(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        with tempfile.TemporaryDirectory(prefix="autoreview-history-reader-test.") as tempdir:
            root = Path(tempdir)
            home = root / "home"
            fallback_parent = root / "system-temp"
            fallback = fallback_parent / f"autoreview-state-{os.getuid()}"
            home.mkdir()
            (fallback / "runs").mkdir(parents=True)
            fallback.chmod(0o777)
            with (
                mock.patch.object(Path, "home", return_value=home),
                mock.patch.object(
                    history["tempfile"],
                    "gettempdir",
                    return_value=str(fallback_parent),
                ),
                mock.patch.dict(os.environ, {}, clear=True),
            ):
                self.assertEqual(history["default_log_dirs"](), [])

    def test_history_reader_does_not_follow_implicit_fallback_symlink(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        with tempfile.TemporaryDirectory(prefix="autoreview-history-reader-test.") as tempdir:
            root = Path(tempdir)
            home = root / "home"
            fallback_parent = root / "system-temp"
            target = root / "owned-target"
            fallback = fallback_parent / f"autoreview-state-{os.getuid()}"
            home.mkdir()
            (target / "runs").mkdir(parents=True)
            fallback_parent.mkdir()
            fallback.symlink_to(target, target_is_directory=True)
            with (
                mock.patch.object(Path, "home", return_value=home),
                mock.patch.object(
                    history["tempfile"],
                    "gettempdir",
                    return_value=str(fallback_parent),
                ),
                mock.patch.dict(os.environ, {}, clear=True),
            ):
                self.assertEqual(history["default_log_dirs"](), [])

    def test_history_reader_merges_default_and_fallback_runs(self) -> None:
        history = runpy.run_path(str(SCRIPT_PATH.with_name("autoreview-history")))
        with tempfile.TemporaryDirectory(prefix="autoreview-history-merge-test.") as tempdir:
            root = Path(tempdir)
            default = root / "default"
            fallback = root / "fallback"
            for history_root, run_id, started in (
                (default, "default-run", 20),
                (fallback, "fallback-run", 10),
            ):
                run_dir = history_root / "runs" / run_id
                run_dir.mkdir(parents=True)
                (run_dir / "metadata.json").write_text(
                    json.dumps(
                        {
                            "run_id": run_id,
                            "started_at_unix_ns": started,
                        }
                    ),
                    encoding="utf-8",
                )
            runs = history["load_run_roots"]([default, fallback])
            self.assertEqual(
                [run["run_id"] for run in runs],
                ["fallback-run", "default-run"],
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
            trufflehog_bin = root / "trufflehog"
            record_path = root / "record.json"
            AUTOREVIEW.write_executable(cursor_bin, AUTOREVIEW.fake_cursor_script())
            AUTOREVIEW.write_executable(
                trufflehog_bin,
                "#!/usr/bin/env python3\nraise SystemExit(0)\n",
            )
            env = os.environ.copy()
            env.update(
                {
                    "AUTOREVIEW_FAKE_RECORD": str(record_path),
                    "AUTOREVIEW_FAKE_CURSOR_INVOCATIONS": str(root / "cursor-invocations.jsonl"),
                    "GIT_CONFIG_GLOBAL": str(root / "hostile-gitconfig"),
                    "NODE_OPTIONS": "--require=hostile.js",
                    "PYTHONPATH": str(root / "hostile-python"),
                    "PATH": (
                        f"{root}{os.pathsep}{repo}{os.pathsep}"
                        f"{env.get('PATH', '')}"
                    ),
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


if __name__ == "__main__":
    unittest.main()
