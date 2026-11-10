from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from .test_autoreview_hardening import init_repo, load_helper, write_executable


class CodexInferenceRouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="autoreview-route-test.")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = init_repo(self.root)
        self.home = self.root / "operator-home"
        self.home.mkdir()
        self.runtime_helper = write_executable(
            self.home / "credential-helper", "#!/bin/sh\nexit 99\n"
        )
        self.catalogue = self.home / "models.json"
        self.catalogue_bytes = json.dumps({
            "models": [{
                "slug": "gpt-6.1-sol", "context_window": 120000,
                "max_context_window": 120000, "auto_compact_token_limit": 90000,
                "display_name": "Synthetic model", "supported_reasoning_levels": [],
                "shell_type": "unified_exec", "visibility": "list",
                "supported_in_api": True, "priority": 0, "support_verbosity": False,
                "truncation_policy": {"mode": "tokens", "limit": 10000},
                "experimental_supported_tools": [],
                "model_messages": {"instructions_template": "synthetic instructions"},
            }],
        }).encode()
        self.catalogue.write_bytes(self.catalogue_bytes)
        self.config = {
            "model_provider": "review_api",
            "model_catalog_json": str(self.catalogue),
            "model_context_window": 120000,
            "model_auto_compact_token_limit": 90000,
            "model_auto_compact_token_limit_scope": "total",
            "cli_auth_credentials_store": "file",
        }
        self.provider = {
            "name": "Synthetic review API", "base_url": "https://api.openai.com/v1",
            "wire_api": "responses", "requires_openai_auth": False,
        }
        self.auth = {
            "command": str(self.runtime_helper), "timeout_ms": 5000,
            "refresh_interval_ms": 300000,
        }
        self.helper = load_helper()
        self.args = argparse.Namespace(
            engine="codex", codex_bin="synthetic-codex", codex_config=['model_provider="review_api"'], codex_speed=None,
            fallback_model=None, model="gpt-6-sol", stream_engine_output=False,
            thinking="high", tools=True, web_search=False,
        )
        self.environment = mock.patch.dict(os.environ, {
            "CODEX_HOME": str(self.home), "HOME": str(self.root),
            "AUTOREVIEW_CODEX_CONFIG": "", "AUTOREVIEW_CODEX_SPEED": "",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_config(self):
        def value(item):
            if isinstance(item, dict):
                return "{" + ", ".join(f"{json.dumps(key)}={value(part)}" for key, part in item.items()) + "}"
            return json.dumps(item, ensure_ascii=False)

        def table(values):
            return "\n".join(f"{key} = {value(item)}" for key, item in values.items())

        text = table(self.config)
        text += "\n[model_providers.review_api]\n" + table(self.provider)
        if self.auth is not None:
            text += "\n[model_providers.review_api.auth]\n" + table(self.auth)
        for identifier, provider in getattr(self, "extra_providers", {}).items():
            text += f"\n[model_providers.{identifier}]\n" + table(provider)
        # These unrelated operator capabilities must never enter the review runtime.
        text += '\n[mcp_servers.unrelated]\ncommand = "must-not-execute"\n'
        (self.home / "config.toml").write_text(text, encoding="utf-8")

    def run_review(self, *, prepare_auth=None, during_run=None):
        observed = {}

        def fake_run(command, cwd, **kwargs):
            observed["command"] = command
            observed["cwd"] = cwd
            observed["workspace"] = list(cwd.iterdir())
            observed["env"] = kwargs["env"]
            observed["stream_display"] = kwargs["stream_display"]
            flags = [command[index + 1] for index, value in enumerate(command) if value == "-c"]
            observed["flags"] = dict(flag.split("=", 1) for flag in flags)
            auth_command = observed["flags"].get("model_providers.review_api.auth.command")
            if auth_command:
                launcher = Path(tomllib.loads(f"value = {auth_command}")["value"])
                observed["auth_command"] = launcher
                auth_args = observed["flags"].get("model_providers.review_api.auth.args")
                if auth_args:
                    observed["auth_args"] = tomllib.loads("value=" + auth_args)["value"]
                else:
                    observed["auth_launcher_text"] = launcher.read_text(encoding="utf-8")
            catalogue = observed["flags"].get("model_catalog_json")
            if catalogue:
                file = Path(json.loads(catalogue))
                observed["catalogue"] = file.read_bytes()
                observed["catalogue_path"] = file
            if during_run:
                result = during_run(observed)
                if result is not None:
                    return result
            output = Path(command[command.index("--output-last-message") + 1])
            output.write_text('{"findings": []}')
            return subprocess.CompletedProcess(command, 0, "", "")

        replacements = {
            "ensure_codex_isolation_supported": mock.Mock(return_value="synthetic-codex"),
            "resolve_command": mock.Mock(return_value="synthetic-codex"),
            "run_with_heartbeat": fake_run,
        }
        if prepare_auth is not None:
            replacements["prepare_codex_runtime_auth"] = prepare_auth
        with mock.patch.dict(self.helper["run_codex"].__globals__, replacements):
            observed["report"] = self.helper["run_codex"](self.args, self.repo, "synthetic review")
        return observed

    def assert_auth_command(self, observed, executable):
        if os.name == "nt":
            self.assertEqual(observed["auth_command"], executable.resolve())
        else:
            self.assertNotEqual(observed["auth_command"], executable.resolve())
            self.assertIn(f"exec {shlex.quote(str(executable.resolve()))}\n", observed["auth_launcher_text"])

    def test_trusted_route_reaches_client_without_workspace_or_config_capabilities(self):
        self.write_config()
        observed = self.run_review()
        flags = observed["flags"]
        self.assertEqual(flags.get("model_provider"), '"review_api"')
        self.assertEqual(flags.get("model_providers.review_api.base_url"), '"https://api.openai.com/v1"')
        self.assert_auth_command(observed, self.runtime_helper)
        auth_cwd = tomllib.loads(f'value = {flags["model_providers.review_api.auth.cwd"]}')["value"]
        self.assertEqual(auth_cwd, str(self.home.resolve()))
        self.assertEqual(flags.get("model_providers.review_api.auth.timeout_ms"), "5000")
        self.assertEqual(flags.get("model_providers.review_api.auth.refresh_interval_ms"), "300000")
        self.assertEqual(flags.get("model_context_window"), "120000")
        self.assertEqual(flags.get("model_auto_compact_token_limit"), "90000")
        self.assertEqual(observed["catalogue"], self.catalogue_bytes)
        self.assertNotEqual(observed["catalogue_path"], self.catalogue)
        self.assertFalse(observed["catalogue_path"].is_relative_to(observed["cwd"]))
        self.assertEqual(observed["workspace"], [])
        self.assertIn("--ignore-user-config", observed["command"])
        self.assertIn("--ignore-rules", observed["command"])
        self.assertNotIn("mcp_servers.unrelated.command", flags)
        self.assertEqual(flags["features.hooks"], "false")
        self.assertEqual(flags["features.plugins"], "false")
        self.assertEqual(flags["default_permissions"], '"autoreview"')
        self.assertEqual(observed["command"][observed["command"].index("--model") + 1], self.args.model)
        self.assertEqual(observed["command"][observed["command"].index("--ask-for-approval") + 1], "never")
        self.assertFalse(observed["cwd"].exists())
        self.assertFalse(observed["catalogue_path"].exists())
        if os.name != "nt":
            self.assertFalse(observed["auth_command"].exists())

    def available(self):
        replacements = {
            "find_command": mock.Mock(return_value="synthetic-codex"),
            "ENGINE_ISOLATION_PROBES": {"codex": mock.Mock()},
        }
        with (
            mock.patch.dict(self.helper["resolve_engine_binary"].__globals__, replacements),
            mock.patch("tempfile.TemporaryDirectory", side_effect=AssertionError("preflight must not create runtime state")),
            mock.patch("subprocess.run", side_effect=AssertionError("preflight must not execute credentials or reviewer")),
        ):
            return self.helper["resolve_engine_binary"](self.args, self.repo)

    def test_https_gateway_base_url_reaches_client_unchanged(self):
        for base_url in (
            "https://gateway.example.invalid/v1",
            "https://gateway.example.invalid:8443/inference/v1/",
            "https://[::1]:8443/v1",
            "https://gateway.example.invalid",
            "HTTPS://Gateway.Example.Invalid/v1/%23responses",
        ):
            with self.subTest(base_url=base_url):
                self.provider["base_url"] = base_url
                self.args.model = "openai/gpt-6.1-sol"
                self.write_config()
                observed = self.run_review()
                flags = observed["command"]
                key = "model_providers.review_api.base_url="
                self.assertEqual(
                    [flags[index + 1] for index, part in enumerate(flags)
                     if part == "-c" and flags[index + 1].startswith(key)],
                    [key + json.dumps(base_url)],
                )
                self.assertEqual(flags[flags.index("--model") + 1], self.args.model)
                self.assertEqual(observed["report"], '{"findings": []}')
                self.assertEqual(self.available(), (True, None))

    def test_invalid_base_url_refuses_in_run_and_preflight(self):
        for base_url in (
            "http://gateway.example.invalid/v1", "http://127.0.0.1/v1",
            "https://user:password@gateway.example.invalid/v1",
            "https://user@gateway.example.invalid/v1",
            "https://@gateway.example.invalid/v1",
            "https://gateway.example.invalid/v1?key=synthetic",
            "https://gateway.example.invalid/v1#fragment",
            "https://gateway.example.invalid/v1?", "https://gateway.example.invalid/v1#",
            "not-a-url", "", "//gateway.example.invalid/v1", "https:///v1",
            "https://", "https://[invalid/v1",
            "https://gateway.example.invalid:bad/v1",
            "https://gateway.example.invalid:65536/v1",
            "https://gateway.example.invalid:0/v1",
            "https://gateway.example.invalid:/v1",
            " https://gateway.example.invalid/v1",
            "https://gateway.example.invalid/v1\n",
            "https://gate way.example.invalid/v1",
            "https://gateway.example.invalid\\other/v1",
            "https://gateway.example.invalid/v1/%invalid",
            "https://gate%20way.example.invalid/v1",
            "https://gateway.example.invalid%2fother/v1",
            42, False, [], {},
        ):
            with self.subTest(base_url=base_url):
                self.provider["base_url"] = base_url
                self.write_config()
                self.assert_route_refused()
        self.provider.pop("base_url")
        self.write_config()
        self.assert_route_refused()

    def assert_route_refused(self):
        prepare_auth = mock.Mock()
        with self.assertRaisesRegex(SystemExit, "inference|Codex config") as caught:
            self.run_review(prepare_auth=prepare_auth)
        prepare_auth.assert_not_called()
        self.assertEqual(self.available(), (False, str(caught.exception.code)))

    def use_default_models(self):
        args = copy.copy(self.args)
        args.model, args.thinking, args.fallback_model = [], [], []
        with mock.patch.dict(self.helper["reviewer_args"].__globals__, {
            "env_defaults_for": lambda _: (None, {}),
        }):
            self.args = self.helper["reviewer_args"](args)[0]

    def test_primary_only_catalogue_keeps_normal_fallback_and_frozen_route(self):
        self.use_default_models()
        self.write_config()
        original = self.catalogue_bytes
        events = []
        launchers = []

        def respond(observed):
            command = observed["command"]
            selected = command[command.index("--model") + 1]
            events.append(selected)
            self.assertEqual(observed["flags"].get("model_provider"), '"review_api"')
            self.assertEqual(observed["catalogue"], original)
            self.assert_auth_command(observed, self.runtime_helper)
            launchers.append(observed["auth_command"])
            if selected == "gpt-6.1-sol":
                # A retry keeps the prepared route even if operator files change.
                self.catalogue.write_bytes(b"changed after primary send")
                (self.home / "config.toml").write_text('model_provider = "another-route"')
                return subprocess.CompletedProcess(
                    command, 1, "", "The model gpt-6.1-sol does not exist or you do not have access to it.",
                )

        self.run_review(during_run=respond)
        self.assertEqual(events, ["gpt-6.1-sol", "gpt-6-sol"])
        self.assertEqual(launchers[0], launchers[1])

    def test_primary_only_catalogue_does_not_block_successful_primary(self):
        self.use_default_models()
        self.write_config()
        attempts = []
        self.run_review(during_run=lambda observed: attempts.append(observed["command"]))
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0][attempts[0].index("--model") + 1], "gpt-6.1-sol")
        self.assertEqual(self.available(), (True, None))

    def test_default_keeps_legacy_auth_only_behavior_with_unrelated_routes(self):
        self.args.codex_config = []
        for provider in ("openai", "review_api", "unsupported-provider"):
            for without_parser in (False, True):
                with self.subTest(provider=provider, without_parser=without_parser):
                    self.config.update({
                        "model_provider": provider, "profile": "operator-profile",
                        "openai_base_url": "https://example.invalid/operator",
                        "forced_login_method": "api",
                    })
                    self.provider["base_url"] = "https://example.invalid/custom"
                    self.write_config()
                    modules = {"tomllib": None, "tomli": None} if without_parser else {}
                    with (
                        mock.patch.dict(sys.modules, modules),
                        mock.patch.dict(os.environ, {"HOME": str(self.repo)}),
                        mock.patch.dict(self.helper["run_codex"].__globals__, {
                            "codex_auth_helper_home": mock.Mock(side_effect=AssertionError("default route must not validate helper HOME")),
                        }),
                    ):
                        observed = self.run_review()
                        self.assertEqual(observed["flags"]["cli_auth_credentials_store"], '"file"')
                        self.assertEqual(observed["flags"]["forced_login_method"], '"api"')
                        for key in (
                            "model_provider", "model_catalog_json", "model_context_window",
                            "model_auto_compact_token_limit", "model_auto_compact_token_limit_scope",
                            "profile", "openai_base_url", "model_providers.review_api.auth.command",
                        ):
                            self.assertNotIn(key, observed["flags"])
                        self.assertEqual(self.available(), (True, None))

    def test_tuning_override_alone_does_not_select_operator_route(self):
        self.args.codex_config = ["model_context_window=240000"]
        self.write_config()
        observed = self.run_review()
        self.assertEqual(observed["flags"]["model_context_window"], "240000")
        self.assertNotIn("model_provider", observed["flags"])
        self.assertNotIn("model_catalog_json", observed["flags"])
        self.assertEqual(self.available(), (True, None))

    def test_projection_requires_explicit_matching_provider_selector(self):
        self.write_config()
        for selector in ('review_api', '"review_api"', "'review_api'"):
            with self.subTest(selector=selector):
                self.args.codex_config = [f"model_provider = {selector}"]
                observed = self.run_review()
                provider_flags = [part for part in observed["command"] if part.startswith("model_provider=")]
                self.assertEqual(provider_flags, ['model_provider="review_api"'])
                self.assertEqual(observed["catalogue"], self.catalogue_bytes)
                self.assertEqual(self.available(), (True, None))

    def test_provider_selector_rejects_mismatch_and_nonliteral_values(self):
        self.write_config()
        for selector in (
            '"other"', '["review_api"]', '{id="review_api"}',
            '"review_api"\nfeatures.hooks=true', '"review_api" # comment',
            '"review\\u005fapi"', '""',
        ):
            with self.subTest(selector=selector):
                self.args.codex_config = [f"model_provider={selector}"]
                self.assert_route_refused()
        self.args.codex_config = ['model_provider="review_api"', 'model_provider="other"']
        self.assert_route_refused()
        self.args.codex_config = ['model_provider="review_api"']
        del self.config["model_provider"]
        self.write_config()
        self.assert_route_refused()

    def test_optional_route_fields_keep_native_defaults_when_omitted(self):
        context = ("model_context_window", "model_auto_compact_token_limit", "model_auto_compact_token_limit_scope")
        original_config, original_auth, original_provider = copy.deepcopy(self.config), copy.deepcopy(self.auth), copy.deepcopy(self.provider)
        for absent in (("timeout_ms", "refresh_interval_ms"), ("name", "wire_api", "requires_openai_auth"), context, (*context, "model_catalog_json", "timeout_ms", "refresh_interval_ms")):
            with self.subTest(absent=absent):
                self.config, self.auth, self.provider = copy.deepcopy(original_config), copy.deepcopy(original_auth), copy.deepcopy(original_provider)
                self.auth["args"] = []
                for key in absent:
                    self.config.pop(key, None)
                    self.auth.pop(key, None)
                    self.provider.pop(key, None)
                self.write_config()
                observed = self.run_review()
                self.assertEqual(observed["flags"]["model_provider"], '"review_api"')
                for key in absent:
                    flag = (f"model_providers.review_api.auth.{key}" if key in {"timeout_ms", "refresh_interval_ms"}
                            else f"model_providers.review_api.{key}" if key in {"name", "wire_api", "requires_openai_auth"}
                            else key)
                    self.assertNotIn(flag, observed["flags"])
                self.assertEqual(self.available(), (True, None))

    def test_conflicting_or_malformed_operator_route_refuses_in_run_and_preflight(self):
        original = copy.deepcopy(self.config)
        for config in (
            {**original, "profile": "another-route"},
            {**original, "openai_base_url": "https://example.invalid/v1"},
        ):
            with self.subTest(config=config):
                self.config = config
                self.write_config()
                self.assert_route_refused()
        for contents in (b"model_provider = [", b"\xff"):
            with self.subTest(contents=contents):
                (self.home / "config.toml").write_bytes(contents)
                self.assert_route_refused()

    def test_unsafe_route_descriptor_is_never_forwarded(self):
        provider = copy.deepcopy(self.provider)
        auth = copy.deepcopy(self.auth)
        cases = [
            ("provider", {**provider, "http_headers": {"Authorization": "synthetic"}}),
            ("provider", {**provider, "requires_openai_auth": True}),
            ("provider", {**provider, "requires_openai_auth": "false"}),
            ("provider", {**provider, "wire_api": "chat"}),
            ("auth", {**auth, "command": "credential-helper"}),
            ("auth", {**auth, "args": ["synthetic-credential"]}),
            ("auth", {**auth, "cwd": str(self.repo)}),
            ("auth", {**auth, "cwd": "../repo"}),
            ("auth", {**auth, "timeout_ms": True}),
            ("auth", {**auth, "refresh_interval_ms": -1}),
        ]
        for target, values in cases:
            with self.subTest(target=target, values=values):
                self.provider, self.auth = copy.deepcopy(provider), copy.deepcopy(auth)
                setattr(self, target, values)
                self.write_config()
                self.assert_route_refused()

    def test_catalogue_preserves_native_metadata_and_context_semantics(self):
        document = json.loads(self.catalogue_bytes)
        model = document["models"][0]
        model["max_context_window"] = 240000
        del model["auto_compact_token_limit"]
        model["base_instructions"] = model.pop("model_messages")["instructions_template"]
        # Codex supports a larger maximum and legacy instruction metadata.
        # The helper must forward these bytes without applying another schema.
        self.catalogue_bytes = json.dumps(document, indent=2).encode() + b"\n"
        self.catalogue.write_bytes(self.catalogue_bytes)
        self.write_config()
        observed = self.run_review()
        self.assertEqual(observed["catalogue"], self.catalogue_bytes)
        self.assertEqual(observed["flags"]["model_context_window"], "120000")
        self.assertEqual(self.available(), (True, None))

    def test_catalogue_path_must_be_external(self):
        repo_catalogue = self.repo / "models.json"
        repo_catalogue.write_bytes(self.catalogue_bytes)
        self.config["model_catalog_json"] = str(repo_catalogue)
        self.write_config()
        self.assert_route_refused()

    def test_explicit_projection_requires_toml_parser(self):
        self.write_config()
        with mock.patch.dict(sys.modules, {"tomllib": None, "tomli": None}):
            self.assert_route_refused()

    def test_relative_catalogue_and_auth_cwd_use_the_operator_config_directory(self):
        working_dir = self.home / "credential files"
        working_dir.mkdir()
        self.config["model_catalog_json"] = "models.json"
        for cwd, expected in ((".", self.home), (working_dir.name, working_dir)):
            with self.subTest(cwd=cwd):
                self.auth["cwd"] = cwd
                self.write_config()
                observed = self.run_review()
                auth_cwd = tomllib.loads(f'value = {observed["flags"]["model_providers.review_api.auth.cwd"]}')["value"]
                self.assertEqual(auth_cwd, str(expected.resolve()))
                self.assertEqual(observed["catalogue"], self.catalogue_bytes)
                self.assertEqual(self.available(), (True, None))
        repo_catalogue = self.repo / "models.json"
        repo_catalogue.write_bytes(self.catalogue_bytes)
        self.config["model_catalog_json"] = "../repo/models.json"
        self.write_config()
        self.assert_route_refused()

    def test_configured_executable_is_preserved_including_platform_wrapper(self):
        executable = write_executable(self.home / "credential tool", "#!/usr/bin/env python3\nraise SystemExit(99)\n")
        self.auth["command"] = str(executable)
        self.write_config()
        observed = self.run_review()
        self.assert_auth_command(observed, executable)
        self.auth["command"] = executable.name
        self.write_config()
        self.assert_route_refused()

    def test_non_bmp_route_paths_round_trip_through_toml_overrides(self):
        executable = write_executable(self.home / "credential-🦞", "#!/bin/sh\nexit 99\n")
        working_dir = self.home / "working-🦞"
        working_dir.mkdir()
        self.auth.update(command=str(executable), cwd=str(working_dir))
        self.write_config()
        observed = self.run_review()
        self.assert_auth_command(observed, executable)

        runtime = self.root / "runtime-🦞"
        runtime.mkdir()
        catalogue_flags = self.helper["prepare_codex_inference_config"](
            ([], self.catalogue_bytes), runtime,
        )
        key, value = catalogue_flags[-1].split("=", 1)
        flags = {**observed["flags"], key: value}
        expected = {
            "model_providers.review_api.auth.command": observed["auth_command"],
            "model_providers.review_api.auth.cwd": working_dir,
            "model_catalog_json": runtime / "model-catalog.json",
        }
        for key, path in expected.items():
            with self.subTest(key=key):
                parsed = tomllib.loads(f"value = {flags[key]}")["value"]
                self.assertEqual(parsed, str(path.resolve()))
        self.assertEqual((runtime / "model-catalog.json").read_bytes(), self.catalogue_bytes)

    def test_repository_owned_route_files_refuse_before_authentication(self):
        for name in ("config.toml", "models.json", self.runtime_helper.name):
            with self.subTest(name=name):
                self.write_config()
                source = self.home / name
                original = source.read_bytes()
                repo_file = self.repo / name
                repo_file.write_bytes(original)
                repo_file.chmod(0o755)
                source.unlink()
                try:
                    try:
                        source.symlink_to(repo_file)
                    except OSError as exc:
                        if getattr(exc, "winerror", None) != 1314:  # ERROR_PRIVILEGE_NOT_HELD
                            raise
                        self.skipTest("Windows symlink privilege is unavailable")
                    self.assert_route_refused()
                finally:
                    source.unlink(missing_ok=True)
                    source.write_bytes(original)
                    source.chmod(0o755)

        with mock.patch.dict(os.environ, {"CODEX_HOME": str(self.repo)}):
            self.assert_route_refused()

    def test_context_override_cannot_split_projected_route(self):
        self.args.codex_config.append("model_context_window=240000")
        self.write_config()
        self.assert_route_refused()

    def test_builtin_provider_collision_does_not_silently_change_route(self):
        for provider in ("openai", "ollama", "lmstudio", "amazon-bedrock", "amazon-bedrock-runtime"):
            with self.subTest(provider=provider):
                self.write_config()
                config = self.home / "config.toml"
                config.write_text(config.read_text().replace("review_api", provider))
                self.args.codex_config = [f'model_provider="{provider}"']
                self.assert_route_refused()

    def test_route_does_not_link_subscription_auth_or_change_original_configuration(self):
        self.write_config()
        source_auth = self.home / "auth.json"
        source_auth.write_text('{"fixture": "before"}')
        config_before = (self.home / "config.toml").read_bytes()

        def inspect(observed):
            home = Path(observed["env"]["CODEX_HOME"])
            self.assertNotEqual(home, self.home)
            self.assertFalse((home / "auth.json").exists())
            self.assertEqual(observed["flags"].get("cli_auth_credentials_store"), '"file"')

        prepare_auth = mock.Mock(side_effect=AssertionError("must not link subscription auth"))
        observed = self.run_review(prepare_auth=prepare_auth, during_run=inspect)
        self.assertEqual(observed["flags"].get("model_provider"), '"review_api"')
        self.assertEqual(json.loads(source_auth.read_text()), {"fixture": "before"})
        self.assertEqual((self.home / "config.toml").read_bytes(), config_before)

    @unittest.skipIf(os.name == "nt", "POSIX auth helper launcher")
    def test_launcher_restores_only_helper_home_with_literal_paths(self):
        weird = " ' \" $(not-a-command) `not-a-command` ; & 🦞"
        caller_home = self.root / ("caller" + weird)
        caller_home.mkdir()
        working_dir = self.home / ("working" + weird)
        working_dir.mkdir()
        executable = write_executable(
            self.home / ("helper" + weird),
            f"#!{sys.executable}\nimport json, os, sys\n"
            "print(json.dumps({'env': dict(os.environ), 'cwd': os.getcwd(), 'args': sys.argv[1:]}))\n",
        )
        self.auth.update(command=str(executable), cwd=str(working_dir), args=[])
        self.write_config()
        originals = {path: path.read_bytes() for path in (self.home / "config.toml", self.catalogue, executable)}

        def execute(observed):
            launcher = observed["auth_command"]
            runtime = Path(observed["env"]["HOME"]).parent
            self.assertEqual(launcher.parent, runtime)
            self.assertEqual(stat.S_IMODE(launcher.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(runtime.stat().st_mode), 0o700)
            self.assertEqual(launcher.stat().st_uid, os.getuid())
            self.assertFalse(launcher.is_relative_to(observed["cwd"]))
            self.assertFalse(launcher.is_relative_to(self.repo))
            before = dict(observed["env"])
            cwd = tomllib.loads(f'value = {observed["flags"]["model_providers.review_api.auth.cwd"]}')["value"]
            result = subprocess.run([str(launcher)], cwd=cwd, env=before, capture_output=True, text=True, check=True)
            actual = json.loads(result.stdout)
            self.assertEqual(actual["env"]["HOME"], str(caller_home.resolve()))
            for key, value in before.items():
                if key not in {"HOME", "PWD", "SHLVL", "_"}:
                    self.assertEqual(actual["env"].get(key), value, key)
            self.assertEqual(actual["cwd"], str(working_dir.resolve()))
            self.assertEqual(actual["args"], [])
            self.assertNotEqual(before["HOME"], str(caller_home.resolve()))
            self.assertEqual(observed["env"], before)
            self.assertEqual(list(observed["cwd"].iterdir()), [])
            flags = observed["flags"]
            self.assertEqual(flags["shell_environment_policy.set"], self.helper["toml_inline_string_table"](self.helper["codex_tool_git_env"]()))
            filesystem = flags["permissions.autoreview.filesystem"]
            for private_path in (caller_home, runtime, executable):
                self.assertNotIn(str(private_path), filesystem)
            self.assertEqual(flags["model_providers.review_api.auth.timeout_ms"], "5000")
            self.assertEqual(flags["model_providers.review_api.auth.refresh_interval_ms"], "300000")

        with mock.patch.dict(os.environ, {"HOME": str(caller_home)}):
            observed = self.run_review(during_run=execute)
        self.assert_auth_command(observed, executable)
        self.assertEqual({path: path.read_bytes() for path in originals}, originals)

    @unittest.skipIf(os.name == "nt", "POSIX auth helper launcher")
    def test_staged_launcher_path_uses_toml_unicode_encoder(self):
        self.write_config()
        runtime = self.root / "runtime ' \" 🦞"
        runtime.mkdir(mode=0o700)
        workspace = self.root / "workspace"
        workspace.mkdir()
        with mock.patch.dict(self.helper["codex_command"].__globals__, {"resolve_command": lambda *_: "synthetic-codex"}):
            command = self.helper["codex_command"](
                self.args, self.repo, workspace, runtime, runtime / "schema", runtime / "output", self.args.model,
            )
        flags = [command[index + 1] for index, part in enumerate(command) if part == "-c"]
        flag = next(value for value in flags if value.startswith("model_providers.review_api.auth.command="))
        launcher = Path(tomllib.loads("value=" + flag.partition("=")[2])["value"])
        self.assertEqual(launcher.parent, runtime)
        self.assertIn(f"exec {shlex.quote(str(self.runtime_helper.resolve()))}\n", launcher.read_text())

    @unittest.skipIf(os.name == "nt", "POSIX auth helper HOME validation")
    def test_unsafe_home_refused_in_run_and_dry_run_without_auth(self):
        self.write_config()
        external = self.root / "external"
        external.mkdir()
        repo_exit = self.repo / "exit-link"
        repo_exit.symlink_to(external, target_is_directory=True)
        final_link = self.root / "final-link"
        final_link.symlink_to(self.repo, target_is_directory=True)
        chain = self.root / "chain"
        chain.symlink_to(repo_exit, target_is_directory=True)
        loop = self.root / "loop"
        loop.symlink_to(loop)
        for home in (
            str(self.repo), str(repo_exit), str(final_link), str(final_link / "exit-link"),
            str(chain), str(self.repo / ".." / "external"), str(loop),
            str(self.root / "missing"), str(self.catalogue), "relative-home", "",
        ):
            with self.subTest(home=home), mock.patch.dict(os.environ, {"HOME": home}):
                self.args.dry_run = True
                self.assert_route_refused()

    def test_command_auth_failures_expose_only_fixed_categories(self):
        self.write_config()
        cases = {
            "provider-auth-helper": "provider auth command failed",
            "model-catalogue": "failed reading model_catalog_json",
            "model-sandbox-policy": "requires a sandbox with reviewed escalations",
            "cli-arguments": "unexpected argument",
            "configuration": "Error parsing config: missing field",
            "authentication": "HTTP 401 Unauthorized",
            "provider-access": "HTTP 403 Forbidden",
            "rate-limit": "HTTP 429 Too Many Requests",
            "transport": "connection refused",
            "unclassified": "unrecognized synthetic failure",
        }
        for category, diagnostic in cases.items():
            for stream in ("stdout", "stderr"):
                with self.subTest(category=category, stream=stream):
                    def fail(observed):
                        result = subprocess.CompletedProcess(observed["command"], 1, "", "")
                        setattr(result, stream, diagnostic + "\nsynthetic-private-diagnostic\x1b[31m")
                        return result

                    with self.assertRaises(SystemExit) as caught:
                        self.run_review(during_run=fail)
                    diagnostics = "authentication" if category == "authentication" and stream == "stderr" else "provider"
                    self.assertEqual(str(caught.exception), f"codex engine failed: {category}; {diagnostics} diagnostics suppressed")

    def test_command_auth_stream_hides_diagnostics_but_preserves_progress_and_report(self):
        self.write_config()
        self.args.stream_engine_output = True
        marker = "synthetic-private-diagnostic"

        def stream(observed):
            display = observed["stream_display"]
            for name, line in (
                ("stderr", marker), ("stdout", marker), ("stdout", '"' + marker + '"'),
                ("stdout", "[]"), ("stdout", "null"),
                ("stdout", json.dumps({"type": "error", "message": marker})),
                ("stdout", json.dumps({"type": "turn.failed", "error": {"message": marker}})),
            ):
                self.assertNotIn(marker, display(name, line) or "")
            self.assertIn("turn started", display("stdout", '{"type":"turn.started"}'))
            usage = display("stdout", '{"type":"turn.completed","usage":{"input_tokens":2,"output_tokens":1}}')
            self.assertIn("input_tokens=2", usage)
            report = '{"findings": []}'
            self.assertIn(report, display("stdout", json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": report}})))

        self.assertEqual(self.run_review(during_run=stream)["report"], '{"findings": []}')

    def test_command_auth_missing_report_and_failed_retry_do_not_return_diagnostics(self):
        self.write_config()
        marker = "synthetic-private-diagnostic"
        for stream_output in (False, True):
            for empty in ("", " \n"):
                with self.subTest(stream_output=stream_output, empty=empty):
                    self.args.stream_engine_output = stream_output
                    def no_report(observed):
                        command = observed["command"]
                        Path(command[command.index("--output-last-message") + 1]).write_text(empty)
                        return subprocess.CompletedProcess(command, 0, marker, marker)

                    with self.assertRaises(SystemExit) as caught:
                        self.run_review(during_run=no_report)
                    self.assertEqual(str(caught.exception), "codex engine failed: missing-report; provider diagnostics suppressed")

        self.use_default_models()
        attempts = []
        def fail_retry(observed):
            attempts.append(observed["command"])
            diagnostic = (f"The model {self.args.model} does not exist or you do not have access to it."
                          if len(attempts) == 1 else "provider auth command failed")
            return subprocess.CompletedProcess(observed["command"], 1, marker, diagnostic + "\n" + marker)

        console = io.StringIO()
        with contextlib.redirect_stderr(console), self.assertRaises(SystemExit) as caught:
            self.run_review(during_run=fail_retry)
        self.assertEqual(len(attempts), 2)
        self.assertNotIn(marker, console.getvalue())
        self.assertEqual(str(caught.exception), "codex engine failed: provider-auth-helper; provider diagnostics suppressed")

    def test_default_route_keeps_diagnostic_streaming_and_stdout_fallback(self):
        self.args.codex_config = []
        self.args.stream_engine_output = True
        self.write_config()
        marker = "synthetic-default-diagnostic"

        def respond(observed):
            for name in ("stdout", "stderr"):
                self.assertIn(marker, observed["stream_display"](name, marker))
            return subprocess.CompletedProcess(observed["command"], returncode, marker, marker)

        returncode = 0
        self.assertEqual(self.run_review(during_run=respond)["report"], marker)
        returncode = 1
        with self.assertRaises(SystemExit) as caught:
            self.run_review(during_run=respond)
        self.assertIn(marker, str(caught.exception))


@unittest.skipIf(os.name == "nt", "hostname route requires POSIX ownership checks")
class CodexHostnameRouteTests(unittest.TestCase):
    setUp = CodexInferenceRouteTests.setUp
    write_config = CodexInferenceRouteTests.write_config
    run_review = CodexInferenceRouteTests.run_review
    available = CodexInferenceRouteTests.available
    assert_route_refused = CodexInferenceRouteTests.assert_route_refused
    use_default_models = CodexInferenceRouteTests.use_default_models

    def configure(self):
        self.args.codex_config = []
        self.args.codex_route = ["gateway.example.invalid"]
        self.auth = None
        self.token = "synthetic-host-route-credential/+=="
        self.provider.update({
            "base_url": "https://Gateway.Example.Invalid.:8443/inference/v1/%23responses/",
            "experimental_bearer_token": self.token,
            "supports_websockets": True,
            "supports_standalone_web_search": False,
            "request_max_retries": 2, "stream_max_retries": 3, "stream_idle_timeout_ms": 120000,
        })
        self.write_config()

    def test_hostname_binds_full_endpoint_and_token_without_other_credentials_or_capabilities(self):
        self.configure()
        source_auth = self.home / "auth.json"
        source_auth.write_text('{"OPENAI_API_KEY":"synthetic-other-login"}')
        before = {path: path.read_bytes() for path in (source_auth, self.home / "config.toml", self.catalogue)}
        self.args.stream_engine_output = True
        token_path = None

        def inspect(observed):
            nonlocal token_path
            flags = observed["flags"]
            self.assertEqual(json.loads(flags["model_providers.review_api.base_url"]), self.provider["base_url"])
            for key in ("supports_websockets", "supports_standalone_web_search", "request_max_retries",
                        "stream_max_retries", "stream_idle_timeout_ms"):
                self.assertEqual(tomllib.loads("value=" + flags[f"model_providers.review_api.{key}"])["value"], self.provider[key])
            args = observed["auth_args"]
            self.assertEqual(args[:2], ["-I", "-S"])
            helper = Path(args[2])
            token_path = helper.with_name("route-token")
            self.assertEqual(stat.S_IMODE(token_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(token_path.parent.stat().st_mode), 0o700)
            self.assertFalse(helper.is_relative_to(observed["cwd"]))
            result = subprocess.run([str(observed["auth_command"]), *args], env=observed["env"],
                                    cwd=helper.parent, capture_output=True, check=True)
            self.assertEqual(result.stdout.decode(), self.token)
            self.assertEqual(result.stderr, b"")
            self.assertNotIn(self.token, repr(observed["command"]))
            self.assertNotIn(self.token, repr(observed["env"]))
            self.assertNotIn(self.token, helper.read_text())
            for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "AZURE_OPENAI_API_KEY",
                        "AZURE_OPENAI_ENDPOINT", "OPENAI_PROJECT", "OPENAI_ORGANIZATION"):
                self.assertNotIn(key, observed["env"])
            self.assertEqual(observed["workspace"], [])
            self.assertFalse((Path(observed["env"]["CODEX_HOME"]) / "auth.json").exists())
            self.assertEqual(flags["cli_auth_credentials_store"], '"file"')
            self.assertNotIn("forced_login_method", flags)
            self.assertIn("--ignore-user-config", observed["command"])
            self.assertEqual(flags["features.hooks"], "false")
            self.assertEqual(flags["features.plugins"], "false")
            self.assertEqual(flags["default_permissions"], '"autoreview"')
            self.assertEqual(observed["catalogue"], self.catalogue_bytes)
            self.assertFalse(any(key.startswith("mcp_servers") for key in flags))

        self.config["forced_login_method"] = "chatgpt"
        self.write_config()
        before[self.home / "config.toml"] = (self.home / "config.toml").read_bytes()
        env = {key: "synthetic-unrelated" for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL",
               "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "OPENAI_PROJECT", "OPENAI_ORGANIZATION")}
        with mock.patch.dict(os.environ, env), mock.patch.dict(self.helper["run_codex"].__globals__, {
            "load_codex_auth_fallback_route": mock.Mock(side_effect=AssertionError("no provider fallback")),
        }):
            observed = self.run_review(prepare_auth=mock.Mock(side_effect=AssertionError("no auth.json")), during_run=inspect)
        self.assertFalse(token_path.exists())
        self.assertFalse(observed["cwd"].exists())
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(self.available(), (True, None))

    def test_exact_normalized_hostname_not_active_provider_or_machine_hostname(self):
        self.configure()
        self.config["model_provider"] = "another_provider"
        self.extra_providers = {"another_provider": {"base_url": "https://other.example.invalid/v1"}}
        for selector, endpoint in (
            ("GATEWAY.EXAMPLE.INVALID.", self.provider["base_url"]),
            ("xn--bcher-kva.example", "https://BÜCHER.example/v1"),
            ("bücher.example.", "https://xn--bcher-kva.example/v1"),
            ("gateway.example.invalid", "https://%67ateway.example.invalid/v1"),
            ("::1", "https://[0:0:0:0:0:0:0:1]:8443/v1"),
            ("127.0.0.1", "https://127.0.0.1:8443/v1"),
        ):
            with self.subTest(selector=selector):
                self.args.codex_route = [selector]
                self.provider["base_url"] = endpoint
                self.write_config()
                observed = self.run_review()
                self.assertEqual(json.loads(observed["flags"]["model_providers.review_api.base_url"]), endpoint)
                self.assertEqual(observed["flags"]["model_provider"], '"review_api"')

    def test_malformed_missing_and_ambiguous_hosts_fail_without_auth_or_fallback(self):
        self.configure()
        for selector in ("", " gateway.example.invalid", "gateway.example.invalid\n", "https://gateway.example.invalid",
                         "gateway.example.invalid:443", "user@gateway.example.invalid", "gateway.example.invalid/path",
                         "*.example.invalid", ".example.invalid", "gateway..invalid", "bad_host", "-bad.invalid",
                         "bad-.invalid", "a" * 64 + ".invalid", "gateway.example.invalid?", "gateway.example.invalid#",
                         "gate%77ay.example.invalid", "[::1]", "gateway.example.invalid..", "bad\x00host"):
            with self.subTest(selector=selector):
                self.args.codex_route = [selector]
                self.assert_route_refused()
        # IDNA2003-only mappings must not conflate the client's distinct hosts.
        self.args.codex_route = ["faß.example"]
        self.assert_route_refused()
        self.provider["base_url"] = "https://faß.example/v1"
        self.args.codex_route = ["fass.example"]
        self.write_config()
        self.assert_route_refused()
        self.provider["base_url"] = "https://gateway.example.invalid/v1"
        for selector in ("example.invalid", "gateway.example.invalid.evil", "other.gateway.example.invalid"):
            with self.subTest(missing=selector):
                self.args.codex_route = [selector]
                self.assert_route_refused()
        self.args.codex_route = ["gateway.example.invalid"]
        self.extra_providers = {"duplicate": {"base_url": "https://gateway.example.invalid/different-path"}}
        self.write_config()
        self.assert_route_refused()

    def test_conflicts_include_repeat_selectors_environment_provider_and_split_context(self):
        self.configure()
        self.args.codex_route *= 2
        self.assert_route_refused()
        self.args.codex_route = ["gateway.example.invalid"]
        for overrides in (["model_provider=review_api"], ["model_provider=other"], ["model_context_window=123"]):
            with self.subTest(overrides=overrides):
                self.args.codex_config = overrides
                self.assert_route_refused()
        self.args.codex_config = []
        with mock.patch.dict(os.environ, {"AUTOREVIEW_CODEX_CONFIG": "model_provider=review_api"}):
            self.assert_route_refused()
        self.args.codex_config = ["model_verbosity='low'"]
        self.assertEqual(self.available(), (True, None))

    def test_unsupported_authentication_and_connection_shapes_never_degrade_to_other_auth(self):
        self.configure()
        original = copy.deepcopy(self.provider)
        for extra in (
            {"experimental_bearer_token": ""}, {"experimental_bearer_token": None},
            {"experimental_bearer_token": 42}, {"experimental_bearer_token": "bad\ntoken"},
            {"experimental_bearer_token": "bad token"}, {"requires_openai_auth": True},
            {"env_key": "OPENAI_API_KEY"}, {"http_headers": {"Authorization": "synthetic"}},
            {"env_http_headers": {"Authorization": "SYNTHETIC"}}, {"auth": {"command": str(self.runtime_helper)}},
            {"wire_api": "chat"}, {"supports_websockets": "true"}, {"supports_standalone_web_search": 1},
            {"request_max_retries": -1}, {"stream_idle_timeout_ms": True}, {"query_params": {"key": "value"}},
        ):
            with self.subTest(fields=list(extra)):
                self.provider = {**original, **extra}
                # JSON null is not TOML; write a literal wrong type instead.
                if self.provider.get("experimental_bearer_token", 0) is None:
                    self.provider["experimental_bearer_token"] = []
                self.write_config()
                self.assert_route_refused()
        self.provider = original
        self.provider.pop("experimental_bearer_token")
        self.write_config()
        self.assert_route_refused()

    def test_regression_legacy_projection_cannot_use_configured_bearer_provider(self):
        self.configure()
        self.args.codex_route = None
        self.args.codex_config = ['model_provider="review_api"']
        self.assert_route_refused()
        self.args.codex_config = []
        observed = self.run_review()
        self.assertNotIn("model_provider", observed["flags"])
        self.args.codex_route = ["gateway.example.invalid"]
        self.assertEqual(self.available(), (True, None))

    def test_matched_endpoint_safety_and_unsupported_types_fail_without_public_values(self):
        self.configure()
        original = self.provider["base_url"]
        for endpoint in (
            "http://gateway.example.invalid/v1", "https://user@gateway.example.invalid/v1",
            "https://gateway.example.invalid:invalid/v1", "https://gateway.example.invalid:0/v1",
            "https://gateway.example.invalid/v1?", "https://gateway.example.invalid/v1#",
            "https://gateway.example.invalid/v1/%invalid", "https://gateway.example.invalid/v1\n",
        ):
            with self.subTest(endpoint=endpoint):
                self.provider["base_url"] = endpoint
                self.write_config()
                self.assert_route_refused()
        self.provider["base_url"] = original
        self.config["model_context_window"] = {"malformed": self.token}
        self.write_config()
        with self.assertRaises(SystemExit) as caught:
            self.run_review()
        self.assertNotIn(self.token, str(caught.exception))

    def test_model_retry_keeps_one_frozen_endpoint_token_and_catalogue_and_records_usage(self):
        self.configure()
        self.use_default_models()
        original_endpoint, original_token, original_catalogue = self.provider["base_url"], self.token, self.catalogue_bytes
        attempts = []
        self.args.review_usage = []
        def respond(observed):
            attempts.append(observed["command"])
            flags = observed["flags"]
            self.assertEqual(json.loads(flags["model_providers.review_api.base_url"]), original_endpoint)
            self.assertEqual(Path(observed["auth_args"][2]).with_name("route-token").read_text(), original_token)
            self.assertEqual(observed["catalogue"], original_catalogue)
            self.provider.update(base_url="https://gateway.example.invalid/changed", experimental_bearer_token="synthetic-replacement")
            self.catalogue.write_text('{"models":[]}')
            self.write_config()
            usage = json.dumps({"type": "turn.completed", "usage": {
                "input_tokens": 5, "cached_input_tokens": 1, "output_tokens": 2, "reasoning_output_tokens": 1,
            }})
            if len(attempts) == 1:
                return subprocess.CompletedProcess(observed["command"], 1, usage,
                    f"The model {self.args.model} does not exist or you do not have access to it.")
            Path(observed["command"][observed["command"].index("--output-last-message") + 1]).write_text('{"findings": []}')
            return subprocess.CompletedProcess(observed["command"], 0, usage, "")
        self.run_review(during_run=respond)
        summary = self.helper["review_usage_summary"](self.args)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["reported_attempts"], 2)
        self.assertEqual(summary["partial_attempts"], 1)
        self.assertEqual(summary["tokens"]["input_tokens"], 10)

    def test_hostname_selection_also_accepts_existing_command_auth_and_no_fallback_model(self):
        self.configure()
        self.provider.pop("experimental_bearer_token")
        self.auth = {"command": str(self.runtime_helper)}
        self.write_config()
        observed = self.run_review()
        self.assertNotIn("auth_args", observed)
        self.assertIn("exec ", observed["auth_launcher_text"])
        self.provider["experimental_bearer_token"] = self.token
        self.auth = None
        self.write_config()
        self.args.codex_no_fallback = True
        self.args.fallback_model = "gpt-6-luna"
        attempts = []
        def failure(observed):
            attempts.append(observed["command"])
            return subprocess.CompletedProcess(observed["command"], 1, "",
                f"The model {self.args.model} does not exist or you do not have access to it.")
        with self.assertRaises(SystemExit):
            self.run_review(during_run=failure)
        self.assertEqual(len(attempts), 1)

    def test_config_ownership_writable_paths_repository_provenance_and_parse_errors_fail(self):
        self.configure()
        config = self.home / "config.toml"
        for path in (config, self.home):
            mode = stat.S_IMODE(path.stat().st_mode)
            path.chmod(mode | 0o020)
            self.assert_route_refused()
            path.chmod(mode)
        original_stat = Path.lstat
        def foreign_owner(path, *args, **kwargs):
            info = original_stat(path, *args, **kwargs)
            if path == config:
                values = list(info)
                values[4] = os.getuid() + 1
                return os.stat_result(values)
            return info
        with mock.patch.object(Path, "lstat", foreign_owner):
            self.assert_route_refused()
        before = config.read_bytes()
        for contents in (b"model_provider = [", b"\xff"):
            config.write_bytes(contents)
            self.assert_route_refused()
        config.write_bytes(before)
        with mock.patch.dict(sys.modules, {"tomllib": None, "tomli": None}):
            self.assert_route_refused()
        repo_config = self.repo / "operator.toml"
        repo_config.write_bytes(before)
        config.unlink()
        config.symlink_to(repo_config)
        self.assert_route_refused()
        config.unlink()
        config.write_bytes(before)
        repo_link = self.repo / "external"
        repo_link.symlink_to(self.home, target_is_directory=True)
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(repo_link)}):
            self.assert_route_refused()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(self.repo)}):
            self.assert_route_refused()

    def test_secret_redaction_usage_and_cleanup_on_failures_and_interruption(self):
        self.configure()
        self.args.stream_engine_output = True
        runtimes = []
        for outcome in ("success", "failure", "missing", "interrupt"):
            with self.subTest(outcome=outcome):
                def respond(observed):
                    runtime = Path(observed["auth_args"][2]).parent
                    runtimes.append(runtime)
                    display = observed["stream_display"]
                    for stream in ("stdout", "stderr"):
                        self.assertNotIn(self.token, display(stream, self.token) or "")
                    agent = display("stdout", json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": self.token}}))
                    self.assertIn("[REDACTED]", agent)
                    self.assertNotIn(self.token, agent)
                    usage = display("stdout", '{"type":"turn.completed","usage":{"input_tokens":5,"output_tokens":2}}')
                    self.assertIn("input_tokens=5", usage)
                    if outcome == "interrupt":
                        raise KeyboardInterrupt
                    command = observed["command"]
                    Path(command[command.index("--output-last-message") + 1]).write_text(
                        json.dumps({"findings": [], "explanation": self.token}) if outcome == "success" else "")
                    return subprocess.CompletedProcess(command, 1 if outcome == "failure" else 0, self.token, "HTTP 401 " + self.token)
                if outcome == "success":
                    self.assertNotIn(self.token, self.run_review(during_run=respond)["report"])
                else:
                    with self.assertRaises(KeyboardInterrupt if outcome == "interrupt" else SystemExit) as caught:
                        self.run_review(during_run=respond)
                    self.assertNotIn(self.token, str(caught.exception))
                self.assertFalse(runtimes[-1].exists())
        route = self.helper["load_codex_inference_route"](self.repo, [], "gateway.example.invalid")
        self.assertNotIn(self.token, repr(route))


if __name__ == "__main__":
    unittest.main()
