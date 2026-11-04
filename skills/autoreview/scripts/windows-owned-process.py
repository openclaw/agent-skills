"""Private Windows process ownership for autoreview's three launch paths.

The caller admits the interpreter and this file, registers Startup.process and
Startup.job before finish(), and closes the job when unregistering the process.
"""

import ctypes
from ctypes import wintypes
import errno
import json
import os
import struct
import subprocess
import sys
import threading
import time


MAX_FRAME = 1024 * 1024
STARTUP_SECONDS = 10.0
SETTLE_SECONDS = 2.0


class LaunchIndeterminate(RuntimeError):
    """The target may have started; availability fallback or retry is unsafe."""

    def __str__(self):
        message = super().__str__()
        if errors := getattr(self, "cleanup_errors", ()):
            # Exception text can contain target argv; expose only failure kinds.
            message += "; cleanup also failed: " + ", ".join(type(error).__name__ for error in errors)
        return message


class Native:
    def __init__(self):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          wintypes.DWORD], wintypes.BOOL),
            "QueryInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "GetCurrentProcess": ([], wintypes.HANDLE),
            "DuplicateHandle": ([wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
                                  ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
                                  wintypes.BOOL, wintypes.DWORD], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
            "GetStdHandle": ([wintypes.DWORD], wintypes.HANDLE),
            "SetStdHandle": ([wintypes.DWORD, wintypes.HANDLE], wintypes.BOOL),
            "PeekNamedPipe": ([wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD),
                                ctypes.c_void_p], wintypes.BOOL),
            "ExitProcess": ([wintypes.UINT], None),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes = arguments
            function.restype = result

    @staticmethod
    def check(result):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return result

    def close(self, handle):
        if handle is not None:
            self.check(self.kernel.CloseHandle(handle))

    def duplicate(self, handle, access=None):
        duplicate = wintypes.HANDLE()
        current = self.kernel.GetCurrentProcess()
        self.check(self.kernel.DuplicateHandle(
            current, handle, current, ctypes.byref(duplicate), access or 0,
            True, 2 if access is None else 0))
        return duplicate.value


class BasicLimits(ctypes.Structure):
    _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                ("flags", wintypes.DWORD), ("minimum_working_set", ctypes.c_size_t),
                ("maximum_working_set", ctypes.c_size_t), ("active_limit", wintypes.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                ("scheduling", wintypes.DWORD)]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [("basic", BasicLimits), ("io_counters", ctypes.c_ulonglong * 6),
                ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]


class Accounting(ctypes.Structure):
    _fields_ = [("times", ctypes.c_longlong * 4), ("page_faults", wintypes.DWORD),
                ("total_processes", wintypes.DWORD), ("active_processes", wintypes.DWORD),
                ("terminated_processes", wintypes.DWORD)]


