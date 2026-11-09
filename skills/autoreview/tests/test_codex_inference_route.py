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

from .test_autoreview_hardening import git, init_repo, load_helper, write_executable


class CodexInferenceRouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="autoreview-route-test.")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = init_repo(self.root)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.codex = write_executable(
            self.bin / "codex", "#!" + sys.executable + " -S\nraise SystemExit(99)\n"
        )
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
            engine="codex", codex_bin=str(self.codex), codex_config=['model_provider="review_api"'], codex_speed=None,
            fallback_model=None, model="gpt-6-sol", stream_engine_output=False,
            thinking="high", tools=True, web_search=False,
        )
        self.environment = mock.patch.dict(os.environ, {
            "CODEX_HOME": str(self.home), "HOME": str(self.root),
            "AUTOREVIEW_CODEX_CONFIG": "", "AUTOREVIEW_CODEX_SPEED": "",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @unittest.skipIf(os.name == "nt", "uses POSIX symbolic links")
    def test_source_owned_links_cannot_select_codex_home_or_provider_paths(self):
        upstream = self.root / "upstream"
        upstream.mkdir()
        controlled = upstream / "selector"
        alias = self.root / "operator-alias"
        alias.symlink_to(controlled)
        token = self.helper["UNTRUSTED_SOURCE_ROOTS"].set((self.repo, upstream))
        try:
            controlled.symlink_to(self.home, target_is_directory=True)
            with self.subTest(path="CODEX_HOME"), mock.patch.dict(os.environ, {"CODEX_HOME": str(alias)}):
                self.assertIsNone(self.helper["codex_source_home"](self.repo))
            for key, target in (("command", self.runtime_helper), ("cwd", self.home)):
                with self.subTest(key=key):
                    controlled.unlink()
                    controlled.symlink_to(target, target_is_directory=target.is_dir())
                    original = self.auth.copy()
                    self.auth[key] = str(alias)
                    self.write_config()
                    try:
                        with self.assertRaisesRegex(SystemExit, "authentication .*outside"):
                            self.helper["load_codex_inference_route"](self.repo, self.args.codex_config)
                    finally:
                        self.auth = original
            # An operator-owned link directly to the same external directory remains valid.
            alias.unlink()
            alias.symlink_to(self.home, target_is_directory=True)
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(alias)}):
                self.assertEqual(self.helper["codex_source_home"](self.repo), self.home.resolve())
        finally:
            self.helper["UNTRUSTED_SOURCE_ROOTS"].reset(token)

    def test_relative_engine_config_is_pinned_before_changing_child_directory(self):
        scratch = self.root / "scratch"
        child = scratch / "run"
        child.mkdir(parents=True)
        source = scratch / "operator-home"
        source.mkdir()
        (source / "selected.txt").write_text("source-owned")
        (self.home / "selected.txt").write_text("operator-owned")
        token = self.helper["UNTRUSTED_SOURCE_ROOTS"].set((self.repo, source))
        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            for engine, key in (("claude", "CLAUDE_CONFIG_DIR"), ("codex", "CODEX_HOME")):
                with self.subTest(engine=engine), mock.patch.dict(os.environ, {key: "../operator-home"}):
                    env = self.helper["safe_engine_env"](self.repo, engine=engine)
                    result = subprocess.run([
                        sys.executable, "-S", "-c",
                        "import os,pathlib,sys; print((pathlib.Path(os.environ[sys.argv[1]])/'selected.txt').read_text())",
                        key,
                    ], cwd=child, env=env, text=True, capture_output=True, check=True)
                    self.assertEqual(result.stdout.strip(), "operator-owned")
                    self.assertEqual(env[key], str(self.home.resolve()))
        finally:
            os.chdir(previous)
            self.helper["UNTRUSTED_SOURCE_ROOTS"].reset(token)

    @unittest.skipIf(os.name == "nt", "uses executable POSIX login wrapper")
    def test_entry_distinguishes_operator_login_from_external_source_review(self):
        child = self.root / "login-child"
        child.mkdir()
        wrapper = write_executable(self.bin / "login-wrapper", "#!" + sys.executable + " -S\n"
            "import os,sys\n"
            "configured = os.environ.get('XDG_CONFIG_HOME', '').endswith('/operator-settings')\n"
            "configured = configured and os.path.isabs(os.environ.get('CODEX_HOME', ''))\n"
            "print('Logged in using ChatGPT' if configured else 'Not logged in')\n"
            "sys.exit(0 if configured else 1)\n")
        upstream_parent = self.root / "external"
        upstream_parent.mkdir()
        upstream = init_repo(upstream_parent)
        (upstream / "context.txt").write_text("external source fixture")
        git(upstream, "add", "context.txt")
        git(upstream, "commit", "-qm", "source fixture")
        manifest = {
            "version": 1, "root": str(upstream.resolve()),
            "commit": git(upstream, "rev-parse", "HEAD").strip(),
            "files": [{"path": "context.txt", "mode": "100644",
                       "blob": git(upstream, "rev-parse", "HEAD:context.txt").strip()}],
        }
        (self.repo / "external-context.json").write_text(json.dumps(manifest))
        observed = []
        def login_from_boundary(args, repo):
            self.assertEqual(repo, self.repo)
            roots = self.helper["UNTRUSTED_SOURCE_ROOTS"].get()
            self.assertIn(self.repo, roots)
            self.assertEqual(upstream in roots, bool(args.external_source_manifests))
            observed.append(self.helper["codex_subscription_login_missing"](str(wrapper), child, repo))
            return 0
        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            for manifests in ([], ["external-context.json"]):
                with self.subTest(manifests=manifests), mock.patch.dict(os.environ, {
                    "XDG_CONFIG_HOME": str(self.root / "operator-settings"),
                    "CODEX_HOME": "../operator-home",
                }), mock.patch.dict(self.helper["main_with_args"].__globals__, {
                    "main_with_source_boundary": login_from_boundary,
                }):
                    with mock.patch.object(sys, "argv", ["autoreview"]):
                        args = self.helper["parse_args"]()
                    args.external_source_context_file = manifests
                    self.assertEqual(self.helper["main_with_args"](args), 0)
            self.assertEqual(observed, [False, True],
                             "ordinary entry retains operator settings; external review keeps its filtered environment")
            self.assertFalse(self.helper["EXTERNAL_SOURCE_REVIEW"].get())
        finally:
            os.chdir(previous)

    def write_config(self):
        def value(item):
            if isinstance(item, dict):
                return "{" + ", ".join(f"{json.dumps(key)}={value(part)}" for key, part in item.items()) + "}"
            return json.dumps(item, ensure_ascii=False)

        def table(values):
            return "\n".join(f"{key} = {value(item)}" for key, item in values.items())

        text = table(self.config)
        text += "\n[model_providers.review_api]\n" + table(self.provider)
        text += "\n[model_providers.review_api.auth]\n" + table(self.auth)
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
            "ensure_codex_isolation_supported": mock.Mock(return_value=str(self.codex)),
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

    @unittest.skipIf(os.name == "nt", "uses POSIX symbolic links")
    def test_retry_revalidates_original_auth_command_directory(self):
        self.use_default_models()
        self.write_config()
        source_module = self.repo / "auth_dependency.py"
        source_module.write_text("raise SystemExit('source must not execute')\n")
        dependency = self.home / "auth_dependency.py"
        attempts = []

        def respond(observed):
            attempts.append(observed["command"])
            if len(attempts) == 1:
                # The staged launcher stays unchanged, but its original helper
                # directory must remain independent of reviewed source on retry.
                dependency.symlink_to(source_module)
                return subprocess.CompletedProcess(
                    observed["command"], 1, "",
                    "The model gpt-6.1-sol does not exist or you do not have access to it.",
                )

        with self.assertRaisesRegex(SystemExit, "trusted installation"):
            self.run_review(during_run=respond)
        self.assertEqual(len(attempts), 1, "a contaminated auth installation must prevent the fallback send")

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


if __name__ == "__main__":
    unittest.main()
