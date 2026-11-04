"""Native Windows test-process proof and portable invocation regression."""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import textwrap
import unittest


HELPER_PATH = Path(__file__).with_name("windows_test_process.py").resolve()
HELPER = runpy.run_path(str(HELPER_PATH))


NATIVE_LAUNCH_DRIVER = r'''
import json
import runpy
import sys
from pathlib import Path

helper_path, mode, receipt_path, *options = sys.argv[1:]
helper = runpy.run_path(helper_path)
api = helper["_windows_api"]()


def raw_entries():
    # Observe the child's actual OS environment without applying the helper's
    # transformation a second time. Never serialize unrelated environment data.
    address = api.kernel.GetEnvironmentStringsW()
    if not address:
        raise api.c.WinError(api.c.get_last_error())
    try:
        units = api.c.cast(address, api.c.POINTER(api.c.c_uint16))
        length = 0
        while units[length] or units[length + 1]:
            length += 1
        block = api.c.string_at(address, (length + 2) * 2)
    finally:
        api.kernel.FreeEnvironmentStringsW(address)
    return block.decode("utf-16-le", "surrogatepass").split("\0")[:-2]


def synthetic_values():
    marker = helper["_CHILD_MARKER"]
    entries = raw_entries()
    return {
        "drive": [entry for entry in entries if entry.startswith("=Q:=")],
        "marker": [entry for entry in entries
                   if entry.partition("=")[0].upper() == marker.upper()],
        "marker_family": [entry for entry in entries
                          if entry.partition("=")[0].upper() in (marker.upper(), marker.upper() + "0")],
    }


def launch(next_mode, block, extra=()):
    command = [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
               helper_path, next_mode, receipt_path, *extra]
    with helper["_process_token"](api, for_launch=True) as source:
        with helper["_restricted_primary"](api, source) as restricted:
            return helper["_launch"](api, restricted, command, block)


if mode == "environment-seed":
    marker = helper["_CHILD_MARKER"]
    entries = [entry for entry in raw_entries()
               if not entry.startswith("=Q:=")
               and entry.partition("=")[0].upper() not in (marker.upper(), marker.upper() + "0")]
    entries += ["=Q:=Q:\\agent-skills-native-proof", marker.lower() + "=stale", marker + "0=control"]
    # The controlled entries are ASCII; ordinal sorting retains the documented
    # native environment ordering without exposing any ambient values.
    compare = api.kernel.CompareStringOrdinal
    from functools import cmp_to_key
    def order(left, right):
        left = left[:left.index("=", 1 if left.startswith("=") else 0)]
        right = right[:right.index("=", 1 if right.startswith("=") else 0)]
        result = compare(left, -1, right, -1, True)
        if not result:
            raise api.c.WinError(api.c.get_last_error())
        return result - 2
    entries.sort(key=cmp_to_key(order))
    block = ("\0".join(entries) + "\0\0").encode("utf-16-le", "surrogatepass")
    raise SystemExit(launch("environment-forward", block))

if mode == "environment-forward":
    before = synthetic_values()
    Path(receipt_path + ".seed").write_text(json.dumps(before), encoding="utf-8")
    raise SystemExit(launch("environment-leaf", helper["_native_environment_block"](api)))

if mode == "environment-leaf":
    Path(receipt_path).write_text(json.dumps(synthetic_values()), encoding="utf-8")
    raise SystemExit(29)

if mode in ("streams-seed", "streams-invalid"):
    setter = api.kernel.SetStdHandle
    setter.argtypes = [api.w.DWORD, api.w.HANDLE]
    setter.restype = api.w.BOOL
    if mode == "streams-invalid":
        if not setter(-11, api.c.c_void_p(-1).value):
            raise api.c.WinError(api.c.get_last_error())
        try:
            launch("streams-leaf", helper["_native_environment_block"](api))
        except RuntimeError as error:
            data = {"type": type(error).__name__, "message": str(error)}
            Path(receipt_path + ".rejected").write_text(json.dumps(data), encoding="utf-8")
            raise SystemExit(31)
        raise AssertionError("invalid native stdout handle was accepted")
    absent = options[0].split(",")
    for name, identifier in (("stdin", -10), ("stdout", -11), ("stderr", -12)):
        if name in absent and not setter(identifier, None):
            raise api.c.WinError(api.c.get_last_error())
    raise SystemExit(launch("streams-leaf", helper["_native_environment_block"](api)))

if mode == "streams-leaf":
    # These streams were initialized by Python from the real inherited native
    # handles. None is observed here, rather than assigned to fake the result.
    data = {}
    for name, identifier in (("stdin", -10), ("stdout", -11), ("stderr", -12)):
        data[name] = {
            "native_null": api.kernel.GetStdHandle(identifier) is None,
            "python_none": getattr(sys, name) is None,
        }
    if sys.stdin is not None:
        data["input"] = sys.stdin.read()
    if sys.stdout is not None:
        print("retained stdout")
    if sys.stderr is not None:
        print("retained stderr", file=sys.stderr)
    helper["_flush_standard_streams"]()
    Path(receipt_path).write_text(json.dumps(data), encoding="utf-8")
    raise SystemExit(29)

raise AssertionError("unknown native proof mode")
'''


