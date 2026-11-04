from __future__ import annotations

import contextlib
import io
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
        return [call.args[0] for call in run.call_args_list]

    def test_default_preserves_full_command_order(self) -> None:
        commands = self.commands([])
        self.assertEqual(commands, self.commands(["--group", "all"]))
        self.assertEqual([command[1] for command in commands[:6]], [
            "scripts/validate-skills", "-n", "-m", "scripts/install-skills.test.py",
            "scripts/validate-skills.test.py", "scripts/check-skills.test.py",
        ])
        self.assertIn(str(SCRIPT.resolve()), commands[6])
        self.assertEqual(commands[6][-3:], ["--group", "all", "--tests-only"])
        self.assertEqual([command[1] for command in commands[7:]], [
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
                self.assertEqual(other, full[:6] + full[7:] if group == "core" else [])

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

    @contextlib.contextmanager
    def fixture(self, *, parent=None, forward_import=False):
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            root = Path(directory) / "repo"
            (root / "scripts").mkdir(parents=True)
            shutil.copy2(SCRIPT, root / "scripts/check-skills")
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
                                 f"        with Path(os.environ['CHECK_TEST_LOG']).open('a') as stream: stream.write({label!r} + '\\n')\n"
                                 f"        self.assertNotEqual(os.environ.get('CHECK_FAIL_TEST'), {label!r})\n")
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
            log = Path(directory) / "executed"
            environment = {**os.environ, "PYTHONPATH": str(foreign), "PYTHONNOUSERSITE": "1",
                           "CHECK_TEST_LOG": str(log)}
            yield root, foreign, marker, log, environment, groups

    def invoke(self, root, cwd, environment, group, *, tests_only=True):
        return subprocess.run(
            [sys.executable, "-S", str(root / "scripts/check-skills"), "--group", group,
             *(["--tests-only"] if tests_only else [])],
            cwd=cwd, env=environment, text=True, capture_output=True, timeout=30,
        )

    def test_every_group_and_shard_runs_checkout_tests_despite_installed_package(self) -> None:
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
        with self.fixture() as (root, foreign, marker, log, environment, groups):
            environment["CHECK_FAIL_TEST"] = groups["boundaries"][0]
            result = self.invoke(root, foreign, environment, "boundaries", tests_only=False)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("FAILED (failures=1)", result.stderr)
            self.assertFalse(marker.exists())

    def test_forward_sibling_import_preserves_module_identity(self) -> None:
        with self.fixture(forward_import=True) as (root, foreign, marker, log, environment, groups):
            result = self.invoke(root, foreign, environment, "boundaries", tests_only=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertCountEqual(log.read_text().splitlines(), groups["boundaries"])
            self.assertFalse(marker.exists())

    def test_fixture_source_supports_unicode_paths_under_a_narrow_locale(self) -> None:
        # Change the text locale after interpreter startup so the filesystem
        # retains Unicode support while default text writes use a narrow codec.
        code = r'''
import locale, runpy, sys, tempfile
from pathlib import Path
case = runpy.run_path(sys.argv[1])["CheckSkillsTest"]()
with tempfile.TemporaryDirectory() as temporary:
    parent = Path(temporary) / "\u674e"
    parent.mkdir()
    locale.setlocale(locale.LC_CTYPE, "C")
    try:
        "\u674e".encode(locale.getpreferredencoding(False))
    except UnicodeEncodeError:
        pass
    else:
        raise AssertionError("fixture must exercise a narrow text locale")
    with case.fixture(parent=parent) as (root, foreign, marker, log, environment, groups):
        result = case.invoke(root, foreign, environment, "boundaries")
        assert result.returncode == 0, result.stdout + result.stderr
        assert not marker.exists()
        assert sorted(log.read_text().splitlines()) == sorted(groups["boundaries"])
'''
        result = subprocess.run([sys.executable, "-X", "utf8=0", "-S", "-c", code, str(Path(__file__).resolve())],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
    unittest.main()
