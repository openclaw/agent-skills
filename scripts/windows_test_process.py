"""Run native Windows repository tests with a restricted primary token.

This prepares a test process, not a sandbox for hostile programs. Admission is
based on native token state; an environment marker only stops retry loops.
"""
from __future__ import annotations

import contextlib
import functools
import os
from pathlib import Path
import re
import subprocess
import sys


_CHILD_MARKER = "AGENT_SKILLS_WINDOWS_TEST_CHILD"
_MEDIUM_INTEGRITY = 0x2000
_ORDINARY_PRIVILEGES = (
    "SeChangeNotifyPrivilege", "SeShutdownPrivilege", "SeUndockPrivilege",
    "SeIncreaseWorkingSetPrivilege", "SeTimeZonePrivilege",
)
_ORDINARY_GROUPS = frozenset({
    "S-1-1-0",       # Everyone
    "S-1-2-0",       # Local
    "S-1-2-1",       # Console logon
    "S-1-5-4",       # Interactive
    "S-1-5-11",      # Authenticated Users
    "S-1-5-14",      # Remote Interactive Logon
    "S-1-5-15",      # This Organization
    "S-1-5-32-545",  # Builtin Users
    "S-1-5-64-10",   # NTLM Authentication
    "S-1-5-113",     # Local Account
})


def _supported_identity(sid: str) -> bool:
    # TokenUser must belong to the local/domain or Entra account namespace.
    # SYSTEM and virtual services retain intrinsic identity grants after token
    # restriction. Domain service accounts are ordinary account identities;
    # this does not claim to identify how those accounts are used.
    return bool(re.fullmatch(r"S-1-(?:5-21|12-1)(?:-\d+){4}", sid))


def _ordinary_group(sid: str, attributes: int, domain_users_sid: str | None = None) -> bool:
    if sid in _ORDINARY_GROUPS or sid == domain_users_sid:
        return True
    if attributes & 0x20 and re.fullmatch(r"S-1-16-\d+", sid):
        return True  # Integrity label, not a discretionary grant.
    return bool(attributes & 0xC0000000 == 0xC0000000
                and re.fullmatch(r"S-1-5-5-\d+-\d+", sid))