class Job:
    def __init__(self):
        self.native = Native()
        self.lock = threading.RLock()
        self.handle = self.native.check(self.native.kernel.CreateJobObjectW(None, None))
        try:
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
            self.native.check(self.native.kernel.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        except BaseException:
            self.close()
            raise

    def assignment_handle(self):
        with self.lock:
            if self.handle is None:
                raise OSError(errno.EBADF, "Windows owned job is closed")
            return self.native.duplicate(self.handle, 0x0001)  # JOB_OBJECT_ASSIGN_PROCESS only.

    def terminate(self):
        with self.lock:
            if self.handle is not None:
                self.native.check(self.native.kernel.TerminateJobObject(self.handle, 1))

    def active_count(self):
        with self.lock:
            if self.handle is None:
                return 0
            information = Accounting()
            self.native.check(self.native.kernel.QueryInformationJobObject(
                self.handle, 1, ctypes.byref(information), ctypes.sizeof(information), None))
            return information.active_processes

    def close(self):
        with self.lock:
            handle, self.handle = self.handle, None
            self.native.close(handle)


def encode_frame(value):
    data = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    if len(data) > MAX_FRAME:
        raise ValueError("Windows startup record exceeds its size limit")
    return struct.pack("!I", len(data)) + data


def write_frame(descriptor, frame):
    remaining = memoryview(frame)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError(errno.EPIPE, "Windows startup channel closed")
        remaining = remaining[written:]


def read_frame(descriptor, *, native=None, deadline=None):
    def exact(size):
        data = bytearray()
        while len(data) < size:
            wanted = size - len(data)
            if deadline is not None:
                import msvcrt

                if time.monotonic() >= deadline:
                    raise TimeoutError("Windows startup channel timed out")
                available = wintypes.DWORD()
                native.check(native.kernel.PeekNamedPipe(
                    msvcrt.get_osfhandle(descriptor), None, 0, None,
                    ctypes.byref(available), None))
                if not available.value:
                    time.sleep(0.01)
                    continue
                wanted = min(wanted, available.value)
            chunk = os.read(descriptor, wanted)
            if not chunk:
                raise EOFError("Windows startup channel closed")
            data.extend(chunk)
        return data

    size, = struct.unpack("!I", exact(4))
    if not 0 < size <= MAX_FRAME:
        raise ValueError("invalid Windows startup record size")
    value = json.loads(exact(size))
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("invalid Windows startup record")
    return value


class Startup:
    def __init__(self, interpreter, supervisor_path, argv, *, cwd, env=None, **stdio):
        import msvcrt

        self.frame = encode_frame({"version": 1, "operation": "go", "argv": argv})
        self.argv = argv
        self.job = Job()
        self.process = None
        self.reader = self.writer = None
        self.worker = None
        self.done = threading.Event()
        self.state_lock = threading.Lock()
        self.cancelled = False
        self.deadline = None
        self.go_sent = False
        self.reported_error = False
        self.error = None
        self.control_errors = []
        child_reader = child_writer = assignment = None
        try:
            try:
                child_reader, self.writer = os.pipe()
                self.reader, child_writer = os.pipe()
                for descriptor in (child_reader, child_writer):
                    os.set_inheritable(descriptor, True)
                assignment = self.job.assignment_handle()
                child_handles = [msvcrt.get_osfhandle(child_reader),
                                 msvcrt.get_osfhandle(child_writer)]
                startup = subprocess.STARTUPINFO(lpAttributeList={
                    "handle_list": [assignment, *child_handles]})
                self.process = subprocess.Popen(
                    [str(interpreter), "-I", "-S", "-B", str(supervisor_path),
                     str(assignment), *(str(handle) for handle in child_handles)],
                    cwd=cwd, env=env, startupinfo=startup, close_fds=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, **stdio)
            finally:
                # Closing inherited duplicates is still construction. A failure
                # here must reap the child instead of escaping before registration.
                close_error = None
                for descriptor in (child_reader, child_writer):
                    if descriptor is not None:
                        try:
                            os.close(descriptor)
                        except OSError as exc:
                            close_error = exc
                try:
                    self.job.native.close(assignment)
                except OSError as exc:
                    close_error = exc
                if close_error is not None:
                    raise close_error
        except BaseException as failure:
            # No exchange worker exists during construction. Attempt all three
            # releases even when a previous native operation failed.
            for cleanup in (self.abort, self.job.close, self.close):
                try:
                    cleanup()
                except BaseException as error:
                    if not isinstance(error, Exception) and isinstance(failure, Exception):
                        error.startup_failure = failure
                        error.__cause__ = None
                        error.__suppress_context__ = True
                        failure = error
                    else:
                        failure.cleanup_errors = (*getattr(failure, "cleanup_errors", ()), error)
            raise failure

    def _exchange(self):
        try:
            with self.state_lock:
                if self.cancelled:
                    raise TimeoutError("Windows startup aborted before readiness")
            if read_frame(self.reader) != {"version": 1, "operation": "ready"}:
                raise ValueError("invalid Windows supervisor readiness")
            # Cancellation and GO share one decision: a pre-GO timeout cannot
            # subsequently release the target from this worker.
            with self.state_lock:
                if self.cancelled or time.monotonic() >= self.deadline:
                    raise TimeoutError("Windows startup expired before GO")
                # Even a partial GO write is conservatively potentially launched.
                self.go_sent = True
            write_frame(self.writer, self.frame)
            result = read_frame(self.reader)
            if (result.get("operation") == "error"
                    and type(result.get("winerror")) is int
                    and result["winerror"] > 0):
                self.reported_error = True
                error = ctypes.WinError(result["winerror"])
                error.filename = self.argv[0]
                raise error
            if (result.get("operation") != "started"
                    or type(result.get("pid")) is not int or result["pid"] <= 0):
                raise ValueError("invalid Windows launch acknowledgement")
        except BaseException as exc:
            self.error = exc
        finally:
            # Once started, this worker alone closes the raw endpoints, after
            # its last I/O. Even failed aborts cannot orphan or recycle them
            # underneath a live reader.
            self._close_control()
            self.done.set()

    def finish(self, deadline):
        if self.worker is not None:
            raise RuntimeError("Windows startup can only be awaited once")
        with self.state_lock:
            if self.cancelled:
                raise RuntimeError("Windows startup was already aborted")
            self.deadline = deadline
        allowance = max(0, deadline - time.monotonic())
        # The worker owns its raw endpoints until I/O ends, but a broken peer
        # must not turn bounded startup cleanup into an unbounded interpreter exit.
        self.worker = threading.Thread(target=self._exchange, name="windows-startup", daemon=True)
        self.worker.start()
        if not self.done.wait(allowance):
            with self.state_lock:
                self.cancelled = True
                go_sent = self.go_sent
            if go_sent:
                raise LaunchIndeterminate("Windows target may have started; acknowledgement timed out")
            raise subprocess.TimeoutExpired(self.argv, allowance)
        self.worker.join()
        failure = None
        if self.error is not None:
            if self.reported_error:
                failure = self.error
            elif self.go_sent:
                failure = LaunchIndeterminate("Windows target may have started; acknowledgement lost")
            elif isinstance(self.error, TimeoutError):
                failure = subprocess.TimeoutExpired(self.argv, allowance)
            else:
                failure = OSError(errno.EIO, "Windows supervisor failed before target startup")
        elif self.control_errors:
            failure = LaunchIndeterminate("Windows target started; control cleanup failed")
        if failure is not None:
            failure.cleanup_errors = (*getattr(failure, "cleanup_errors", ()), *self.control_errors)
            self.control_errors.clear()
            if failure is self.error:
                raise failure
            raise failure from self.error
        return self.process

    def _close_control(self):
        for name in ("reader", "writer"):
            descriptor = getattr(self, name)
            setattr(self, name, None)
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except BaseException as error:
                    self.control_errors.append(error)

    def close(self):
        """Finalize protocol I/O after the caller releases the native job."""
        with self.state_lock:
            self.cancelled = True
            unstarted = self.worker is None or self.worker.ident is None
            if unstarted:
                # A delayed worker must see cancellation before any I/O. Holding
                # its entry lock makes closing unstarted endpoints safe too.
                self._close_control()
        if not unstarted:
            self.worker.join(timeout=SETTLE_SECONDS)
            if self.worker.is_alive():
                # The worker still owns both endpoints and will close them when
                # its I/O ends; never close a descriptor beneath that operation.
                raise TimeoutError("Windows startup I/O did not settle")
        if self.control_errors:
            errors, self.control_errors = self.control_errors, []
            primary = next((error for error in errors if not isinstance(error, Exception)), errors[0])
            primary.cleanup_errors = (*getattr(primary, "cleanup_errors", ()),
                                      *(error for error in errors if error is not primary))
            raise primary

    def abort(self):
        # The child cannot retain a control endpoint after it and its job settle.
        # Closing a descriptor beneath a live blocking reader is not cancellation.
        with self.state_lock:
            self.cancelled = True
        deadline = time.monotonic() + SETTLE_SECONDS
        termination_error = None
        try:
            self.job.terminate()
        except OSError as exc:
            termination_error = exc
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=max(0, deadline - time.monotonic()))
        while self.job.active_count():
            if time.monotonic() >= deadline:
                raise TimeoutError("Windows owned job did not settle")
            time.sleep(0.01)
        if termination_error is not None:
            raise termination_error