class NativeLaunchProofs(unittest.TestCase):
    def run_driver(self, root, mode, *options, expected_exit=29, receipt_suffix=""):
        script = root / "native-boundary-driver.py"
        script.write_text(textwrap.dedent(NATIVE_LAUNCH_DRIVER), encoding="utf-8")
        receipt = root / "receipt.json"
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(script), str(HELPER_PATH),
             mode, str(receipt), *options],
            input="retained stdin", text=True, capture_output=True, timeout=60,
        )
        self.assertEqual(result.returncode, expected_exit, result.stdout + result.stderr)
        result_path = Path(str(receipt) + receipt_suffix)
        return result, json.loads(result_path.read_text(encoding="utf-8")), receipt

    @unittest.skipUnless(os.name == "nt", "requires native Windows process creation")
    def test_native_environment_retains_hidden_drive_and_replaces_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            _, after, receipt = self.run_driver(Path(directory), "environment-seed")
            before = json.loads(Path(str(receipt) + ".seed").read_text(encoding="utf-8"))
            expected_drive = ["=Q:=Q:\\agent-skills-native-proof"]
            marker = "AGENT_SKILLS_WINDOWS_TEST_CHILD"
            self.assertEqual(before["drive"], expected_drive)
            self.assertEqual(before["marker"], [marker.lower() + "=stale"])
            self.assertEqual(after["drive"], expected_drive)
            self.assertEqual(after["marker"], [marker + "=1"])
            self.assertEqual(after["marker_family"], [marker + "=1", marker + "0=control"])

    @unittest.skipUnless(os.name == "nt", "requires native Windows process creation")
    def test_native_launch_preserves_null_standard_handles(self):
        # The all-absent case also covers creation without an inherited handle
        # list. Other cases prove that present streams still carry real data.
        for absent in (("stdin",), ("stdout",), ("stdin", "stdout", "stderr")):
            with self.subTest(absent=absent), tempfile.TemporaryDirectory() as directory:
                result, data, _ = self.run_driver(
                    Path(directory), "streams-seed", ",".join(absent),
                )
                for name in ("stdin", "stdout", "stderr"):
                    self.assertEqual(data[name]["native_null"], name in absent, name)
                    self.assertEqual(data[name]["python_none"], name in absent, name)
                if "stdin" not in absent:
                    self.assertEqual(data["input"], "retained stdin")
                self.assertEqual(result.stdout, "" if "stdout" in absent else "retained stdout\n")
                self.assertEqual(result.stderr, "" if "stderr" in absent else "retained stderr\n")

    @unittest.skipUnless(os.name == "nt", "requires native Windows process creation")
    def test_native_launch_rejects_invalid_standard_handle_before_child(self):
        with tempfile.TemporaryDirectory() as directory:
            result, data, receipt = self.run_driver(
                Path(directory), "streams-invalid", expected_exit=31, receipt_suffix=".rejected",
            )
            self.assertEqual(data, {
                "type": "RuntimeError", "message": "native stdout handle is invalid",
            })
            self.assertFalse(receipt.exists(), "an invalid native handle must prevent child launch")
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")


