from __future__ import annotations

import contextlib
import io
import runpy
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("check-skills")
MAIN = runpy.run_path(str(SCRIPT))["main"]
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
        for group in ("all", "core", "hardening", "boundaries"):
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