@functools.cache
def _windows_api():
    # Import native modules only when needed. Cache declarations, never tokens.
    import ctypes as c
    from ctypes import wintypes as w

    class Luid(c.Structure):
        _fields_ = [("low", w.DWORD), ("high", w.LONG)]

    class LuidAndAttributes(c.Structure):
        _fields_ = [("luid", Luid), ("attributes", w.DWORD)]

    class SidAndAttributes(c.Structure):
        _fields_ = [("sid", c.c_void_p), ("attributes", w.DWORD)]

    class TokenGroups(c.Structure):
        _fields_ = [("count", w.DWORD), ("groups", SidAndAttributes * 1)]

    class StartupInfo(c.Structure):
        _fields_ = [
            ("cb", w.DWORD), ("reserved", w.LPWSTR), ("desktop", w.LPWSTR),
            ("title", w.LPWSTR), ("x", w.DWORD), ("y", w.DWORD),
            ("x_size", w.DWORD), ("y_size", w.DWORD),
            ("x_chars", w.DWORD), ("y_chars", w.DWORD),
            ("fill", w.DWORD), ("flags", w.DWORD), ("show", w.WORD),
            ("reserved_size", w.WORD), ("reserved_data", c.c_void_p),
            ("stdin", w.HANDLE), ("stdout", w.HANDLE), ("stderr", w.HANDLE),
        ]

    class StartupInfoEx(c.Structure):
        _fields_ = [("startup", StartupInfo), ("attributes", c.c_void_p)]

    class ProcessInfo(c.Structure):
        _fields_ = [("process", w.HANDLE), ("thread", w.HANDLE),
                    ("process_id", w.DWORD), ("thread_id", w.DWORD)]

    class Api:
        pass

    api = Api()
    api.c, api.w = c, w
    api.Luid = Luid
    api.LuidAndAttributes = LuidAndAttributes
    api.SidAndAttributes = SidAndAttributes
    api.TokenGroups = TokenGroups
    api.StartupInfoEx = StartupInfoEx
    api.ProcessInfo = ProcessInfo
    api.kernel = c.WinDLL("kernel32", use_last_error=True)
    api.security = c.WinDLL("advapi32", use_last_error=True)

    def bind(library, name, result, *arguments):
        function = getattr(library, name)
        function.restype = result
        function.argtypes = list(arguments)

    handle_pointer = c.POINTER(w.HANDLE)
    dword_pointer = c.POINTER(w.DWORD)
    bind(api.kernel, "GetCurrentProcess", w.HANDLE)
    bind(api.kernel, "GetCurrentThread", w.HANDLE)
    bind(api.kernel, "CloseHandle", w.BOOL, w.HANDLE)
    bind(api.kernel, "LocalFree", c.c_void_p, c.c_void_p)
    bind(api.kernel, "GetStdHandle", w.HANDLE, w.DWORD)
    bind(api.kernel, "GetEnvironmentStringsW", c.c_void_p)
    bind(api.kernel, "FreeEnvironmentStringsW", w.BOOL, c.c_void_p)
    bind(api.kernel, "CompareStringOrdinal", c.c_int, w.LPCWSTR, c.c_int, w.LPCWSTR, c.c_int, w.BOOL)
    bind(api.kernel, "DuplicateHandle", w.BOOL, w.HANDLE, w.HANDLE,
         w.HANDLE, handle_pointer, w.DWORD, w.BOOL, w.DWORD)
    bind(api.kernel, "InitializeProcThreadAttributeList", w.BOOL,
         c.c_void_p, w.DWORD, w.DWORD, c.POINTER(c.c_size_t))
    bind(api.kernel, "UpdateProcThreadAttribute", w.BOOL, c.c_void_p,
         w.DWORD, c.c_size_t, c.c_void_p, c.c_size_t, c.c_void_p, c.c_void_p)
    bind(api.kernel, "DeleteProcThreadAttributeList", None, c.c_void_p)
    bind(api.kernel, "WaitForSingleObject", w.DWORD, w.HANDLE, w.DWORD)
    bind(api.kernel, "GetExitCodeProcess", w.BOOL, w.HANDLE, dword_pointer)
    bind(api.kernel, "TerminateProcess", w.BOOL, w.HANDLE, w.UINT)
    bind(api.security, "OpenProcessToken", w.BOOL, w.HANDLE, w.DWORD, handle_pointer)
    bind(api.security, "OpenThreadToken", w.BOOL, w.HANDLE, w.DWORD, w.BOOL, handle_pointer)
    bind(api.security, "GetTokenInformation", w.BOOL, w.HANDLE,
         c.c_int, c.c_void_p, w.DWORD, dword_pointer)
    bind(api.security, "SetTokenInformation", w.BOOL, w.HANDLE,
         c.c_int, c.c_void_p, w.DWORD)
    bind(api.security, "GetWindowsAccountDomainSid", w.BOOL,
         c.c_void_p, c.c_void_p, dword_pointer)
    bind(api.security, "CreateWellKnownSid", w.BOOL,
         c.c_int, c.c_void_p, c.c_void_p, dword_pointer)
    bind(api.security, "LookupPrivilegeValueW", w.BOOL,
         w.LPCWSTR, w.LPCWSTR, c.POINTER(Luid))
    bind(api.security, "ConvertSidToStringSidW", w.BOOL, c.c_void_p, c.POINTER(w.LPWSTR))
    bind(api.security, "CreateRestrictedToken", w.BOOL, w.HANDLE, w.DWORD,
         w.DWORD, c.POINTER(SidAndAttributes), w.DWORD, c.POINTER(LuidAndAttributes),
         w.DWORD, c.POINTER(SidAndAttributes), handle_pointer)
    bind(api.security, "CreateProcessAsUserW", w.BOOL, w.HANDLE,
         w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL, w.DWORD,
         c.c_void_p, w.LPCWSTR, c.POINTER(StartupInfo), c.POINTER(ProcessInfo))
    ordinary = set()
    for name in _ORDINARY_PRIVILEGES:
        luid = Luid()
        if not api.security.LookupPrivilegeValueW(None, name, c.byref(luid)):
            raise c.WinError(c.get_last_error())
        ordinary.add((luid.low, luid.high))
    api.ordinary_privileges = frozenset(ordinary)
    return api