class TokenPolicyTests(unittest.TestCase):
    def test_service_identities_do_not_become_supported_by_removing_groups(self):
        for sid in ("S-1-5-18", "S-1-5-19", "S-1-5-20", "S-1-5-80-1-2-3-4-5",
                    "S-1-5-82-1-2-3-4-5", "S-1-16-8192"):
            with self.subTest(sid=sid):
                self.assertFalse(HELPER["_supported_identity"](sid))
        self.assertTrue(HELPER["_supported_identity"]("S-1-5-21-111-222-333-1001"))
        self.assertTrue(HELPER["_supported_identity"]("S-1-12-1-111-222-333-444"))

    def test_only_verified_account_domain_users_gets_ordinary_grants(self):
        users = "S-1-5-21-111-222-333-513"
        classify = HELPER["_ordinary_group"]
        self.assertFalse(classify(users, 4))
        self.assertTrue(classify(users, 4, users))
        for sid in ("S-1-5-21-111-222-333-512", "S-1-5-21-111-222-333-519",
                    "S-1-5-21-444-555-666-513", "S-1-5-32-544"):
            with self.subTest(sid=sid):
                self.assertFalse(classify(sid, 4, users))


@unittest.skipUnless(os.name == "nt", "native Windows token APIs required")
class NativeTokenTests(unittest.TestCase):
    def test_status_handle_can_query_but_cannot_duplicate_token(self):
        api = HELPER["_windows_api"]()
        with HELPER["_process_token"](api) as token:
            self.assertTrue(HELPER["_status"](api, token)["primary_token"])
            duplicate = api.w.HANDLE()
            created = api.security.CreateRestrictedToken(
                token, 0, 0, None, 0, None, 0, None, api.c.byref(duplicate),
            )
            error = api.c.get_last_error()
            if duplicate:
                api.kernel.CloseHandle(duplicate)
            self.assertFalse(created, "read-only inspection must not request TOKEN_DUPLICATE")
            self.assertEqual(error, 5)  # ERROR_ACCESS_DENIED for missing handle rights.

    def test_new_primary_lowers_integrity_and_preserves_parent_identity(self):
        api = HELPER["_windows_api"]()
        before = HELPER["windows_test_process_status"]()
        self.assertTrue(before["supported_identity"], "use a supported account for this native proof")
        with HELPER["_process_token"](api, for_launch=True) as source:
            with HELPER["_restricted_primary"](api, source) as restricted:
                after = HELPER["_status"](api, restricted)
                self.assertTrue(after["primary_token"])
                self.assertEqual(after["user_sid"], before["user_sid"])
                self.assertEqual(after["domain_users_sid"], before["domain_users_sid"])
                self.assertNotEqual(after["primary_token_id"], before["primary_token_id"])
                self.assertEqual(after["integrity_level"], min(before["integrity_level"], 0x2000))
                self.assertEqual(after["nonordinary_privileges"], 0)
                self.assertEqual(after["nonordinary_groups"], 0)
        self.assertEqual(HELPER["windows_test_process_status"](), before)

    def test_enabled_account_domain_users_survives_restriction(self):
        api = HELPER["_windows_api"]()
        with HELPER["_process_token"](api, for_launch=True) as source:
            _, users_sid = HELPER["_token_identity"](api, source)
            def groups(token):
                buffer, entries = HELPER["_token_entries"](
                    api, token, 2, api.SidAndAttributes, api.TokenGroups.groups.offset,
                )
                return {HELPER["_sid_string"](api, entry.sid): entry.attributes for entry in entries}
            original = groups(source)
            if users_sid is None or not original.get(users_sid, 0) & 4:
                self.skipTest("requires an actual enabled account-domain Users membership")
            with HELPER["_restricted_primary"](api, source) as restricted:
                reduced = groups(restricted)
                self.assertTrue(reduced.get(users_sid, 0) & 4)
                self.assertFalse(reduced[users_sid] & 0x10)