def spawn(interpreter, supervisor_path, argv, *, cwd, env=None, **stdio):
    if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("Windows owned process requires a nonempty string argument list")
    return Startup(interpreter, supervisor_path, argv, cwd=cwd, env=env, **stdio)


def start_target(native, argv, standard_handles):
    # Do not let Popen's all-None stdio path reinterpret absent/inherited handles.
    # Its explicit STARTUPINFO survives because no stdin/out/err override is passed.
    duplicates = []
    handles = []
    invalid = wintypes.HANDLE(-1).value
    try:
        for handle in standard_handles:
            if handle not in (None, invalid):
                handle = native.duplicate(handle)
                duplicates.append(handle)
            handles.append(handle or 0)
        startup = subprocess.STARTUPINFO(
            dwFlags=subprocess.STARTF_USESTDHANDLES,
            hStdInput=handles[0], hStdOutput=handles[1], hStdError=handles[2],
            lpAttributeList={"handle_list": duplicates})
        return subprocess.Popen(argv, startupinfo=startup, close_fds=True)
    finally:
        for handle in duplicates:
            try:
                native.close(handle)
            except OSError as exc:
                # Popen may already have succeeded. Do not report a cleanup
                # failure as proof that CreateProcess never started the target.
                raise LaunchIndeterminate("Windows standard-handle cleanup failed") from exc