def _token_data(api, token, information_class):
    c, w = api.c, api.w
    size = w.DWORD()
    result = api.security.GetTokenInformation(token, information_class, None, 0, c.byref(size))
    if result or c.get_last_error() != 122 or not 0 < size.value <= 1048576:
        raise RuntimeError("cannot determine native token information size")
    buffer = c.create_string_buffer(size.value)
    if not api.security.GetTokenInformation(token, information_class, buffer, len(buffer), c.byref(size)):
        raise c.WinError(c.get_last_error())
    if not 0 < size.value <= len(buffer):
        raise RuntimeError("invalid native token information length")
    return buffer, size.value


def _token_entries(api, token, information_class, entry_type, offset):
    buffer, length = _token_data(api, token, information_class)
    if length < offset or offset < api.c.sizeof(api.w.DWORD):
        raise RuntimeError("truncated native token entries")
    count = api.w.DWORD.from_buffer(buffer).value
    stride = api.c.sizeof(entry_type)
    if count > (length - offset) // stride:
        raise RuntimeError("native token entry count exceeds its buffer")
    return buffer, [entry_type.from_buffer(buffer, offset + index * stride) for index in range(count)]


def _sid_string(api, sid):
    text = api.w.LPWSTR()
    if not api.security.ConvertSidToStringSidW(sid, api.c.byref(text)):
        raise api.c.WinError(api.c.get_last_error())
    try:
        return text.value
    finally:
        api.kernel.LocalFree(api.c.cast(text, api.c.c_void_p))


@contextlib.contextmanager
def _process_token(api, *, for_launch=False):
    token = api.w.HANDLE()
    # Status needs only QUERY. Creation additionally needs DUPLICATE,
    # ASSIGN_PRIMARY, and ADJUST_DEFAULT to lower the new child's integrity.
    access = 0x008B if for_launch else 0x0008
    if not api.security.OpenProcessToken(api.kernel.GetCurrentProcess(), access, api.c.byref(token)):
        raise api.c.WinError(api.c.get_last_error())
    try:
        yield token
    finally:
        api.kernel.CloseHandle(token)


def _thread_impersonating(api):
    thread = api.w.HANDLE()
    if not api.security.OpenThreadToken(api.kernel.GetCurrentThread(), 0x0008, True, api.c.byref(thread)):
        if api.c.get_last_error() == 1008:
            return False
        raise api.c.WinError(api.c.get_last_error())
    api.kernel.CloseHandle(thread)
    return True


def _token_identity(api, token):
    buffer, length = _token_data(api, token, 1)  # TokenUser
    if length < api.c.sizeof(api.SidAndAttributes):
        raise RuntimeError("truncated native token user")
    user = api.SidAndAttributes.from_buffer(buffer)
    sid = _sid_string(api, user.sid)
    if not _supported_identity(sid) or sid.startswith("S-1-12-1-"):
        return sid, None
    # Derive this account's domain through the OS; never infer ordinary
    # membership from arbitrary domain-looking SIDs or TokenPrimaryGroup.
    domain = api.c.create_string_buffer(68)  # SECURITY_MAX_SID_SIZE
    size = api.w.DWORD(len(domain))
    if not api.security.GetWindowsAccountDomainSid(user.sid, domain, api.c.byref(size)):
        raise api.c.WinError(api.c.get_last_error())
    if not 0 < size.value <= len(domain):
        raise RuntimeError("invalid native account domain SID length")
    users = api.c.create_string_buffer(68)
    size = api.w.DWORD(len(users))
    if not api.security.CreateWellKnownSid(42, domain, users, api.c.byref(size)):
        raise api.c.WinError(api.c.get_last_error())
    if not 0 < size.value <= len(users):
        raise RuntimeError("invalid native Domain Users SID length")
    return sid, _sid_string(api, users)


def _token_owner(api, token):
    buffer, length = _token_data(api, token, 4)  # TokenOwner
    if length < api.c.sizeof(api.c.c_void_p):
        raise RuntimeError("truncated native token owner")
    owner = api.c.c_void_p.from_buffer(buffer)
    return _sid_string(api, owner)


