"""Native Windows test-process proof and portable invocation regression."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest


HELPER_PATH = Path(__file__).with_name("windows_test_process.py").resolve()
HELPER = runpy.run_path(str(HELPER_PATH))


def native_directory_security(path):
    """Report the disposable fixture's owner/DACL without account identifiers."""
    api = HELPER["_windows_api"]()
    c, w = api.c, api.w
    get = api.security.GetFileSecurityW
    get.argtypes = [w.LPCWSTR, w.DWORD, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    get.restype = w.BOOL
    convert = api.security.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), c.POINTER(w.DWORD)]
    convert.restype = w.BOOL
    size = w.DWORD()
    if get(str(path), 5, None, 0, c.byref(size)) or c.get_last_error() != 122:
        raise RuntimeError("cannot size fixture security descriptor")
    descriptor = c.create_string_buffer(size.value)
    if not get(str(path), 5, descriptor, len(descriptor), c.byref(size)):
        raise c.WinError(c.get_last_error())
    get_owner = api.security.GetSecurityDescriptorOwner
    get_owner.argtypes = [c.c_void_p, c.POINTER(c.c_void_p), c.POINTER(w.BOOL)]
    get_owner.restype = w.BOOL
    owner = c.c_void_p()
    defaulted = w.BOOL()
    if not get_owner(descriptor, c.byref(owner), c.byref(defaulted)):
        raise c.WinError(c.get_last_error())
    text = w.LPWSTR()
    if not convert(descriptor, 1, 5, c.byref(text), None):
        raise c.WinError(c.get_last_error())
    try:
        user = HELPER["windows_test_process_status"]()["user_sid"]
        return {"owner_is_user": HELPER["_sid_string"](api, owner) == user,
                "sddl": text.value.replace(user, "<current-user>")}
    finally:
        api.kernel.LocalFree(c.cast(text, c.c_void_p))


def grant_new_fixture_user_access(root, *, inherit=True):
    # Restricted to caller-created empty fixture directories, never source or
    # operator paths. The non-inheriting case exercises token default DACLs.
    assert not list(root.iterdir()), "only a new empty fixture may receive test grants"
    api = HELPER["_windows_api"]()
    c, w = api.c, api.w
    convert = api.security.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.POINTER(w.DWORD)]
    convert.restype = w.BOOL
    apply = api.security.SetFileSecurityW
    apply.argtypes = [w.LPCWSTR, w.DWORD, c.c_void_p]
    apply.restype = w.BOOL
    user = HELPER["windows_test_process_status"]()["user_sid"]
    descriptor = c.c_void_p()
    flags = "OICI" if inherit else ""
    sddl = f"D:P(A;{flags};FA;;;SY)(A;{flags};FA;;;BA)(A;{flags};FA;;;{user})"
    if not convert(sddl, 1, c.byref(descriptor), None):
        raise c.WinError(c.get_last_error())
    try:
        if not apply(str(root), 0x80000004, descriptor):
            raise c.WinError(c.get_last_error())
    finally:
        api.kernel.LocalFree(descriptor)


@contextlib.contextmanager
def cross_token_fixture():
    # Python's Windows mkdir(0700) grants OWNER RIGHTS, which can mean the
    # Administrators group in an elevated parent. Give only this fresh, empty
    # fixture explicit user access before creating files a reduced child reads.
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        original_security = None
        if os.name == "nt":
            original_security = native_directory_security(root)
            grant_new_fixture_user_access(root)
        yield root, original_security


# Test-only diagnostic: reads the token; mutates only an in-memory descriptor.
def token_default_dacl_sddl(helper, token=None):
    import contextlib

    api = helper["_windows_api"]()
    c, w = api.c, api.w
    class SecurityDescriptor(c.Structure):
        _fields_ = [
            ("revision", w.BYTE), ("padding", w.BYTE), ("control", w.WORD),
            ("owner", c.c_void_p), ("group", c.c_void_p),
            ("sacl", c.c_void_p), ("dacl", c.c_void_p),
        ]
    initialize = api.security.InitializeSecurityDescriptor
    initialize.restype = w.BOOL
    initialize.argtypes = [c.c_void_p, w.DWORD]
    set_dacl = api.security.SetSecurityDescriptorDacl
    set_dacl.restype = w.BOOL
    set_dacl.argtypes = [c.c_void_p, w.BOOL, c.c_void_p, w.BOOL]
    convert = api.security.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.restype = w.BOOL
    convert.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), c.POINTER(w.DWORD)]
    scope = helper["_process_token"](api) if token is None else contextlib.nullcontext(token)
    with scope as selected:
        buffer, length = helper["_token_data"](api, selected, 6)  # TokenDefaultDacl
        if length < c.sizeof(c.c_void_p):
            raise RuntimeError("truncated native token default DACL")
        address = c.c_void_p.from_buffer(buffer).value
        if address is None:
            return None
        start = c.addressof(buffer)
        if not start + c.sizeof(c.c_void_p) <= address <= start + length - 8:
            raise RuntimeError("native token default DACL outside its buffer")
        acl_size = int.from_bytes(c.string_at(address + 2, 2), "little")
        if acl_size < 8 or address + acl_size > start + length:
            raise RuntimeError("truncated native token default ACL")
        descriptor = SecurityDescriptor()
        if not initialize(c.byref(descriptor), 1):
            raise c.WinError(c.get_last_error())
        if not set_dacl(c.byref(descriptor), True, address, False):
            raise c.WinError(c.get_last_error())
        text = w.LPWSTR()
        if not convert(c.byref(descriptor), 1, 4, c.byref(text), None):
            raise c.WinError(c.get_last_error())
        try:
            return text.value
        finally:
            api.kernel.LocalFree(c.cast(text, c.c_void_p))