def close_standard_endpoints(native, standard_handles, control_handles):
    invalid = wintypes.HANDLE(-1).value
    originals = dict.fromkeys(handle for handle in standard_handles
                              if handle not in (None, invalid))
    if any(handle in control_handles for handle in originals):
        raise LaunchIndeterminate("Windows standard and control handles overlap")
    try:
        for standard in (-10, -11, -12):
            native.check(native.kernel.SetStdHandle(standard, None))
        for handle in originals:
            native.close(handle)
    except OSError as exc:
        raise LaunchIndeterminate("Windows supervisor standard-handle release failed") from exc
    # Any alias CRT slot/wrapper is deliberately unused from here onward.
    # Native ExitProcess skips finalizers that could otherwise close it again.


def supervise():
    import msvcrt

    native = Native()
    # Adopting a control handle can occupy a vacant CRT standard descriptor.
    # Preserve the actual inherited streams before that registration occurs.
    standard_handles = [native.kernel.GetStdHandle(number) for number in (-10, -11, -12)]
    assignment, input_handle, output_handle = (int(value) for value in sys.argv[1:])
    reader = writer = None
    try:
        reader = msvcrt.open_osfhandle(input_handle, os.O_BINARY | os.O_RDONLY)
        writer = msvcrt.open_osfhandle(output_handle, os.O_BINARY | os.O_WRONLY)
        os.set_inheritable(reader, False)
        os.set_inheritable(writer, False)
        native.check(native.kernel.AssignProcessToJobObject(
            assignment, native.kernel.GetCurrentProcess()))
        native.close(assignment)
        assignment = None
        write_frame(writer, encode_frame({"version": 1, "operation": "ready"}))
        request = read_frame(reader, native=native,
                             deadline=time.monotonic() + STARTUP_SECONDS)
        argv = request.get("argv")
        if (request.get("operation") != "go" or not isinstance(argv, list)
                or not argv or any(not isinstance(arg, str) for arg in argv)):
            raise ValueError("invalid Windows target request")
        try:
            target = start_target(native, argv, standard_handles)
        except OSError as exc:
            if getattr(exc, "winerror", None):
                write_frame(writer, encode_frame({"version": 1, "operation": "error",
                                                  "winerror": exc.winerror}))
            return 1
        # Only the target retains its copies: keeping stdin's read endpoint here
        # would stop the parent seeing BrokenPipe when the target closes stdin.
        close_standard_endpoints(native, standard_handles, (input_handle, output_handle))
        write_frame(writer, encode_frame({"version": 1, "operation": "started", "pid": target.pid}))
        os.close(reader)
        reader = None
        os.close(writer)
        writer = None
        return target.wait()
    finally:
        native.close(assignment)
        for descriptor in (reader, writer):
            if descriptor is not None:
                os.close(descriptor)


if __name__ == "__main__":
    try:
        status = supervise()
    except BaseException:
        # Supervisor failures belong to the private channel, never target output.
        status = 1
    Native().kernel.ExitProcess(status)