def _set_token_user_owner(api, token):
    buffer, length = _token_data(api, token, 1)  # TokenUser
    if length < api.c.sizeof(api.SidAndAttributes):
        raise RuntimeError("truncated native token user")
    user = api.SidAndAttributes.from_buffer(buffer)
    user_sid = _sid_string(api, user.sid)
    if _token_owner(api, token) == user_sid:
        return
    # Called only for the fresh restricted token. CPython's private temporary
    # directories grant OWNER RIGHTS, so their default owner must be this user,
    # rather than the Administrators group whose allow grants were removed.
    owner = api.c.c_void_p(user.sid)
    if not api.security.SetTokenInformation(token, 4, api.c.byref(owner), api.c.sizeof(owner)):
        raise api.c.WinError(api.c.get_last_error())
    if _token_owner(api, token) != user_sid:
        raise RuntimeError("native restricted token did not retain its user as default owner")


def _token_integrity(api, token):
    buffer, length = _token_data(api, token, 25)  # TokenIntegrityLevel
    if length < api.c.sizeof(api.SidAndAttributes):
        raise RuntimeError("truncated native token integrity label")
    label = api.SidAndAttributes.from_buffer(buffer)
    sid = _sid_string(api, label.sid)
    if not label.attributes & 0x20 or not re.fullmatch(r"S-1-16-\d+", sid):
        raise RuntimeError("invalid native token integrity label")
    return int(sid.rsplit("-", 1)[1])


def _lower_integrity(api, token):
    if _token_integrity(api, token) <= _MEDIUM_INTEGRITY:
        return
    # Only called on the fresh restricted primary, never the parent's token.
    # Allocate TOKEN_MANDATORY_LABEL and its SID in one buffer with exact length.
    offset = api.c.sizeof(api.SidAndAttributes)
    buffer = api.c.create_string_buffer(offset + 68)
    sid = api.c.byref(buffer, offset)
    size = api.w.DWORD(68)
    if not api.security.CreateWellKnownSid(67, None, sid, api.c.byref(size)):
        raise api.c.WinError(api.c.get_last_error())  # WinMediumLabelSid
    if not 0 < size.value <= 68:
        raise RuntimeError("invalid native medium integrity SID length")
    label = api.SidAndAttributes.from_buffer(buffer)
    label.sid = api.c.cast(sid, api.c.c_void_p)
    label.attributes = 0x20  # SE_GROUP_INTEGRITY
    if not api.security.SetTokenInformation(token, 25, buffer, offset + size.value):
        raise api.c.WinError(api.c.get_last_error())


def _token_authority(api, token):
    _, domain_users_sid = _token_identity(api, token)
    privilege_buffer, privileges = _token_entries(
        api, token, 3, api.LuidAndAttributes, api.c.sizeof(api.w.DWORD),
    )
    group_buffer, groups = _token_entries(
        api, token, 2, api.SidAndAttributes, api.TokenGroups.groups.offset,
    )
    extra_privileges = [entry for entry in privileges
                        if (entry.luid.low, entry.luid.high) not in api.ordinary_privileges]
    extra_groups = [entry for entry in groups
                    if not _ordinary_group(_sid_string(api, entry.sid), entry.attributes, domain_users_sid)]
    # Return buffers too: SID pointers inside group entries point into them.
    return privilege_buffer, group_buffer, extra_privileges, extra_groups


def _status(api, token):
    buffers = _token_authority(api, token)
    extra_privileges, extra_groups = buffers[2:]
    unsafe_groups = [entry for entry in extra_groups if not entry.attributes & 0x10]
    kind, kind_length = _token_data(api, token, 8)  # TokenType
    statistics, statistics_length = _token_data(api, token, 10)  # TokenStatistics
    if kind_length < api.c.sizeof(api.w.DWORD) or statistics_length < api.c.sizeof(api.Luid):
        raise RuntimeError("truncated native token identity")
    primary = api.w.DWORD.from_buffer(kind).value == 1
    identity = api.Luid.from_buffer(statistics)
    impersonating = _thread_impersonating(api)
    user_sid, domain_users_sid = _token_identity(api, token)
    supported_identity = _supported_identity(user_sid)
    integrity_level = _token_integrity(api, token)
    owner_sid = _token_owner(api, token)
    # Private directories must default to this user, including OWNER RIGHTS ACLs.
    primary_eligible = (primary and not extra_privileges and not unsafe_groups
                        and supported_identity and integrity_level <= _MEDIUM_INTEGRITY
                        and owner_sid == user_sid)
    return {
        "native": True,
        "eligible": primary_eligible and not impersonating,
        "primary_eligible": primary_eligible,
        "user_sid": user_sid,
        "owner_sid": owner_sid,
        "supported_identity": supported_identity,
        "domain_users_sid": domain_users_sid,
        "integrity_level": integrity_level,
        "primary_token": primary,
        "primary_token_id": [identity.high, identity.low],
        "thread_impersonating": impersonating,
        "nonordinary_privileges": len(extra_privileges),
        "nonordinary_groups": len(unsafe_groups),
    }