# Object DACL/label are distinct from TokenDefaultDacl and TokenIntegrityLevel.
# This is read-only, including when recording the original elevated caller.
def token_object_security_sddl(helper, token=None):
    api = helper["_windows_api"]()
    c, w = api.c, api.w
    query = api.security.GetKernelObjectSecurity
    query.restype = w.BOOL
    query.argtypes = [w.HANDLE, w.DWORD, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    convert = api.security.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.restype = w.BOOL
    convert.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), c.POINTER(w.DWORD)]
    selected = token
    owned = w.HANDLE()
    if selected is None:
        if not api.security.OpenProcessToken(api.kernel.GetCurrentProcess(), 0x20008, c.byref(owned)):
            raise c.WinError(c.get_last_error())
        selected = owned
    try:
        # LABEL_SECURITY_INFORMATION needs READ_CONTROL, not SeSecurityPrivilege.
        flags = 1 | 4 | 16
        size = w.DWORD()
        result = query(selected, flags, None, 0, c.byref(size))
        if result or c.get_last_error() != 122 or not 0 < size.value <= 1048576:
            raise RuntimeError("cannot size native token object descriptor")
        descriptor = c.create_string_buffer(size.value)
        if not query(selected, flags, descriptor, len(descriptor), c.byref(size)):
            raise c.WinError(c.get_last_error())
        if not 0 < size.value <= len(descriptor):
            raise RuntimeError("invalid native token object descriptor length")
        text = w.LPWSTR()
        # The retrieved SACL contains only the mandatory label, never audit ACEs.
        if not convert(descriptor, 1, 1 | 4 | 8, c.byref(text), None):
            raise c.WinError(c.get_last_error())
        try:
            return text.value
        finally:
            api.kernel.LocalFree(c.cast(text, c.c_void_p))
    finally:
        if owned:
            api.kernel.CloseHandle(owned)


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


if mode == "parent-streams-seed":
    import _winapi
    import subprocess
    # CreateProcessW retains the current primary token without requiring the
    # privilege that CreateProcessAsUser can need for an unreduced token.
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESTDHANDLES
    handles = []
    process = thread = None
    try:
        current = _winapi.GetCurrentProcess()
        for name, identifier, field in (("stdin", -10, "hStdInput"),
                                        ("stdout", -11, "hStdOutput"),
                                        ("stderr", -12, "hStdError")):
            original = api.kernel.GetStdHandle(identifier)
            value = 0
            if original and name not in options[0].split(","):
                value = _winapi.DuplicateHandle(current, original, current, 0, True,
                                               _winapi.DUPLICATE_SAME_ACCESS)
                handles.append(value)
            setattr(startup, field, value)
        startup.lpAttributeList = {"handle_list": handles} if handles else {}
        command = [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
                   helper_path, "parent-streams-subject", receipt_path, *options]
        process, thread, _, _ = _winapi.CreateProcess(
            sys.executable, subprocess.list2cmdline(command), None, None, bool(handles),
            0, None, None, startup,
        )
        if _winapi.WaitForSingleObject(process, 30000) != _winapi.WAIT_OBJECT_0:
            _winapi.TerminateProcess(process, 130)
            _winapi.WaitForSingleObject(process, 5000)
            raise RuntimeError("native parent-stream subject did not exit")
        code = _winapi.GetExitCodeProcess(process)
    finally:
        for handle in (thread, process, *handles):
            if handle is not None:
                _winapi.CloseHandle(handle)
    raise SystemExit(code)

