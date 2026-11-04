from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("check-skills")
HELPER = runpy.run_path(str(SCRIPT))
MAIN = HELPER["main"]


class CheckSkillsTest(unittest.TestCase):
    fixture_failure = None

    def test_manifest_covers_checkout_test_files_in_their_groups(self) -> None:
        root = SCRIPT.resolve().parent.parent
        core = "skills/autoreview/scripts/autoreview_test.py"
        hardening = "skills/autoreview/tests/test_autoreview_hardening.py"
        discovered = {path.relative_to(root).as_posix()
                      for path in (root / "skills/autoreview/tests").glob("test_*.py")}
        self.assertTrue((root / core).is_file())
        self.assertIn(hardening, discovered)
        expected = {"core": {core}, "hardening": {hardening},
                    "boundaries": discovered - {hardening}}
        self.assertEqual(set(HELPER["TEST_MODULES"]), set(expected))
        for group, paths in expected.items():
            actual = [entry if entry.endswith(".py") else entry.replace(".", "/") + ".py"
                      for entry in HELPER["TEST_MODULES"][group]]
            self.assertCountEqual(actual, paths, group)

    def commands(self, args: list[str]) -> list[list[str]]:
        with mock.patch("shutil.which", side_effect=lambda name: name), \
                mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(MAIN(args), 0)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs, {"cwd": SCRIPT.resolve().parent.parent})
        commands = [list(call.args[0]) for call in run.call_args_list]
        for command in commands:
            if command[1:2] == ["-X"]:
                self.assertTrue(command[2].startswith("pycache_prefix="))
                self.assertFalse(Path(command[2].removeprefix("pycache_prefix=")).exists())
                command[2] = "pycache_prefix=<temporary>"
        return commands

    def test_default_preserves_full_command_order(self) -> None:
        commands = self.commands([])
        self.assertEqual(commands, self.commands(["--group", "all"]))
        self.assertEqual([command[1] for command in commands[:6]], [
            "scripts/validate-skills", "-n", "-X", "scripts/install-skills.test.py",
            "scripts/validate-skills.test.py", "scripts/check-skills.test.py",
        ])
        self.assertEqual(commands[2][1:5], ["-X", "pycache_prefix=<temporary>", "-m", "py_compile"])
        self.assertEqual(commands[6][1], "scripts/windows-test-process.test.py")
        self.assertIn("scripts/check-skills", commands[7])
        self.assertEqual(commands[7][-3:], ["--group", "all", "--tests-only"])
        self.assertEqual([command[1] for command in commands[8:]], [
            "--check", "--check", "--check", "run", "--test",
        ])

    def test_only_core_runs_other_checks(self) -> None:
        full = self.commands([])
        for group in (*HELPER["TEST_MODULES"], *HELPER["HARDENING_SHARDS"]):
            with self.subTest(group=group):
                commands = self.commands(["--group", group])
                suites = [command for command in commands if "--tests-only" in command]
                self.assertEqual(len(suites), 1)
                self.assertEqual(suites[0][-3:], ["--group", group, "--tests-only"])
                other = [command for command in commands if command not in suites]
                self.assertEqual(other, full[:7] + full[8:] if group == "core" else [])

    def test_first_failure_stops_and_preserves_exit_status(self) -> None:
        for group in ("all", *HELPER["TEST_MODULES"], *HELPER["HARDENING_SHARDS"]):
            with self.subTest(group=group), \
                    mock.patch("shutil.which", return_value="resolved-executable"), \
                    mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 17)) as run, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(MAIN(["--group", group]), 17)
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0][0], "resolved-executable")

    def test_missing_executable_stops_before_execution(self) -> None:
        with mock.patch("shutil.which", return_value=None), mock.patch("subprocess.run") as run, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(MAIN(["--group", "boundaries"]), 1)
        run.assert_not_called()
        self.assertIn("required executable not found:", error.getvalue())

    def test_main_compiles_outside_checkout_and_cleans_cache_on_success_and_failure(self) -> None:
        real_run = subprocess.run
        source_root = SCRIPT.resolve().parent.parent
        sources = (
            "scripts/install-skills", "scripts/install-skills.test.py",
            "scripts/validate-skills", "scripts/validate-skills.test.py",
            "scripts/check-skills", "scripts/check-skills.test.py",
            "skills/autoreview/scripts/autoreview",
            "skills/autoreview/scripts/windows-owned-process.py",
            "skills/autoreview/scripts/test-review-harness.py",
            "skills/autoreview/scripts/autoreview_test.py",
        )
        for invalid in (False, True):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "repo"
                for source in sources:
                    target = root / source
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source_root / source, target)
                if invalid:
                    (root / "scripts/install-skills.test.py").write_text("def broken(:\n", encoding="utf-8")
                before = {source: (root / source).read_bytes() for source in sources}
                main = runpy.run_path(str(root / "scripts/check-skills"))["main"]
                executed = []
                caches = []
                compiled = []

                def run(command, **kwargs):
                    executed.append(command)
                    # Delegate the compiler unchanged; unrelated toolchains and
                    # test suites are outside this cache-placement regression.
                    if "py_compile" not in command:
                        return subprocess.CompletedProcess(command, 0)
                    result = real_run(
                        command, **kwargs, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                        capture_output=True, text=True, encoding="utf-8",
                    )
                    compiled.append(result)
                    self.assertEqual(command[1], "-X")
                    cache = Path(command[2].removeprefix("pycache_prefix="))
                    caches.append(cache)
                    self.assertTrue(any(cache.rglob("*.pyc")))
                    self.assertFalse(list(root.rglob("__pycache__")))
                    return result

                with mock.patch("shutil.which", side_effect=lambda name: name), \
                        mock.patch("subprocess.run", side_effect=run), \
                        contextlib.redirect_stdout(io.StringIO()):
                    status = main(["--group", "core"])
                self.assertEqual(len(compiled), 1)
                self.assertEqual(status, compiled[0].returncode)
                if invalid:
                    self.assertNotEqual(status, 0)
                    self.assertIn("SyntaxError", compiled[0].stderr)
                    self.assertEqual(len(executed), 3)
                else:
                    self.assertEqual(status, 0, compiled[0].stderr)
                    self.assertEqual(len(executed), 13)
                self.assertFalse(any(cache.exists() for cache in caches))
                self.assertFalse(list(root.rglob("__pycache__")))
                self.assertEqual(before, {source: (root / source).read_bytes() for source in sources})

    @contextlib.contextmanager
    def fixture(self, *, parent=None, forward_import=False, fail_test=None):
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            root = Path(directory) / "repo"
            (root / "scripts").mkdir(parents=True)
            shutil.copy2(SCRIPT, root / "scripts/check-skills")
            for name in ("windows_test_process.py", "windows-test-process.test.py"):
                shutil.copy2(SCRIPT.with_name(name), root / "scripts" / name)
            log = Path(directory) / "executed"
            groups = {}
            for group, entries in HELPER["TEST_MODULES"].items():
                groups[group] = []
                for entry in entries:
                    name = entry.removesuffix(".py").replace("/", ".")
                    path = root.joinpath(*name.split(".")).with_suffix(".py")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    body = "import importlib, os, unittest\nfrom pathlib import Path\nSENTINEL = 'local checkout'\n"
                    if forward_import and name.endswith("test_native_handoff"):
                        body += "from skills.autoreview.tests import test_openclaw_exec as forward\n"
                    # Exercise the same sibling-import forms as the real suite.
                    if name.endswith("test_openclaw_exec"):
                        body += "from skills.autoreview.tests import test_native_handoff as native\nassert native.SENTINEL == SENTINEL\n"
                    if name.endswith("test_gitlinks"):
                        body += "from skills.autoreview.tests.test_autoreview_hardening import SENTINEL as sibling\nassert sibling == SENTINEL\n"
                    body += "class Cases(unittest.TestCase):\n"
                    for index in range(5 if group == "hardening" else 1):
                        label = name + ".Cases.test_" + str(index)
                        groups[group].append(label)
                        body += (f"    def test_{index}(self):\n"
                                 f"        with Path({str(log)!r}).open('a') as stream: stream.write({label!r} + '\\n')\n"
                                 f"        self.assertNotEqual({fail_test!r}, {label!r})\n")
                        if forward_import and name.endswith("test_native_handoff"):
                            body += "        self.assertIs(forward, importlib.import_module('skills.autoreview.tests.test_openclaw_exec'))\n"
                    path.write_text(body, encoding="utf-8")
            foreign = Path(directory) / "installed"
            (foreign / "skills").mkdir(parents=True)
            marker = foreign / "imported"
            (foreign / "skills/__init__.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('unrelated package imported')\n"
                "raise RuntimeError('unrelated installed skills package')\n",
                encoding="utf-8",
            )
            environment = {**os.environ, "PYTHONPATH": str(foreign), "PYTHONNOUSERSITE": "1"}
            yield root, foreign, marker, log, environment, groups

    def invoke(self, root, cwd, environment, group, *, tests_only=True, output_encoding="utf-8"):
        return subprocess.run(
            [sys.executable, "-S", "-X", "utf8=1", str(root / "scripts/check-skills"), "--group", group,
             *(["--tests-only"] if tests_only else [])],
            cwd=cwd, env={**environment, "PYTHONIOENCODING": output_encoding},
            text=True, encoding=output_encoding, capture_output=True, timeout=30,
        )

    def test_every_group_and_shard_runs_checkout_tests_despite_installed_package(self) -> None:
        if os.name == "nt":
            bootstrap = runpy.run_path(str(SCRIPT.with_name("windows_test_process.py")))
            self.assertTrue(bootstrap["windows_test_process_status"]()["eligible"],
                            "runner fixtures must be created by the admitted test process")
        with self.fixture() as (root, foreign, marker, log, environment, groups):
            expected = {**groups, "all": sum(groups.values(), []),
                        "hardening-1": sorted(groups["hardening"])[::2],
                        "hardening-2": sorted(groups["hardening"])[1::2]}
            for group, labels in expected.items():
                with self.subTest(group=group):
                    log.unlink(missing_ok=True)
                    result = self.invoke(root, foreign, environment, group)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(sorted(log.read_text().splitlines()), sorted(labels))
                    self.assertFalse(marker.exists())
            # Also exercise the outer command runner and its real child process.
            log.unlink()
            result = self.invoke(root, foreign, environment, "boundaries", tests_only=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sorted(log.read_text().splitlines()), sorted(groups["boundaries"]))
            self.assertFalse(marker.exists())

    def test_test_failure_is_not_hidden_by_file_bound_loading(self) -> None:
        with self.fixture(fail_test="skills.autoreview.tests.test_native_handoff.Cases.test_0") as (
            root, foreign, marker, log, environment, groups,
        ):
            result = self.invoke(root, foreign, environment, "boundaries", tests_only=False)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("FAILED (failures=1)", result.stderr)
            self.assertFalse(marker.exists())

    def test_fixture_invocation_uses_utf8_with_inherited_legacy_stream_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "caf\u00e9"
            parent.mkdir()
            # A real failing test emits its non-ASCII source path. cp1252 can
            # encode this character, so implicit UTF-8 capture would misdecode
            # it rather than receiving an ASCII backslash escape.
            with self.fixture(
                parent=parent, fail_test="skills.autoreview.tests.test_native_handoff.Cases.test_0",
            ) as (root, foreign, marker, log, environment, groups):
                environment["PYTHONIOENCODING"] = "cp1252"
                result = self.invoke(root, foreign, environment, "boundaries")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(str(parent.resolve()), result.stderr)
                self.assertIn("FAILED (failures=1)", result.stderr)
                self.assertFalse(marker.exists())

    def test_forward_sibling_import_preserves_module_identity(self) -> None:
        with self.fixture(forward_import=True) as (root, foreign, marker, log, environment, groups):
            result = self.invoke(root, foreign, environment, "boundaries", tests_only=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertCountEqual(log.read_text().splitlines(), groups["boundaries"])
            self.assertFalse(marker.exists())

    def test_fixture_environment_covers_discovery_children_and_cleanup(self) -> None:
        with self.fixture() as (root, foreign, marker, log, environment, groups):
            operator = root.parent / "synthetic-operator"
            operator.mkdir()
            (operator / ".codex").mkdir()
            protected = [operator / ".codex" / name for name in ("config.toml", "auth.json")]
            for config in protected:
                config.write_text("synthetic operator state\n", encoding="utf-8")
            selectors = {
                "CODEX_HOME", "CLAUDE_CONFIG_DIR", "PI_CODING_AGENT_DIR",
                "OPENCLAW_CONFIG_PATH", "GH_CONFIG_DIR", "AWS_CONFIG_FILE",
                "GOOGLE_APPLICATION_CREDENTIALS", "SSL_CERT_FILE",
                "DBUS_SESSION_BUS_ADDRESS", "AUTOREVIEW_CODEX_CONFIG",
                "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CUSTOM_TEST_API_KEY",
            }
            environment.update({key: str(operator) for key in selectors})
            environment["CODEX_HOME"] = str(operator / ".codex")
            environment.update(HOME=str(operator), USERPROFILE=str(operator),
                               XDG_CONFIG_HOME=str(operator), APPDATA=str(operator))
            path = root / "skills/autoreview/tests/test_autoreview_hardening.py"
            driver = '''
import json, os, runpy, sys
from pathlib import Path
protected = set(json.loads(sys.argv[3]))
def forbid_operator_reads(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        if os.path.abspath(os.fsdecode(args[0])) in protected:
            raise AssertionError("runner accessed synthetic operator configuration")
sys.addaudithook(forbid_operator_reads)
before = dict(os.environ)
result = runpy.run_path(sys.argv[1])["main"](["--group", "hardening", "--tests-only"])
Path(sys.argv[2]).write_text(json.dumps(dict(os.environ) == before))
sys.exit(result)
'''
            # A real imported test module and its child observe only the fixture
            # environment. Failure at either stage must still release the home.
            for failure in ("none", "discovery", "test"):
                with self.subTest(failure=failure):
                    receipt = root.parent / f"environment-{failure}.json"
                    restored = root.parent / f"restored-{failure}.json"
                    body = f'''
import json, os, subprocess, sys, unittest
from pathlib import Path
selectors = {sorted(selectors)!r}
receipt = Path({str(receipt)!r})
home = Path.home()
observation = {{"home": str(home), "selectors": [key for key in selectors if key in os.environ],
               "copied_config": (home / ".codex").exists(),
               "path": os.environ.get("PATH"), "pythonpath": os.environ.get("PYTHONPATH"),
               "temp": {{key: os.environ.get(key) for key in ("TEMP", "TMP", "TMPDIR")}},
               "config": os.environ.get("XDG_CONFIG_HOME"), "appdata": os.environ.get("APPDATA"),
               "runtime_mode": (Path(os.environ["XDG_RUNTIME_DIR"]).stat().st_mode & 0o777
                                if "XDG_RUNTIME_DIR" in os.environ else None)}}
receipt.write_text(json.dumps(observation))
if {failure!r} == "discovery":
    raise RuntimeError("synthetic discovery failure")
class Cases(unittest.TestCase):
    def test_child(self):
        self.assertEqual(observation["selectors"], [])
        self.assertNotEqual(home, Path({str(operator)!r}))
        # Credentials explicitly created by a test remain available to its child.
        env = {{**os.environ, "OPENAI_API_KEY": "synthetic-fixture", "PYTHONIOENCODING": "utf-8"}}
        code = "import json, os; print(json.dumps([os.environ['OPENAI_API_KEY'], os.environ.get('CODEX_HOME'), os.environ['HOME']]))"
        child = subprocess.run([sys.executable, "-S", "-X", "utf8=1", "-c", code], env=env,
                               text=True, encoding="utf-8", capture_output=True, check=True)
        observation["child"] = json.loads(child.stdout)
        receipt.write_text(json.dumps(observation))
        self.assertNotEqual({failure!r}, "test", "synthetic test failure")
'''
                    path.write_text(body, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, "-S", "-X", "utf8=1", "-c", driver,
                         str(root / "scripts/check-skills"), str(restored),
                         json.dumps([str(config.resolve()) for config in protected])],
                        env={**environment, "PYTHONIOENCODING": "utf-8"}, cwd=foreign,
                        text=True, encoding="utf-8", capture_output=True, timeout=30,
                    )
                    self.assertEqual(result.returncode, 0 if failure == "none" else 1,
                                     result.stdout + result.stderr)
                    if failure != "none":
                        self.assertIn(f"synthetic {failure} failure", result.stderr)
                    observed = json.loads(receipt.read_text())
                    self.assertEqual(observed["selectors"], [])
                    self.assertEqual(Path(observed["home"]).parent, operator.resolve())
                    self.assertFalse(observed["copied_config"])
                    self.assertFalse(Path(observed["home"]).exists())
                    self.assertTrue(json.loads(restored.read_text()))
                    self.assertEqual(observed["path"], environment.get("PATH"))
                    self.assertEqual(observed["pythonpath"], str(foreign))
                    self.assertEqual(observed["temp"], {key: environment.get(key) for key in ("TEMP", "TMP", "TMPDIR")})
                    for key in ("config", "appdata"):
                        self.assertTrue(Path(observed[key]).is_relative_to(observed["home"]))
                    if os.name != "nt":
                        self.assertEqual(observed["runtime_mode"], 0o700)
                    if failure != "discovery":
                        self.assertEqual(observed["child"], ["synthetic-fixture", None, observed["home"]])
                    for config in protected:
                        self.assertEqual(config.read_text(encoding="utf-8"), "synthetic operator state\n")
                    self.assertFalse(marker.exists())

    def test_fixture_source_supports_unicode_paths_under_a_narrow_locale(self) -> None:
        # Always exercise outer-command output. The default-write-encoding proof
        # additionally needs a real narrow codec, which some hosts do not offer.
        code = r'''
import locale, os, runpy, sys, tempfile
from pathlib import Path
if sys.getfilesystemencoding().lower().replace("-", "") != "utf8":
    print("host has no UTF-8 filesystem locale with UTF-8 mode disabled", file=sys.stderr)
    sys.exit(77)
character = "\u674e"
if sys.argv[2] == "narrow":
    locale.setlocale(locale.LC_CTYPE, "C")
    for character in ("\u674e", "\U0001f984"):
        try:
            character.encode(locale.getpreferredencoding(False))
        except UnicodeEncodeError:
            break
    else:
        print("host text codec supports both Unicode filename probes", file=sys.stderr)
        sys.exit(77)
case = runpy.run_path(sys.argv[1])["CheckSkillsTest"]()
with tempfile.TemporaryDirectory() as temporary:
    parent = Path(temporary) / character
    parent.mkdir()
    if os.name != "nt":
        # A real interpreter alias models a checkout-local virtualenv without
        # requiring virtualenv installation or Windows symlink privileges.
        interpreter = parent / "python"
        interpreter.symlink_to(sys.executable)
        sys.executable = str(interpreter)
    with case.fixture(parent=parent, fail_test=sys.argv[3] or None) as (root, foreign, marker, log, environment, groups):
        result = case.invoke(root, foreign, environment, "boundaries", tests_only=False,
                             output_encoding="ascii")
        case.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        case.assertFalse(marker.exists())
        case.assertCountEqual(log.read_text().splitlines(), groups["boundaries"])
'''
        for mode in ("outer", "narrow"):
            with self.subTest(proof=mode):
                command = [sys.executable, "-X", "utf8=1" if mode == "outer" else "utf8=0",
                           "-S", "-c", code, str(Path(__file__).resolve()), mode,
                           self.fixture_failure or ""]
                environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
                result = subprocess.run(command, env=environment, text=True, encoding="utf-8",
                                        capture_output=True, timeout=30)
                if mode == "narrow" and result.returncode == 77:
                    # Try the common POSIX UTF-8 locale when the inherited
                    # locale cannot establish the required filesystem support.
                    result = subprocess.run(command, env={**environment, "LC_ALL": "C.UTF-8"},
                                            text=True, encoding="utf-8", capture_output=True, timeout=30)
                if mode == "narrow" and result.returncode == 77:
                    self.skipTest(result.stderr.strip())
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unicode_proof_keeps_failure_checks_when_optimized(self) -> None:
        code = '''
import runpy, sys, unittest
case = runpy.run_path(sys.argv[1])["CheckSkillsTest"](
    "test_fixture_source_supports_unicode_paths_under_a_narrow_locale")
case.fixture_failure = "skills.autoreview.tests.test_native_handoff.Cases.test_0"
result = unittest.TextTestRunner().run(unittest.TestSuite([case]))
sys.exit(0 if result.wasSuccessful() else 1)
'''
        result = subprocess.run(
            [sys.executable, "-O", "-S", "-X", "utf8=1", "-c", code, str(Path(__file__).resolve())],
            env={**os.environ, "PYTHONOPTIMIZE": "1", "PYTHONIOENCODING": "utf-8"},
            text=True, encoding="utf-8", capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL: test_0", result.stderr)
        self.assertIn("skills.autoreview.tests.test_native_handoff.Cases", result.stderr)

    def test_empty_and_broken_discovery_fail_before_running_tests(self) -> None:
        with self.fixture() as (root, foreign, marker, log, environment, groups):
            path = root / "skills/autoreview/tests/test_autoreview_hardening.py"
            for content, group, diagnostic in (
                ("", "hardening", "empty or duplicate"),
                ("syntax error!", "hardening-1", "test discovery failed"),
                ("import unittest\nclass One(unittest.TestCase):\n def test_one(self): pass\n",
                 "hardening-2", "shard has no test IDs"),
            ):
                with self.subTest(group=group, diagnostic=diagnostic):
                    path.write_text(content, encoding="utf-8")
                    result = self.invoke(root, foreign, environment, group)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn(diagnostic, result.stderr)
                    self.assertFalse(log.exists())
                    self.assertFalse(marker.exists())

    def test_module_binding_restores_existing_packages(self) -> None:
        alien = types.ModuleType("skills")
        with mock.patch.dict(sys.modules, {"skills": alien}):
            before = {name: value for name, value in sys.modules.items()
                      if name == "skills" or name.startswith("skills.")}
            with HELPER["repository_test_modules"](SCRIPT.resolve().parent.parent):
                self.assertIsNot(sys.modules["skills"], alien)
            after = {name: value for name, value in sys.modules.items()
                     if name == "skills" or name.startswith("skills.")}
            self.assertEqual(before, after)

    def test_invalid_selector_is_rejected_before_any_command(self) -> None:
        for args in (["--group", "unknown"], ["--group"]):
            with self.subTest(args=args), mock.patch("shutil.which") as which, \
                    mock.patch("subprocess.run") as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    MAIN(args)
                self.assertEqual(result.exception.code, 2)
                which.assert_not_called()
                run.assert_not_called()


if __name__ == "__main__":
    # Admit the test process before it creates private fixture checkouts.
    # The runner entrypoint, not this caller test, owns the native parent proof.
    bootstrap = runpy.run_path(str(SCRIPT.with_name("windows_test_process.py")))
    status = bootstrap["ensure_windows_test_process"](sys.argv[0], sys.argv[1:])
    if status is not None:
        bootstrap["exit_test_process"](status)
    unittest.main()