def windows_test_process_status() -> dict:
    """Inspect actual native primary authority and the presence of impersonation."""
    if os.name != "nt":
        return {"native": False, "eligible": False, "primary_eligible": False, "primary_token": False,
                "primary_token_id": None, "thread_impersonating": False,
                "nonordinary_privileges": 0, "nonordinary_groups": 0,
                "user_sid": None, "owner_sid": None, "supported_identity": False,
                "domain_users_sid": None, "integrity_level": None}
    api = _windows_api()
    with _process_token(api) as token:
        return _status(api, token)


def test_interpreter_flags() -> list[str]:
    """Retain the exact options of a supported direct-script invocation."""
    original = getattr(sys, "orig_argv", None)
    current = list(sys.argv)
    if (not original or not current or len(original) <= len(current)
            or original[-len(current):] != current):
        raise RuntimeError("Windows test bootstrap requires an unchanged direct-script invocation")
    if not sys.executable or not Path(sys.executable).is_file():
        raise RuntimeError("Windows test bootstrap requires the current Python executable")
    return list(original[1:-len(current)])


@contextlib.contextmanager
def _restricted_primary(api, source):
    user_sid, _ = _token_identity(api, source)
    if not _supported_identity(user_sid):
        raise RuntimeError(f"unsupported Windows test identity: {user_sid}")
    buffers = _token_authority(api, source)
    extra_privileges, extra_groups = buffers[2:]
    privileges = (api.LuidAndAttributes * len(extra_privileges))(*extra_privileges)
    groups = (api.SidAndAttributes * len(extra_groups))(*extra_groups)
    restricted = api.w.HANDLE()
    # Explicitly remove available privileges and make discretionary grants
    # deny-only. No SANDBOX_INERT or privilege-enabling flags are used.
    if not api.security.CreateRestrictedToken(
        source, 0, len(groups), groups, len(privileges), privileges, 0, None, api.c.byref(restricted),
    ):
        raise api.c.WinError(api.c.get_last_error())
    try:
        _set_token_user_owner(api, restricted)
        _lower_integrity(api, restricted)
        # Check the created primary token itself before it can launch anything.
        state = _status(api, restricted)
        if (not state["primary_token"] or state["nonordinary_privileges"]
                or state["nonordinary_groups"] or not state["supported_identity"]
                or state["integrity_level"] > _MEDIUM_INTEGRITY
                or state["owner_sid"] != state["user_sid"]):
            raise RuntimeError("native restriction did not remove primary authority")
        yield restricted
    finally:
        api.kernel.CloseHandle(restricted)


