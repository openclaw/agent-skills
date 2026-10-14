from __future__ import annotations

import contextlib
import io
import os
import runpy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "autoreview"


class ReviewHarnessTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX directory traversal mode test")
    def test_harness_cleanup_restores_directory_traversal_before_retry(self) -> None:
        harness = SCRIPT.with_name("test-review-harness.py")
        cleanup_repo = runpy.run_path(str(harness))["cleanup_repo"]
        with tempfile.TemporaryDirectory() as tempdir:
            repo = Path(tempdir) / "repo"
            repo.mkdir()
            nested = repo / "nested"
            nested.mkdir()
            (nested / "fixture.txt").write_text("fixture", encoding="utf-8")
            nested.chmod(0o600)
            repo.chmod(0o600)
            try:
                cleanup_repo(repo)
                self.assertFalse(repo.exists())
            finally:
                if repo.exists():
                    repo.chmod(0o700)
                    if nested.exists():
                        nested.chmod(0o700)

    def test_harness_cleanup_rejects_retained_temp_repo(self) -> None:
        harness = SCRIPT.with_name("test-review-harness.py")
        cleanup_repo = runpy.run_path(str(harness))["cleanup_repo"]
        with tempfile.TemporaryDirectory() as tempdir:
            repo = Path(tempdir) / "repo"
            repo.mkdir()

            with mock.patch.object(shutil, "rmtree", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "path was retained"):
                    cleanup_repo(repo)

    def test_harness_main_preserves_review_failure_when_cleanup_fails(self) -> None:
        harness = SCRIPT.with_name("test-review-harness.py")
        namespace = runpy.run_path(str(harness))
        for review_status in (0, 23):
            with self.subTest(review_status=review_status), tempfile.TemporaryDirectory() as tempdir:
                repo = Path(tempdir) / "repo"
                repo.mkdir()
                stderr = io.StringIO()
                run_reviews = mock.Mock(side_effect=(
                    subprocess.CalledProcessError(review_status, "review") if review_status else None
                ))
                with (
                    # runpy returns a copy; main still reads its original globals.
                    mock.patch.dict(namespace["main"].__globals__, {
                        "create_fixture_repo": mock.Mock(),
                        "run_reviews": run_reviews,
                    }),
                    mock.patch.object(namespace["tempfile"], "mkdtemp", return_value=str(repo)),
                    mock.patch.object(namespace["shutil"], "rmtree", return_value=None),
                    contextlib.redirect_stderr(stderr),
                ):
                    status = namespace["main"]([])
                self.assertEqual(status, review_status or 1)
                self.assertIn("path was retained", stderr.getvalue())
                run_reviews.assert_called_once()

    @unittest.skipUnless(os.name == "nt", "native PowerShell wrapper execution test")
    def test_powershell_wrappers_fallback_quote_and_propagate_exit(self) -> None:
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell is None:
            self.skipTest("PowerShell is unavailable")

        scripts = SCRIPT.parent
        cases = (
            ("autoreview.ps1", ["--help", "two words"], "autoreview"),
            (
                "test-review-harness.ps1",
                ["-Fixture", "benign", "-Engine", "codex"],
                "test-review-harness.py",
            ),
        )
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            log_path = root / "launch.log"
            (root / "py.cmd").write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")
            (root / "python3.cmd").write_text(
                "@echo off\r\n"
                'if "%~1"=="-c" exit /b 0\r\n'
                'echo %*>>"%WRAPPER_LOG%"\r\n'
                "exit /b 23\r\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{root}{os.pathsep}{env.get('PATH', '')}",
                    "WRAPPER_LOG": str(log_path),
                }
            )

            for filename, arguments, helper in cases:
                with self.subTest(filename=filename):
                    result = subprocess.run(
                        [
                            powershell,
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(scripts / filename),
                            *arguments,
                        ],
                        check=False,
                        env=env,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(result.returncode, 23, result.stderr)
                    launched = log_path.read_text(encoding="utf-8").splitlines()[-1]
                    self.assertIn(helper, launched)
                    self.assertIn("two words" if filename == "autoreview.ps1" else "--fixture benign", launched)

    @unittest.skipUnless(os.name == "nt", "native PowerShell command discovery test")
    def test_powershell_wrappers_do_not_autoload_modules_for_missing_python(self) -> None:
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        self.assertIsNotNone(powershell, "native PowerShell is required")
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            modules = root / "modules"
            marker = root / "imported.txt"
            log = root / "launch.log"
            for name in ("py", "python3"):
                module = modules / name
                module.mkdir(parents=True)
                (module / f"{name}.psd1").write_text(
                    f"@{{ RootModule = '{name}.psm1'; ModuleVersion = '1.0'; "
                    f"FunctionsToExport = @('{name}') }}", encoding="utf-8",
                )
                (module / f"{name}.psm1").write_text(
                    "[IO.File]::AppendAllText($env:IMPORT_MARKER, 'imported')\n"
                    f"function {name} {{ }}\n", encoding="utf-8",
                )
            python = root / "python.cmd"
            python.write_text(
                "@echo off\r\n"
                'if "%~1"=="-c" exit /b 0\r\n'
                'echo %*>>"%WRAPPER_LOG%"\r\n'
                "exit /b 23\r\n", encoding="utf-8",
            )
            env = {**os.environ, "PATH": str(root), "IMPORT_MARKER": str(marker),
                   "WRAPPER_LOG": str(log),
                   "PSMODULEPATH": os.pathsep.join((str(modules),
                                                    str(Path(powershell).resolve().parent / "Modules"),
                                                    os.environ.get("PSMODULEPATH", "")))}

            def run(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", *args],
                    env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True, timeout=30,
                )

            # Establish that native discovery can import this trap, rather than
            # passing merely because the fixture module is not discoverable.
            control = run("-Command", "Get-Command py -CommandType Application -ErrorAction SilentlyContinue | Out-Null; exit 0")
            self.assertEqual(control.returncode, 0, control.stderr)
            self.assertTrue(marker.exists())
            marker.unlink()

            for filename, args, helper in (
                ("autoreview.ps1", ["--help", "two words"], "autoreview"),
                ("test-review-harness.ps1", ["-Fixture", "benign"], "test-review-harness.py"),
            ):
                with self.subTest(filename=filename):
                    result = run("-File", str(SCRIPT.with_name(filename)), *args)
                    self.assertEqual(result.returncode, 23, result.stderr)
                    self.assertFalse(marker.exists(), "missing executable lookup imported a module")
                    self.assertIn(helper, log.read_text(encoding="utf-8").splitlines()[-1])
            python.unlink()
            for filename in ("autoreview.ps1", "test-review-harness.ps1"):
                with self.subTest(missing_python=filename):
                    result = run("-File", str(SCRIPT.with_name(filename)))
                    self.assertEqual(result.returncode, 127, result.stderr)
                    self.assertIn("Python 3.10 or newer is required", result.stderr)
                    self.assertFalse(marker.exists())

    @unittest.skipIf(os.name == "nt", "POSIX harness wrapper test")
    def test_posix_harness_skips_non_python3_fallbacks(self) -> None:
        harness = SCRIPT.with_name("test-review-harness")
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            log_path = root / "launch.log"
            fake_python3 = bin_dir / "python3"
            fake_python = bin_dir / "python"
            fake_python3.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-c\" ]]; then exit 1; fi\n"
                'printf "python3:%s\\n" "$*" >> "$HARNESS_LOG"\n'
                "exit 91\n",
                encoding="utf-8",
            )
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-c\" ]]; then exit 0; fi\n"
                'printf "python:%s\\n" "$*" >> "$HARNESS_LOG"\n'
                "exit 23\n",
                encoding="utf-8",
            )
            fake_python3.chmod(0o755)
            fake_python.chmod(0o755)

            result = subprocess.run(
                [str(harness), "--help"],
                check=False,
                env={
                    **os.environ,
                    "HARNESS_LOG": str(log_path),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(result.returncode, 23)
            self.assertEqual(
                log_path.read_text(encoding="utf-8").splitlines(),
                [f"python:{harness.with_name('test-review-harness.py')} --help"],
            )