if mode == "parent-streams-subject":
    # The actual unittest reporter needs stderr even for an empty successful
    # suite. The marker is written only after its reporting completes.
    proof = ("import unittest; from pathlib import Path; "
             "unittest.TextTestRunner().run(unittest.TestSuite()); "
             f"Path({receipt_path + '.parent'!r}).write_text('reported'); "
             f"raise SystemExit({int(options[1])})")
    status = helper["ensure_windows_test_process"](
        sys.argv[0], sys.argv[1:],
        parent_check=[sys.executable, "-I", "-S", "-B", "-X", "utf8=1", "-c", proof],
    )
    if status is not None:
        helper["exit_test_process"](status)
    data = {"eligible": helper["windows_test_process_status"]()["eligible"]}
    for name, identifier in (("stdout", -11), ("stderr", -12)):
        data[name] = {"native_null": api.kernel.GetStdHandle(identifier) is None,
                      "python_none": getattr(sys, name) is None}
    Path(receipt_path).write_text(json.dumps(data), encoding="utf-8")
    raise SystemExit(29)


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
    def test_reduced_child_owns_and_uses_private_temporary_directory(self):
        before = HELPER["windows_test_process_status"]()
        parent_default_dacl = token_default_dacl_sddl(HELPER)
        parent_object_security = token_object_security_sddl(HELPER)
        with cross_token_fixture() as (root, _):
            default_acl_root = root / "default-acl-parent"
            default_acl_root.mkdir()
            grant_new_fixture_user_access(default_acl_root, inherit=False)
            script = root / "private-directory-child.py"
            script.write_text(
                "import json, pathlib, runpy, sys, tempfile\n"
                f"proof = runpy.run_path({str(Path(__file__).resolve())!r})\n"
                "helper = proof['HELPER']\n"
                # Manufacture the token even when the calling account already
                # passes admission; its ambient DACL is not what this proves.
                "if len(sys.argv) == 2:\n"
                "    caller = helper['windows_test_process_status']()\n"
                "    caller_dacl = proof['token_default_dacl_sddl'](helper)\n"
                "    caller_object = proof['token_object_security_sddl'](helper)\n"
                "    api = helper['_windows_api']()\n"
                "    with helper['_process_token'](api, for_launch=True) as source:\n"
                "        with helper['_restricted_primary'](api, source) as restricted:\n"
                "            fresh = helper['_status'](api, restricted)['primary_token_id']\n"
                "            assert fresh != caller['primary_token_id']\n"
                "            command = [sys.executable, '-I', '-S', '-B', '-X', 'utf8=1',\n"
                "                       *sys.argv, json.dumps(caller['primary_token_id'])]\n"
                "            status = helper['_launch'](api, restricted, command,\n"
                "                                      helper['_native_environment_block'](api))\n"
                "    assert helper['windows_test_process_status']() == caller\n"
                "    assert proof['token_default_dacl_sddl'](helper) == caller_dacl\n"
                "    assert proof['token_object_security_sddl'](helper) == caller_object\n"
                "    raise SystemExit(status)\n"
                "state = helper['windows_test_process_status']()\n"
                "fresh_primary = state['primary_token_id'] != json.loads(sys.argv[2])\n"
                "assert fresh_primary\n"
                "ordinary = pathlib.Path(sys.argv[1])\n"
                "direct = ordinary / 'default-file.txt'\n"
                "direct.write_text('default file', encoding='utf-8')\n"
                "assert direct.read_text(encoding='utf-8') == 'default file'\n"
                "file_security = proof['native_directory_security'](direct)['owner_is_user']\n"
                "direct.unlink()\n"
                "nested = ordinary / 'default-directory'\n"
                "nested.mkdir()\n"
                "ordinary_security = proof['native_directory_security'](nested)['owner_is_user']\n"
                "direct = nested / 'child.txt'\n"
                "direct.write_text('nested file', encoding='utf-8')\n"
                "assert direct.read_text(encoding='utf-8') == 'nested file'\n"
                "direct.unlink()\n"
                "nested.rmdir()\n"
                "with tempfile.TemporaryDirectory() as directory:\n"
                "    root = pathlib.Path(directory)\n"
                "    security = proof['native_directory_security'](root)['owner_is_user']\n"
                "    item = root / 'ordinary-file.txt'\n"
                "    item.write_text('created', encoding='utf-8')\n"
                "    assert item.read_text(encoding='utf-8') == 'created'\n"
                "    item.write_text('updated', encoding='utf-8')\n"
                "    assert item.read_text(encoding='utf-8') == 'updated'\n"
                "    item.unlink()\n"
                "assert not root.exists()\n"
                "print(json.dumps(dict(eligible=state['eligible'],\n"
                "    fresh_primary=fresh_primary,\n"
                "    owner_is_user=state['owner_sid'] == state['user_sid'],\n"
                "    ordinary_file=file_security, ordinary_directory=ordinary_security,\n"
                "    directory=security, removed=True)))\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-X", "utf8=1", str(script), str(default_acl_root)],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "", "successful native proof must not emit host diagnostics")
            data = json.loads(result.stdout)
            self.assertTrue(data["eligible"])
            self.assertTrue(data["fresh_primary"])
            self.assertTrue(data["owner_is_user"])
            self.assertTrue(data["directory"])
            self.assertTrue(data["ordinary_file"])
            self.assertTrue(data["ordinary_directory"])
            self.assertTrue(data["removed"])
        self.assertTrue(HELPER["windows_test_process_status"]() == before, "parent token state changed")
        self.assertTrue(token_default_dacl_sddl(HELPER) == parent_default_dacl, "parent default DACL changed")
        self.assertTrue(token_object_security_sddl(HELPER) == parent_object_security, "parent token descriptor changed")

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
    def test_direct_runner_self_test_reduces_before_private_fixture_creation(self):
        before = HELPER["windows_test_process_status"]()
        self.assertTrue(before["native"], "this proof requires native Windows")
        self.assertFalse(before["primary_eligible"],
                         "this proof needs the original unsuitable primary token")
        case = "CheckSkillsTest.test_every_group_and_shard_runs_checkout_tests_despite_installed_package"
        # The self-test's own entrypoint must reduce authority before its real
        # fixture creates a private checkout and invokes the copied runner.
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-X", "utf8=1",
             str(Path(__file__).with_name("check-skills.test.py")), case, "-v"],
            text=True, encoding="utf-8", capture_output=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(case.partition(".")[2], result.stderr)
        self.assertRegex(result.stderr, r"(?m)^Ran 1 test in ")
        self.assertNotIn("skipped", result.stderr)
        self.assertTrue(HELPER["windows_test_process_status"]() == before,
                        "parent token state changed")

    def test_parent_reporting_handles_absent_streams_before_real_child_launch(self):
        self.assertFalse(HELPER["windows_test_process_status"]()["eligible"],
                         "this proof needs the original unsuitable primary token")
        for absent, proof_exit in (("stderr", 0), ("stdout,stderr", 0), ("stderr", 7)):
            with self.subTest(absent=absent, proof_exit=proof_exit), cross_token_fixture() as (root, _):
                script = root / "parent-stream-driver.py"
                script.write_text(textwrap.dedent(NATIVE_LAUNCH_DRIVER), encoding="utf-8")
                receipt = root / "child.json"
                result = subprocess.run(
                    [sys.executable, "-I", "-S", "-B", str(script), str(HELPER_PATH),
                     "parent-streams-seed", str(receipt), absent, str(proof_exit)],
                    capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, proof_exit or 29, result.stdout + result.stderr)
                self.assertEqual(Path(str(receipt) + ".parent").read_text(), "reported")
                if proof_exit:
                    self.assertFalse(receipt.exists(), "a failed parent check must prevent child launch")
                    continue
                data = json.loads(receipt.read_text())
                self.assertTrue(data["eligible"])
                for name in ("stdout", "stderr"):
                    self.assertEqual(data[name]["native_null"], name in absent.split(","))
                    self.assertEqual(data[name]["python_none"], name in absent.split(","))

    def test_restricted_thread_cannot_hide_primary_authority(self):
        before = HELPER["windows_test_process_status"]()
        self.assertTrue(before["native"], "this proof requires native Windows")
        self.assertTrue(before["primary_token"])
        self.assertFalse(before["thread_impersonating"])
        self.assertFalse(before["primary_eligible"],
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
            "parent_check=[sys.executable, '-I', '-X', 'utf8=1', '-c', 'raise SystemExit(23)'])\n"
            "raise SystemExit(status if status is not None else 99)\n"
        )
        command = [sys.executable, "-I", "-S", "-c", code, str(Path(__file__).resolve())]
        ordinary = subprocess.run(command, text=True, capture_output=True, timeout=30)
        self.assertEqual(ordinary.returncode, 23, ordinary.stdout + ordinary.stderr)
        forged = subprocess.run(
            command, env={**os.environ, HELPER["_CHILD_MARKER"]: "1"},
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(forged.returncode, 2, forged.stdout + forged.stderr)
        self.assertIn("still has unsuitable native token authority", forged.stderr)


class WindowsTestProcessTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "requires native parent-proof execution")
    def test_auxiliary_utf8_text_uses_the_callers_utf16_streams(self):
        # The isolated proof and requested suite deliberately use different
        # encodings. Both must remain decodable in each redirected caller log.
        with cross_token_fixture() as (root, _):
            script = root / "different-stream-encodings.py"
            script.write_text(
                "import os, runpy, sys\n"
                f"helper = runpy.run_path({str(HELPER_PATH)!r})\n"
                "proof = [sys.executable, '-I', '-S', '-X', 'utf8=1', '-c',\n"
                "         \"import sys; print('proof 雪'); print('proof Ω', file=sys.stderr)\"]\n"
                "status = helper['ensure_windows_test_process'](sys.argv[0], sys.argv[1:], parent_check=proof)\n"
                "if status is not None: helper['exit_test_process'](status)\n"
                "assert os.environ['PYTHONIOENCODING'] == 'utf-16-le'\n"
                "assert sys.flags.warn_default_encoding == 1\n"
                "assert 'error::EncodingWarning' in sys.warnoptions\n"
                "print('caller 雪')\n"
                "print('caller Ω', file=sys.stderr)\n",
                encoding="utf-8",
            )
            environment = {key: value for key, value in os.environ.items()
                           if not key.upper().startswith("PYTHON")}
            environment["PYTHONIOENCODING"] = "utf-16-le"
            result = subprocess.run(
                [sys.executable, "-u", "-S", "-B", "-X", "warn_default_encoding",
                 "-W", "error::EncodingWarning", str(script)],
                env=environment, capture_output=True, timeout=60,
            )
            stdout = result.stdout.decode("utf-16-le").replace("\r\n", "\n")
            stderr = result.stderr.decode("utf-16-le").replace("\r\n", "\n")
            self.assertEqual(result.returncode, 0, stdout + stderr)
            needs_proof = not HELPER["windows_test_process_status"]()["primary_eligible"]
            self.assertEqual(stdout, ("proof 雪\n" if needs_proof else "") + "caller 雪\n")
            self.assertEqual(stderr, ("proof Ω\n" if needs_proof else "") + "caller Ω\n")

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
                        env={**{key: value for key, value in os.environ.items()
                                if not key.upper().startswith("PYTHON")}, "PYTHONINSPECT": "1"},
                        input="raise SystemExit(99)\n", text=True, capture_output=True, timeout=30,
                    )
                    self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, expected)
                    self.assertNotIn(">>>", result.stderr)

    def test_invocation_preserves_interpreter_arguments_streams_and_exit(self):
        # This is a real second process. On Windows it also has to pass native
        # admission, so argument preservation is proved across the actual path.
        with cross_token_fixture() as (root, _):
            script = root / "invocation witness.py"
            script.write_text(
                "import json, os, runpy, sys\n"
                "from pathlib import Path\n"
                f"helper = runpy.run_path({str(HELPER_PATH)!r})\n"
                "proof = [sys.executable, '-I', '-S', '-X', 'utf8=1', '-c',\n"
                "         \"import sys; sys.stdout.write('auxiliary 雪' + chr(10)); sys.stderr.write('auxiliary Ω' + chr(10))\"]\n"
                "status = helper['ensure_windows_test_process'](sys.argv[0], sys.argv[1:], parent_check=proof)\n"
                "if status is not None: helper['exit_test_process'](status)\n"
                "print('stdout witness', flush=True)\n"
                "print('stderr witness', file=sys.stderr, flush=True)\n"
                "data = dict(executable=sys.executable, argv=sys.argv, cwd=os.getcwd(),\n"
                "            environment=os.environ['INVOCATION_WITNESS'],\n"
                "            ambient_python_verbose=os.environ.get('PYTHONVERBOSE'),\n"
                "            no_site=sys.flags.no_site, optimize=sys.flags.optimize,\n"
                "            dont_write_bytecode=sys.flags.dont_write_bytecode,\n"
                "            utf8_mode=sys.flags.utf8_mode, warnings=sys.warnoptions,\n"
                "            warn_default_encoding=sys.flags.warn_default_encoding,\n"
                "            write_through=sys.stdout.write_through,\n"
                "            stdin=sys.stdin.read(), status=helper['windows_test_process_status']())\n"
                "Path(sys.argv[1]).write_text(json.dumps(data), encoding='utf-8')\n"
                "raise SystemExit(17)\n",
                encoding="utf-8",
            )
            output = root / "result.json"
            arguments = [str(output), "space argument", "雪", 'quoted "argument"', "trailing\\", "$literal`value"]
            result = subprocess.run(
                [sys.executable, "-I", "-u", "-S", "-B", "-O", "-X", "utf8", "-X", "warn_default_encoding", "-W", "error",
                 "-W", "error::EncodingWarning", script.name, *arguments],
                cwd=root, env={**os.environ, "INVOCATION_WITNESS": "preserved"},
                input="stdin witness", encoding="utf-8", capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 17, result.stdout + result.stderr)
            needs_proof = os.name == "nt" and not HELPER["windows_test_process_status"]()["primary_eligible"]
            self.assertEqual(result.stdout, ("auxiliary 雪\n" if needs_proof else "") + "stdout witness\n")
            self.assertEqual(result.stderr, ("auxiliary Ω\n" if needs_proof else "") + "stderr witness\n")
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["executable"], sys.executable)
            self.assertEqual(data["argv"], [script.name, *arguments])
            self.assertEqual(Path(data["cwd"]), root)
            self.assertEqual(data["environment"], "preserved")
            self.assertEqual(data["ambient_python_verbose"], os.environ.get("PYTHONVERBOSE"))
            self.assertEqual(data["stdin"], "stdin witness")
            self.assertEqual(data["no_site"], 1)
            self.assertEqual(data["optimize"], 1)
            self.assertEqual(data["dont_write_bytecode"], 1)
            self.assertEqual(data["utf8_mode"], 1)
            self.assertEqual(data["warn_default_encoding"], 1)
            self.assertIn("error::EncodingWarning", data["warnings"])
            self.assertTrue(data["write_through"])
            self.assertIn("error", data["warnings"])
            self.assertEqual(data["status"]["native"], os.name == "nt")
            if os.name == "nt":
                self.assertTrue(data["status"]["eligible"])
                self.assertTrue(data["status"]["primary_token"])
                self.assertFalse(data["status"]["thread_impersonating"])
                self.assertTrue(data["status"]["supported_identity"])
                self.assertLessEqual(data["status"]["integrity_level"], 0x2000)


