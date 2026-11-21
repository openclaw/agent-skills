#!/usr/bin/env python3
"""Exercise the real macOS tool sandbox, not a mocked Codex verdict."""

import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HELPER = Path(__file__).resolve().parents[1] / "scripts" / "autoreview"


class CodexSandboxPreflightTests(unittest.TestCase):
    def test_linux_checks_selected_installation_inside_tool_sandbox(self):
        helper = runpy.run_path(str(HELPER), run_name="autoreview_under_test")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = str(root / "installed-codex")
            args = type("Args", (), {"codex_bin": binary, "codex_route": None})()
            for sandbox_exit in (0, 1):
                runner = mock.Mock(side_effect=[
                    subprocess.CompletedProcess([], 0, "codex test", ""),
                    subprocess.CompletedProcess([], sandbox_exit, "", "sandbox denied"),
                ])
                with self.subTest(sandbox_exit=sandbox_exit), \
                        mock.patch.object(sys, "platform", "linux"), \
                        mock.patch.dict(helper["ensure_codex_isolation_supported"].__globals__, {
                            "resolve_command": mock.Mock(return_value=binary),
                            "safe_temp_root": mock.Mock(return_value=root),
                            "codex_route_selector": mock.Mock(return_value=None),
                            "codex_runtime_env": mock.Mock(return_value={"SYNTHETIC": "isolated"}),
                            "codex_file_auth_source": mock.Mock(return_value=None),
                            "run": runner,
                        }):
                    if sandbox_exit:
                        with self.assertRaisesRegex(SystemExit, "Codex tool sandbox preflight failed"):
                            helper["ensure_codex_isolation_supported"](args, root)
                    else:
                        self.assertEqual(helper["ensure_codex_isolation_supported"](args, root), binary)
                    calls = runner.call_args_list
                    self.assertEqual(len(calls), 2)
                    command = calls[1].args[0]
                    self.assertEqual(command[:2], [binary, "sandbox"])
                    self.assertEqual(command[-3:], ["--", binary, "--version"])
                    self.assertIn('permissions.autoreview.filesystem={":minimal"="read",":workspace_roots"="read"}', command)
                    self.assertEqual(calls[1].kwargs["env"], {"SYNTHETIC": "isolated"})


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("codex"), "requires macOS and Codex")
class CodexSandboxTests(unittest.TestCase):
    def test_shared_scratch_is_denied_but_workspace_remains_read_only(self):
        helper = runpy.run_path(str(HELPER), run_name="autoreview_under_test")
        private_temp_root = Path(tempfile.gettempdir()).resolve()
        for scratch_root in ("/private/tmp", "/private/var/tmp"):
            self.assertFalse(
                private_temp_root.is_relative_to(scratch_root),
                "sandbox positive control requires the macOS private temporary directory",
            )
        for scratch_root in ("/private/tmp", "/private/var/tmp"):
            with (
                self.subTest(root=scratch_root),
                tempfile.TemporaryDirectory(
                    prefix="autoreview-sandbox-test.", dir=private_temp_root,
                ) as private_temp,
                tempfile.TemporaryDirectory(
                    prefix="autoreview-scratch-test.", dir=scratch_root,
                ) as scratch,
            ):
                root = Path(private_temp).resolve()
                workspace = root / "workspace"
                workspace.mkdir()
                inside = workspace / "inside.txt"
                outside = Path(scratch) / "outside.txt"
                inside.write_text("owned inside\n")
                outside.write_text("owned outside\n")
                flags = helper["codex_config_isolation_flags"](workspace, root / "runtime")
                runtime = root / "runtime"
                token = "synthetic-sandbox-route-token"
                route = helper["CodexInferenceRoute"]([
                    "-c", 'model_provider="synthetic_route"',
                ], None, token)
                auth_flags = helper["prepare_codex_inference_config"](route, runtime)
                # Native client command auth can read it; reviewer tools cannot.
                import json
                settings = dict(item.split("=", 1) for item in auth_flags[1::2])
                prefix = "model_providers.synthetic_route.auth."
                reader = [json.loads(settings[prefix + "command"]), *json.loads(settings[prefix + "args"])]
                credential = subprocess.run(reader, capture_output=True, check=True, timeout=10)
                self.assertEqual(credential.stdout.decode(), token)
                runtime_file = runtime / "route-token"
                scratch_link = workspace / "scratch-link"
                scratch_link.symlink_to(outside)
                runtime_link = workspace / "runtime-link"
                runtime_link.symlink_to(runtime_file)
                alias = Path(str(outside).removeprefix("/private"))
                for path in (outside, alias, scratch_link):
                    self.assertEqual(path.read_text(), "owned outside\n")
                self.assertEqual(runtime_link.read_text(), token)
                subprocess.run(
                    ["/bin/ls", "-f", scratch_root], check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                )
                result = subprocess.run(
                    [
                        shutil.which("codex"), "sandbox", "--include-managed-config",
                        "--permission-profile", "autoreview", *flags, "-C", str(workspace),
                        "--", "/bin/sh", "-c",
                        '''
                        fail=0
                        test "$(cat "$1")" = "owned inside" || fail=1
                        if cat "$2" >/dev/null; then echo outside-read-allowed; fail=1; fi
                        if cat "$3" >/dev/null; then echo alias-read-allowed; fail=1; fi
                        if ls -f "$4" >/dev/null; then echo root-list-allowed; fail=1; fi
                        if (printf unexpected >> "$2"); then echo outside-write-allowed; fail=1; fi
                        if (printf unexpected >> "$1"); then echo inside-write-allowed; fail=1; fi
                        if touch "$5"; then echo outside-create-allowed; fail=1; fi
                        if cat "$6" >/dev/null; then echo scratch-link-read-allowed; fail=1; fi
                        if cat "$7" >/dev/null; then echo runtime-link-read-allowed; fail=1; fi
                        exit "$fail"
                        ''',
                        "sandbox-test", str(inside), str(outside), str(alias), scratch_root,
                        str(Path(scratch) / "created"), str(scratch_link), str(runtime_link),
                    ],
                    capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(inside.read_text(), "owned inside\n")
                self.assertEqual(outside.read_text(), "owned outside\n")
                self.assertEqual(runtime_file.read_text(), token)
                self.assertFalse((Path(scratch) / "created").exists())


if __name__ == "__main__":
    unittest.main()
