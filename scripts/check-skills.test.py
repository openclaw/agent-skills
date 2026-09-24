from __future__ import annotations

import contextlib
import io
import os
import runpy
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
MODULES = [
    "skills/autoreview/scripts/autoreview_test.py",
    "skills.autoreview.tests.test_autoreview_hardening",
    "skills.autoreview.tests.test_codex_sandbox",
    "skills.autoreview.tests.test_codex_inference_route",
    "skills.autoreview.tests.test_git_line_endings",
    "skills.autoreview.tests.test_git_boundary",
    "skills.autoreview.tests.test_git_filter_collection",
]


class CheckSkillsTest(unittest.TestCase):
    def commands(self, args: list[str]) -> list[list[str]]:
        with mock.patch("shutil.which", side_effect=lambda name: name), \
                mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(MAIN(args), 0)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs, {"cwd": SCRIPT.resolve().parent.parent})
        return [call.args[0] for call in run.call_args_list]

    def test_default_preserves_full_command_order_and_combined_modules(self) -> None:
        commands = self.commands([])
        self.assertEqual(commands, self.commands(["--group", "all"]))
        self.assertEqual([command[1] for command in commands], [
            "scripts/validate-skills", "-n", "-m", "scripts/install-skills.test.py",
            "scripts/validate-skills.test.py", "scripts/check-skills.test.py", "-m",
            "--check", "--check", "--check", "run", "--test",
        ])
        self.assertEqual(commands[6], [sys.executable, "-m", "unittest", *MODULES])

    def test_groups_cover_each_module_once_and_only_core_runs_other_checks(self) -> None:
        full = self.commands([])
        grouped_modules = []
        for group, expected in (("core", MODULES[:1]), ("hardening", MODULES[1:2]),
                                ("boundaries", MODULES[2:])):
            with self.subTest(group=group):
                commands = self.commands(["--group", group])
                suites = [command for command in commands if command[1:3] == ["-m", "unittest"]]
                self.assertEqual(suites, [[sys.executable, "-m", "unittest", *expected]])
                grouped_modules.extend(suites[0][3:])
                other = [command for command in commands if command not in suites]
                self.assertEqual(other, [command for command in full if command[1:3] != ["-m", "unittest"]]
                                 if group == "core" else [])
        self.assertEqual(grouped_modules, MODULES)
        self.assertEqual(len(grouped_modules), len(set(grouped_modules)))

    def test_first_failure_stops_and_preserves_exit_status(self) -> None:
        for group in ("all", "core", "hardening", "boundaries", "hardening-1", "hardening-2"):
            with self.subTest(group=group), \
                    mock.patch.dict(MAIN.__globals__, {"hardening_test_ids": lambda _root: ["first", "second"]}), \
                    mock.patch("shutil.which", return_value="resolved-executable"), \
                    mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 17)) as run, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(MAIN(["--group", group]), 17)
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0][0], "resolved-executable")

    def test_missing_executable_stops_before_execution(self) -> None:
        for group in ("boundaries", "hardening-1", "hardening-2"):
            with self.subTest(group=group), \
                    mock.patch.dict(MAIN.__globals__, {"hardening_test_ids": lambda _root: ["first", "second"]}), \
                    mock.patch("shutil.which", return_value=None), mock.patch("subprocess.run") as run, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(MAIN(["--group", group]), 1)
            run.assert_not_called()
            self.assertIn("required executable not found:", error.getvalue())

    def test_hardening_shards_cover_native_loader_ids_once(self) -> None:
        root = SCRIPT.resolve().parent.parent
        loader = unittest.TestLoader()
        with mock.patch.object(sys, "path", [str(root), *sys.path]):
            pending = list(loader.loadTestsFromNames(MODULES[1:2]))
        self.assertFalse(loader.errors)
        expected = []
        while pending:
            test = pending.pop()
            if isinstance(test, unittest.TestSuite):
                pending.extend(test)
            else:
                expected.append(test.id())
        expected.sort()
        self.assertTrue(expected)
        self.assertEqual(len(expected), len(set(expected)))
        shards = []
        for index, group in enumerate(("hardening-1", "hardening-2")):
            command, = self.commands(["--group", group])
            self.assertEqual(command[:3], [sys.executable, "-m", "unittest"])
            self.assertEqual(command[3:], expected[index::2])
            self.assertTrue(command[3:])
            self.assertEqual([command], self.commands(["--group", group]))
            shards.append(command[3:])
        self.assertFalse(set(shards[0]) & set(shards[1]))
        self.assertEqual(sorted(shards[0] + shards[1]), expected)

    def test_discovery_is_bound_to_script_root_from_foreign_cwd(self) -> None:
        root = SCRIPT.resolve().parent.parent
        expected = HELPER["hardening_test_ids"](root)
        with tempfile.TemporaryDirectory() as tempdir:
            foreign = Path(tempdir)
            (foreign / "skills").mkdir()
            (foreign / "skills/__init__.py").write_text("raise AssertionError('alien skills imported')\n")
            alien = types.ModuleType("skills")
            alien.__path__ = [str(foreign / "skills")]
            cwd = Path.cwd()
            try:
                os.chdir(foreign)
                with mock.patch.object(sys, "path", [str(foreign), *sys.path]), \
                        mock.patch.dict(sys.modules, {"skills": alien}):
                    before_path, before_modules = list(sys.path), dict(sys.modules)
                    first, = self.commands(["--group", "hardening-1"])
                    second, = self.commands(["--group", "hardening-2"])
                    self.assertEqual(sorted(first[3:] + second[3:]), expected)
                    self.assertEqual(sys.path, before_path)
                    self.assertEqual(sys.modules, before_modules)
            finally:
                os.chdir(cwd)

    def test_shards_handle_odd_counts_and_reject_discovery_failures(self) -> None:
        def suite(names):
            tests = []
            for name in names:
                test = mock.Mock(spec=unittest.TestCase)
                test.id.return_value = name
                tests.append(test)
            return unittest.TestSuite([unittest.TestSuite(tests)])

        loader = mock.Mock(errors=[], loadTestsFromModule=mock.Mock(return_value=suite(["e", "b", "d", "a", "c"])))
        with mock.patch("unittest.TestLoader", return_value=loader):
            first, = self.commands(["--group", "hardening-1"])
            second, = self.commands(["--group", "hardening-2"])
        self.assertEqual(first[3:], ["a", "c", "e"])
        self.assertEqual(second[3:], ["b", "d"])
        for names, errors, diagnostic in (([], [], "empty or duplicate"),
                                         (["a", "a"], [], "empty or duplicate"),
                                         (["a"], ["loader error"], "loader error"),
                                         (["a"], [], "shard has no test IDs")):
            loader = mock.Mock(errors=errors, loadTestsFromModule=mock.Mock(return_value=suite(names)))
            with self.subTest(names=names, errors=errors), \
                    mock.patch("unittest.TestLoader", return_value=loader), mock.patch("subprocess.run") as run, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(MAIN(["--group", "hardening-2"]), 1)
            run.assert_not_called()
            self.assertIn(diagnostic, error.getvalue())

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