class NativeParentTests(unittest.TestCase):
    def test_restricted_thread_cannot_hide_primary_authority(self):
        before = HELPER["windows_test_process_status"]()
        self.assertTrue(before["native"], "this proof requires native Windows")
        self.assertTrue(before["primary_token"])
        self.assertFalse(before["thread_impersonating"])
        self.assertTrue(before["nonordinary_privileges"] or before["nonordinary_groups"]
                        or before["integrity_level"] > 0x2000,
                        "parent proof requires the original nonordinary primary token")
        self.assertFalse(before["eligible"])
        api = HELPER["_windows_api"]()
        duplicate = api.security.DuplicateToken
        duplicate.restype = api.w.BOOL
        duplicate.argtypes = [api.w.HANDLE, api.c.c_int, api.c.POINTER(api.w.HANDLE)]
        install = api.security.SetThreadToken
        install.restype = api.w.BOOL
        install.argtypes = [api.c.POINTER(api.w.HANDLE), api.w.HANDLE]
        with HELPER["_process_token"](api, for_launch=True) as source:
            with HELPER["_restricted_primary"](api, source) as restricted:
                impersonation = api.w.HANDLE()
                if not duplicate(restricted, 2, api.c.byref(impersonation)):
                    raise api.c.WinError(api.c.get_last_error())
                installed = False
                try:
                    if not install(None, impersonation):
                        raise api.c.WinError(api.c.get_last_error())
                    installed = True
                    # Restricting only the thread cannot erase the authority
                    # available by reverting to the original primary token.
                    during = HELPER["windows_test_process_status"]()
                    self.assertTrue(during["thread_impersonating"])
                    self.assertFalse(during["eligible"])
                    self.assertEqual(during["primary_token_id"], before["primary_token_id"])
                    self.assertEqual(during["nonordinary_privileges"], before["nonordinary_privileges"])
                    self.assertEqual(during["nonordinary_groups"], before["nonordinary_groups"])
                finally:
                    try:
                        if installed and not install(None, None):
                            raise api.c.WinError(api.c.get_last_error())
                    finally:
                        api.kernel.CloseHandle(impersonation)
        self.assertEqual(HELPER["windows_test_process_status"](), before)

    def test_marker_cannot_admit_parent_and_parent_check_failure_propagates(self):
        self.assertFalse(HELPER["windows_test_process_status"]()["eligible"])
        code = (
            "import runpy, sys\n"
            f"helper = runpy.run_path({str(HELPER_PATH)!r})\n"
            "status = helper['ensure_windows_test_process'](sys.argv[1], [], "
            "parent_check=[sys.executable, '-c', 'raise SystemExit(23)'])\n"
            "raise SystemExit(status if status is not None else 99)\n"
        )
        command = [sys.executable, "-S", "-c", code, str(Path(__file__).resolve())]
        ordinary = subprocess.run(command, text=True, capture_output=True, timeout=30)
        self.assertEqual(ordinary.returncode, 23, ordinary.stdout + ordinary.stderr)
        forged = subprocess.run(
            command, env={**os.environ, HELPER["_CHILD_MARKER"]: "1"},
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(forged.returncode, 2, forged.stdout + forged.stderr)
        self.assertIn("still has unsuitable native token authority", forged.stderr)


class WindowsTestProcessTests(unittest.TestCase):
    def test_waiting_wrapper_exits_without_an_inspect_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "waiting-wrapper.py"
            script.write_text(
                "import runpy, sys\n"
                f"helper = runpy.run_path({str(HELPER_PATH)!r})\n"
                "if '--absent-streams' in sys.argv:\n"
                "    sys.stdout = sys.stderr = None\n"
                "else:\n"
                "    print('flushed wrapper output')\n"
                "helper['exit_test_process'](23)\n",
                encoding="utf-8",
            )
            for flags, extra, expected in [
                (["-i"], [], "flushed wrapper output\n"),
                ([], [], "flushed wrapper output\n"),
                (["-i"], ["--absent-streams"], ""),
            ]:
                with self.subTest(flags=flags, absent_streams=bool(extra)):
                    result = subprocess.run(
                        [sys.executable, "-S", *flags, str(script), *extra],
                        env={**os.environ, "PYTHONINSPECT": "1"},
                        input="raise SystemExit(99)\n", text=True, capture_output=True, timeout=30,
                    )
                    self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, expected)
                    self.assertNotIn(">>>", result.stderr)

    def test_invocation_preserves_interpreter_arguments_streams_and_exit(self):
        # This is a real second process. On Windows it also has to pass native
        # admission, so argument preservation is proved across the actual path.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "invocation witness.py"
            script.write_text(
                "import json, os, runpy, sys\n"
                "from pathlib import Path\n"
                f"helper = runpy.run_path({str(HELPER_PATH)!r})\n"
                "status = helper['ensure_windows_test_process'](sys.argv[0], sys.argv[1:])\n"
                "if status is not None: helper['exit_test_process'](status)\n"
                "print('stdout witness', flush=True)\n"
                "print('stderr witness', file=sys.stderr, flush=True)\n"
                "data = dict(executable=sys.executable, argv=sys.argv, cwd=os.getcwd(),\n"
                "            environment=os.environ['INVOCATION_WITNESS'],\n"
                "            no_site=sys.flags.no_site, optimize=sys.flags.optimize,\n"
                "            dont_write_bytecode=sys.flags.dont_write_bytecode,\n"
                "            utf8_mode=sys.flags.utf8_mode, warnings=sys.warnoptions,\n"
                "            write_through=sys.stdout.write_through,\n"
                "            stdin=sys.stdin.read(), status=helper['windows_test_process_status']())\n"
                "Path(sys.argv[1]).write_text(json.dumps(data), encoding='utf-8')\n"
                "raise SystemExit(17)\n",
                encoding="utf-8",
            )
            output = root / "result.json"
            arguments = [str(output), "space argument", "雪", 'quoted "argument"', "trailing\\", "$literal`value"]
            result = subprocess.run(
                [sys.executable, "-u", "-S", "-B", "-O", "-X", "utf8", "-W", "error", script.name, *arguments],
                cwd=root, env={**os.environ, "INVOCATION_WITNESS": "preserved"},
                input="stdin witness", text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 17, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "stdout witness\n")
            self.assertEqual(result.stderr, "stderr witness\n")
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["executable"], sys.executable)
            self.assertEqual(data["argv"], [script.name, *arguments])
            self.assertEqual(Path(data["cwd"]), root)
            self.assertEqual(data["environment"], "preserved")
            self.assertEqual(data["stdin"], "stdin witness")
            self.assertEqual(data["no_site"], 1)
            self.assertEqual(data["optimize"], 1)
            self.assertEqual(data["dont_write_bytecode"], 1)
            self.assertEqual(data["utf8_mode"], 1)
            self.assertTrue(data["write_through"])
            self.assertIn("error", data["warnings"])
            self.assertEqual(data["status"]["native"], os.name == "nt")
            if os.name == "nt":
                self.assertTrue(data["status"]["eligible"])
                self.assertTrue(data["status"]["primary_token"])
                self.assertFalse(data["status"]["thread_impersonating"])
                self.assertTrue(data["status"]["supported_identity"])
                self.assertLessEqual(data["status"]["integrity_level"], 0x2000)


if __name__ == "__main__":
    if "--native-parent" in sys.argv:
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromTestCase(NativeParentTests),
            unittest.defaultTestLoader.loadTestsFromTestCase(NativeTokenTests),
            unittest.defaultTestLoader.loadTestsFromTestCase(WindowsTestProcessTests),
        ])
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    status = HELPER["ensure_windows_test_process"](
        sys.argv[0], sys.argv[1:], parent_check=[
            sys.executable, "-u", "-I", "-S", "-B",
            str(Path(__file__).resolve()), "--native-parent",
        ],
    )
    if status is not None:
        HELPER["exit_test_process"](status)
    unittest.main(defaultTest=("WindowsTestProcessTests", "TokenPolicyTests", "NativeTokenTests", "NativeLaunchProofs"), verbosity=2)