def _launch(api, token, command, environment):
    c, w = api.c, api.w
    startup = api.StartupInfoEx()
    startup.startup.cb = c.sizeof(startup.startup)
    startup.startup.flags = 0x00000100  # STARTF_USESTDHANDLES
    process = api.ProcessInfo()
    handles = []
    attribute_buffer = None
    attributes_initialized = False
    finished = False
    control_handler = None
    control_registered = False
    accept_shared_interrupt = True
    retained_handlers = getattr(api, "_launch_control_handlers", None)
    if retained_handlers is None:
        retained_handlers = api._launch_control_handlers = []
    try:
        current = api.kernel.GetCurrentProcess()
        for identifier, field in ((-10, "stdin"), (-11, "stdout"), (-12, "stderr")):
            original = api.kernel.GetStdHandle(identifier)
            if original == c.c_void_p(-1).value:
                raise RuntimeError(f"native {field} handle is invalid")
            if not original:
                continue  # Preserve an absent stream as NULL in the child.
            duplicate = w.HANDLE()
            if not api.kernel.DuplicateHandle(current, original, current, c.byref(duplicate), 0, True, 2):
                raise c.WinError(c.get_last_error())
            handles.append(duplicate)
            setattr(startup.startup, field, duplicate.value)
        if not handles:
            # STARTF_USESTDHANDLES requires inheritance even when all streams
            # are NULL. A fresh inert event makes the explicit allow-list
            # nonempty without admitting any unrelated inheritable handle.
            create_event = api.kernel.CreateEventW
            create_event.restype = w.HANDLE
            create_event.argtypes = [c.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR]
            sentinel = create_event(None, False, False, None)
            if not sentinel:
                raise c.WinError(c.get_last_error())
            handles.append(w.HANDLE(sentinel))
            set_handle_information = api.kernel.SetHandleInformation
            set_handle_information.restype = w.BOOL
            set_handle_information.argtypes = [w.HANDLE, w.DWORD, w.DWORD]
            if not set_handle_information(sentinel, 1, 1):  # HANDLE_FLAG_INHERIT
                raise c.WinError(c.get_last_error())
        creation_flags = 0x00000400  # CREATE_UNICODE_ENVIRONMENT
        size = c.c_size_t()
        result = api.kernel.InitializeProcThreadAttributeList(None, 1, 0, c.byref(size))
        if result or c.get_last_error() != 122 or not 0 < size.value <= 1048576:
            raise RuntimeError("cannot size native process attribute list")
        attribute_buffer = c.create_string_buffer(size.value)
        startup.attributes = c.cast(attribute_buffer, c.c_void_p)
        if not api.kernel.InitializeProcThreadAttributeList(startup.attributes, 1, 0, c.byref(size)):
            raise c.WinError(c.get_last_error())
        attributes_initialized = True
        inherited = (w.HANDLE * len(handles))(*(handle.value for handle in handles))
        if not api.kernel.UpdateProcThreadAttribute(
            startup.attributes, 0, 0x00020002, inherited, c.sizeof(inherited), None, None,
        ):  # PROC_THREAD_ATTRIBUTE_HANDLE_LIST
            raise c.WinError(c.get_last_error())
        startup.startup.cb = c.sizeof(startup)
        creation_flags |= 0x00080000  # EXTENDED_STARTUPINFO_PRESENT
        command_line = c.create_unicode_buffer(subprocess.list2cmdline(command))
        block = c.create_string_buffer(environment)
        handler_type = c.WINFUNCTYPE(w.BOOL, w.DWORD)

        @handler_type
        def control_handler(event):
            # Console Ctrl+C reaches the child as well. Only the child decides
            # whether to exit or continue; other events keep their normal path.
            return bool(event == 0 and process.process and accept_shared_interrupt)

        control = api.kernel.SetConsoleCtrlHandler
        control.restype = w.BOOL
        control.argtypes = [handler_type, w.BOOL]
        retained_handlers.append(control_handler)
        control_registered = True
        if not control(control_handler, True):
            control_registered = False
            retained_handlers.remove(control_handler)
            raise c.WinError(c.get_last_error())
        # This callback is process-local, unlike the inheritable ignore flag
        # set by SetConsoleCtrlHandler(NULL, TRUE). The child handles Ctrl+C.
        # Only the standard handles (or inert sentinel) enter the allow-list.
        if not api.security.CreateProcessAsUserW(
            token, command[0], command_line, None, None, True, creation_flags,
            block, os.getcwd(), c.byref(startup.startup), c.byref(process),
        ):
            raise c.WinError(c.get_last_error())
        while True:
            waited = api.kernel.WaitForSingleObject(process.process, 1000)
            if waited == 0:
                finished = True
                break
            if waited != 258:  # WAIT_TIMEOUT
                raise c.WinError(c.get_last_error())
        code = w.DWORD()
        if not api.kernel.GetExitCodeProcess(process.process, c.byref(code)):
            raise c.WinError(c.get_last_error())
        return c.c_int32(code.value).value
    finally:
        try:
            if process.process and not finished:
                api.kernel.TerminateProcess(process.process, 130)
                api.kernel.WaitForSingleObject(process.process, 5000)
            if process.thread:
                api.kernel.CloseHandle(process.thread)
            if process.process:
                api.kernel.CloseHandle(process.process)
            if attributes_initialized:
                api.kernel.DeleteProcThreadAttributeList(startup.attributes)
            for handle in handles:
                api.kernel.CloseHandle(handle)
        finally:
            accept_shared_interrupt = False
            if control_registered:
                if not control(control_handler, False):
                    raise c.WinError(c.get_last_error())
                # Keep even a removed callback pinned for this test process:
                # an already-dispatched native handler thread may still be
                # waiting to enter Python. Its inactive closure returns FALSE.