class AuxiliaryConfigurationTests(unittest.TestCase):
    def test_auxiliary_python_configuration_stays_isolated(self):
        # Run the real witnesses with hostile ambient interpreter settings.
        # The explicit inspect-mode case constructs its own intended setting.
        code = (
            "import runpy, unittest\n"
            f"ns = runpy.run_path({str(Path(__file__).resolve())!r})\n"
            "case = ns['WindowsTestProcessTests']\n"
            "suite = unittest.TestSuite([case('test_invocation_preserves_interpreter_arguments_streams_and_exit'), "
            "case('test_waiting_wrapper_exits_without_an_inspect_prompt')])\n"
            "raise SystemExit(not unittest.TextTestRunner().run(suite).wasSuccessful())\n"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-X", "utf8=1", "-c", code],
            env={**os.environ, "PYTHONVERBOSE": "1", "PYTHONINSPECT": "1", "PYTHONWARNINGS": "error"},
            encoding="utf-8", capture_output=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(os.name == "nt", "requires native primary and thread tokens")
class NativeThreadOnlyTests(unittest.TestCase):
    def test_thread_only_ineligibility_reexecutes_without_privileged_parent_proof(self):
        with cross_token_fixture() as (root, _):
            script = root / "thread-only-caller.py"
            script.write_text(textwrap.dedent(f"""
                import json, os, runpy, sys
                helper = runpy.run_path({str(HELPER_PATH)!r})
                if not os.environ.get('AGENT_SKILLS_TEST_THREAD_STAGE'):
                    status = helper['ensure_windows_test_process'](sys.argv[0], sys.argv[1:])
                    if status is not None:
                        helper['exit_test_process'](status)
                    assert helper['windows_test_process_status']()['eligible']
                    api = helper['_windows_api']()
                    duplicate = api.security.DuplicateToken
                    duplicate.restype = api.w.BOOL
                    duplicate.argtypes = [api.w.HANDLE, api.c.c_int, api.c.POINTER(api.w.HANDLE)]
                    install = api.security.SetThreadToken
                    install.restype = api.w.BOOL
                    install.argtypes = [api.c.POINTER(api.w.HANDLE), api.w.HANDLE]
                    thread = api.w.HANDLE()
                    with helper['_process_token'](api, for_launch=True) as primary:
                        if not duplicate(primary, 2, api.c.byref(thread)):
                            raise api.c.WinError(api.c.get_last_error())
                    installed = False
                    try:
                        if not install(None, thread):
                            raise api.c.WinError(api.c.get_last_error())
                        installed = True
                        before = helper['windows_test_process_status']()
                        assert before['primary_eligible'] and before['thread_impersonating']
                        assert not before['eligible']
                        # Prior successful admission consumed its own retry marker.
                        assert helper['_CHILD_MARKER'] not in os.environ
                        os.environ['AGENT_SKILLS_TEST_THREAD_STAGE'] = '1'
                        status = helper['ensure_windows_test_process'](
                            sys.argv[0], sys.argv[1:],
                            parent_check=[sys.executable, '-I', '-X', 'utf8=1', '-c', 'raise SystemExit(47)'])
                    finally:
                        try:
                            if installed and not install(None, None):
                                raise api.c.WinError(api.c.get_last_error())
                        finally:
                            api.kernel.CloseHandle(thread)
                    if status is not None:
                        helper['exit_test_process'](status)
                    raise AssertionError('thread-only caller did not launch a clean child')
                state = helper['windows_test_process_status']()
                assert state['eligible'] and state['primary_eligible'] and not state['thread_impersonating']
                print('clean thread-only child')
                raise SystemExit(23)
                """), encoding="utf-8")
            result = subprocess.run([sys.executable, "-I", "-S", str(script)],
                                    env={key: value for key, value in os.environ.items()
                                         if key != "AGENT_SKILLS_TEST_THREAD_STAGE"},
                                    text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "clean thread-only child\n")


@unittest.skipUnless(os.name == "nt", "requires native DWORD process exit codes")
class NativeParentExitTests(unittest.TestCase):
    def test_parent_proof_dword_exit_survives_waiting_wrapper(self):
        self.assertFalse(HELPER["windows_test_process_status"]()["primary_eligible"])
        # ExitProcess emits this DWORD without an exception or an actual crash.
        exit_code = (
            "import ctypes; f=ctypes.WinDLL('kernel32').ExitProcess; "
            "f.argtypes=[ctypes.c_ulong]; f.restype=None; f(0xC0000005)"
        )
        code = (
            "import runpy, sys\n"
            f"helper = runpy.run_path({str(HELPER_PATH)!r})\n"
            "status = helper['ensure_windows_test_process'](sys.argv[0], sys.argv[1:], "
            f"parent_check=[sys.executable, '-I', '-S', '-X', 'utf8=1', '-c', {exit_code!r}])\n"
            "helper['exit_test_process'](status if status is not None else 99)\n"
        )
        result = subprocess.run([sys.executable, "-I", "-S", "-c", code],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0xC0000005, result.stdout + result.stderr)


def _lifecycle_native_api(helper):
    api = helper["_windows_api"]()
    for name, result, arguments in (
        ("SetStdHandle", api.w.BOOL, [api.w.DWORD, api.w.HANDLE]),
        ("CreateEventW", api.w.HANDLE,
         [api.c.c_void_p, api.w.BOOL, api.w.BOOL, api.w.LPCWSTR]),
        ("SetEvent", api.w.BOOL, [api.w.HANDLE]),
        ("SetHandleInformation", api.w.BOOL, [api.w.HANDLE, api.w.DWORD, api.w.DWORD]),
        ("GenerateConsoleCtrlEvent", api.w.BOOL, [api.w.DWORD, api.w.DWORD]),
    ):
        function = getattr(api.kernel, name)
        function.restype = result
        function.argtypes = arguments
    return api


def _lifecycle_native_launch(helper, api, arguments, *, interactive=False):
    command = [sys.executable, "-I", "-S", "-B"]
    if interactive:
        command.append("-i")
    command += [str(Path(__file__).resolve()), "--native-lifecycle-leaf", *arguments]
    with helper["_process_token"](api, for_launch=True) as source:
        with helper["_restricted_primary"](api, source) as restricted:
            return helper["_launch"](
                api, restricted, command, helper["_native_environment_block"](api),
            )


def native_lifecycle_driver(arguments):
    mode, helper_path = arguments
    helper = runpy.run_path(helper_path)
    status = helper["ensure_windows_test_process"](sys.argv[0], sys.argv[1:])
    if status is not None:
        helper["exit_test_process"](status)
    api = _lifecycle_native_api(helper)
    # This process is already restricted: its temporary directory belongs to
    # the admitted user, rather than the elevated parent's default owner.
    with tempfile.TemporaryDirectory(prefix="native-lifecycle-") as directory:
        root = Path(directory)
        if mode == "all-null":
            leak = api.kernel.CreateEventW(None, True, False, None)
            if not leak:
                raise api.c.WinError(api.c.get_last_error())
            originals = [(identifier, api.kernel.GetStdHandle(identifier))
                         for identifier in (-10, -11, -12)]
            try:
                if not api.kernel.SetHandleInformation(leak, 1, 1):
                    raise api.c.WinError(api.c.get_last_error())
                for identifier, _ in originals:
                    if not api.kernel.SetStdHandle(identifier, None):
                        raise api.c.WinError(api.c.get_last_error())
                receipt = root / "null-receipt.json"
                status = _lifecycle_native_launch(
                    helper, api, [mode, helper_path, str(receipt), str(leak)],
                )
            finally:
                try:
                    for identifier, original in originals:
                        if not api.kernel.SetStdHandle(identifier, original):
                            raise api.c.WinError(api.c.get_last_error())
                finally:
                    leak_wait = api.kernel.WaitForSingleObject(leak, 0)
                    api.kernel.CloseHandle(leak)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            data.update(exit_status=status, unrelated_event_unsignaled=leak_wait == 258)
            print(json.dumps(data), flush=True)
            return
        if mode != "ctrl-c":
            raise AssertionError("unknown native lifecycle driver mode")
        ready = root / "ready"
        continued = root / "continued"
        stop = threading.Event()
        delivery_errors = []

        def deliver_interrupt():
            deadline = time.monotonic() + 8
            while not stop.wait(0.02):
                if ready.is_file():
                    # The test runner started this driver in a new console.
                    # Group zero therefore cannot signal the runner or a job
                    # sharing its original console.
                    if not api.kernel.GenerateConsoleCtrlEvent(0, 0):
                        delivery_errors.append(api.c.get_last_error())
                    return
                if time.monotonic() >= deadline:
                    delivery_errors.append("child readiness deadline")
                    return

        worker = threading.Thread(target=deliver_interrupt)
        worker.start()
        try:
            status = _lifecycle_native_launch(
                helper, api, [mode, helper_path, str(ready), str(continued)], interactive=True,
            )
        finally:
            stop.set()
            worker.join(timeout=2)
        if worker.is_alive() or delivery_errors:
            raise AssertionError(f"native interrupt delivery failed: {delivery_errors}")
        restored = []
        previous = signal.signal(signal.SIGINT, lambda number, frame: restored.append(number))
        try:
            # A second real event must reach Python after _launch has returned;
            # the temporary wrapper handler must no longer consume Ctrl+C.
            if not api.kernel.GenerateConsoleCtrlEvent(0, 0):
                raise api.c.WinError(api.c.get_last_error())
            deadline = time.monotonic() + 2
            while not restored and time.monotonic() < deadline:
                time.sleep(0.01)
        finally:
            signal.signal(signal.SIGINT, previous)
        print(json.dumps({
            "exit_status": status,
            "child_cleanup": continued.read_text(encoding="utf-8"),
            "wrapper_signal_restored": bool(restored),
        }), flush=True)


def native_lifecycle_leaf(arguments):
    mode, helper_path, *details = arguments
    helper = runpy.run_path(helper_path)
    api = _lifecycle_native_api(helper)
    if mode == "all-null":
        receipt, leak = details
        data = {
            name: {"native_null": api.kernel.GetStdHandle(identifier) is None,
                   "python_none": getattr(sys, name) is None}
            for name, identifier in (("stdin", -10), ("stdout", -11), ("stderr", -12))
        }
        # If the parent's unrelated inheritable event leaked, this signals that
        # same kernel object. Numeric handle reuse cannot produce a false leak:
        # the parent checks its own event object, not this call's return value.
        api.kernel.SetEvent(int(leak))
        Path(receipt).write_text(json.dumps(data), encoding="utf-8")
        raise SystemExit(29)
    if mode != "ctrl-c":
        raise AssertionError("unknown native lifecycle leaf mode")
    ready, continued = map(Path, details)
    try:
        ready.write_text("ready", encoding="utf-8")
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            time.sleep(0.02)
        raise AssertionError("child did not receive native Ctrl+C")
    except KeyboardInterrupt:
        # Slow cleanup makes the old wrapper's unconditional TerminateProcess
        # observable, before Python returns to its real -i prompt.
        time.sleep(0.3)
        continued.write_text("handled Ctrl+C and completed cleanup", encoding="utf-8")
    # Returning normally enters the interpreter's actual interactive prompt.


class NativeLifecycleProofs(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "requires native Windows process creation")
    def test_all_null_launch_excludes_unrelated_inheritable_handle(self):
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
             "--native-lifecycle-driver", "all-null", str(HELPER_PATH)],
            text=True, capture_output=True, timeout=40,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        data = json.loads(result.stdout)
        self.assertEqual(data["exit_status"], 29)
        self.assertTrue(data["unrelated_event_unsignaled"])
        for name in ("stdin", "stdout", "stderr"):
            self.assertEqual(data[name], {"native_null": True, "python_none": True})

    @unittest.skipUnless(os.name == "nt", "requires an isolated native Windows console")
    def test_shared_ctrl_c_keeps_child_interactive_and_restores_wrapper_handler(self):
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
             "--native-lifecycle-driver", "ctrl-c", str(HELPER_PATH)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            input="print('interactive command after Ctrl+C', flush=True); raise SystemExit(37)\n",
            text=True, capture_output=True, timeout=40,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "interactive command after Ctrl+C")
        data = json.loads(lines[1])
        self.assertEqual(data, {
            "exit_status": 37,
            "child_cleanup": "handled Ctrl+C and completed cleanup",
            "wrapper_signal_restored": True,
        })
        self.assertIn(">>>", result.stderr)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--native-lifecycle-driver"]:
        native_lifecycle_driver(sys.argv[2:])
    elif sys.argv[1:2] == ["--native-lifecycle-leaf"]:
        native_lifecycle_leaf(sys.argv[2:])
    else:
        if "--native-parent" in sys.argv:
            suite = unittest.TestSuite([
                unittest.defaultTestLoader.loadTestsFromTestCase(NativeParentTests),
                unittest.defaultTestLoader.loadTestsFromTestCase(NativeParentExitTests),
                unittest.defaultTestLoader.loadTestsFromTestCase(NativeThreadOnlyTests),
                unittest.defaultTestLoader.loadTestsFromTestCase(AuxiliaryConfigurationTests),
                unittest.defaultTestLoader.loadTestsFromTestCase(NativeTokenTests),
                unittest.defaultTestLoader.loadTestsFromTestCase(WindowsTestProcessTests),
            ])
            raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
        status = HELPER["ensure_windows_test_process"](
            sys.argv[0], sys.argv[1:], parent_check=[
                sys.executable, "-u", "-I", "-S", "-B", "-X", "utf8=1",
                str(Path(__file__).resolve()), "--native-parent",
            ],
        )
        if status is not None:
            HELPER["exit_test_process"](status)
        unittest.main(defaultTest=("WindowsTestProcessTests", "AuxiliaryConfigurationTests", "NativeThreadOnlyTests", "TokenPolicyTests", "NativeTokenTests", "NativeLaunchProofs", "NativeLifecycleProofs"), verbosity=2)