def _native_environment_block(api) -> bytes:
    """Copy Windows' native block, including hidden per-drive directories."""
    address = api.kernel.GetEnvironmentStringsW()
    if not address:
        raise api.c.WinError(api.c.get_last_error())
    try:
        units = api.c.cast(address, api.c.POINTER(api.c.c_uint16))
        length = 0
        while units[length] or units[length + 1]:
            length += 1
        raw = api.c.string_at(address, (length + 2) * 2)
    finally:
        api.kernel.FreeEnvironmentStringsW(address)
    entries = [entry for entry in raw.decode("utf-16-le", "surrogatepass").split("\0")[:-2] if entry]

    def compare(left, right):
        result = api.kernel.CompareStringOrdinal(left, -1, right, -1, True)
        if not result:
            raise api.c.WinError(api.c.get_last_error())
        return result - 2

    def name(entry):
        return entry[:entry.index("=", 1 if entry.startswith("=") else 0)]

    # The marker is only a retry guard. Remove every differently cased copy,
    # while preserving hidden names (whose first character is '=') verbatim.
    entries = [entry for entry in entries if compare(name(entry), _CHILD_MARKER)]
    marker = _CHILD_MARKER + "=1"
    index = next((i for i, entry in enumerate(entries) if compare(name(entry), _CHILD_MARKER) > 0), len(entries))
    entries.insert(index, marker)
    return ("\0".join(entries) + "\0\0").encode("utf-16-le", "surrogatepass")


def _flush_standard_streams():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.flush()


def _exit_status(status: int) -> int:
    # Windows subprocess exposes a DWORD; os._exit accepts a signed C int.
    return (status + 0x80000000) % 0x100000000 - 0x80000000 if os.name == "nt" else status


def exit_test_process(status: int):
    """Exit the waiting wrapper without a second -i/PYTHONINSPECT prompt."""
    try:
        _flush_standard_streams()
    finally:
        os._exit(_exit_status(status))


def ensure_windows_test_process(
    entrypoint: str | Path, argv: list[str], *, parent_check: list[str] | None = None,
) -> int | None:
    """Continue if suitable, or run the exact test command in a restricted child.

    ``argv`` excludes the script name. ``parent_check`` is an optional trusted
    native regression command that must pass before a parent with unsuitable
    primary authority starts its restricted child. A returned integer is the
    status the caller must exit with; ``None`` means the current process may continue.
    """
    if os.name != "nt":
        return None
    try:
        state = windows_test_process_status()
        if not state["supported_identity"]:
            raise RuntimeError("Windows test bootstrap does not support this privileged account identity")
        if state["eligible"]:
            return None
        if os.environ.get(_CHILD_MARKER):
            raise RuntimeError("restricted test child still has unsuitable native token authority")
        # A thread-only impersonation problem needs a clean child, but a proof
        # subprocess inherits the already-suitable primary and has no excess
        # primary authority to test. Preserve the proof for every other case.
        if parent_check is not None and not state["primary_eligible"]:
            if not parent_check:
                raise ValueError("native parent regression command is empty")
            parent_environment = {key: value for key, value in os.environ.items()
                                  if not key.upper().startswith("PYTHON")}
            # Auxiliary unittest reporters need real streams even when the
            # requested invocation has NULL handles. These pipes belong only
            # to the proof process; the requested child retains its handles.
            result = subprocess.run(parent_check, check=False, env=parent_environment,
                                    capture_output=True, text=True, errors="replace")
            for stream, output in ((sys.stdout, result.stdout), (sys.stderr, result.stderr)):
                if stream is not None:
                    stream.write(output)
                    stream.flush()
            if result.returncode:
                return _exit_status(result.returncode)
        script = os.fspath(entrypoint)
        if not Path(script).is_file() or not sys.executable:
            raise ValueError("test entrypoint and interpreter must name existing files")
        if script != sys.argv[0] or list(argv) != sys.argv[1:]:
            raise RuntimeError("Windows test bootstrap cannot change the original script arguments")
        command = [sys.executable, *test_interpreter_flags(), script, *argv]
        api = _windows_api()
        environment = _native_environment_block(api)
        _flush_standard_streams()
        with _process_token(api, for_launch=True) as source, _restricted_primary(api, source) as restricted:
            return _launch(api, restricted, command, environment)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Windows test process setup failed: {exc}", file=sys.stderr)
        return 2
