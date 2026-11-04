"""Product custody proof run before the native Windows test launcher restricts its parent."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = runpy.run_path(str(ROOT / "scripts" / "windows_test_process.py"))
PRODUCT = runpy.run_path(str(ROOT / "skills" / "autoreview" / "scripts" / "autoreview"))


class NativeProductCustodyTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.name, "nt", "this proof requires native Windows")
        self.api = BOOTSTRAP["_windows_api"]()
        function = self.api.kernel.GetSystemDirectoryW
        function.argtypes = [self.api.w.LPWSTR, self.api.w.UINT]
        function.restype = self.api.w.UINT
        buffer = self.api.c.create_unicode_buffer(32768)
        length = function(buffer, len(buffer))
        self.assertTrue(0 < length < len(buffer), "cannot identify the native system directory")
        self.library = Path(buffer.value) / "kernel32.dll"
        self.assertGreater(self.library.stat().st_nlink, 1,
                           "native custody proof requires a serviced hard-linked system DLL")

    def assert_product_custody(self, expected):
        # Exercise the real path-admission caller too: the DLL must reach the
        # shared-inode policy, not succeed through the single-link fast path.
        self.assertIs(PRODUCT["windows_file_custody"](self.library), expected)
        self.assertIs(PRODUCT["independent_file_custody"](self.library), expected)
        # Create this boundary under the current token. An elevated parent's
        # private directory may not be accessible while impersonating a child.
        with tempfile.TemporaryDirectory(prefix="autoreview-native-primary-") as directory:
            repo = Path(directory).resolve()
            self.assertIs(PRODUCT["external_env_path"](repo, str(self.library)), expected)

    def test_privileged_primary_remains_authoritative(self):
        before = BOOTSTRAP["windows_test_process_status"]()
        self.assertTrue(before["primary_token"])
        self.assertFalse(before["thread_impersonating"])
        original = self.library.stat()

        api = self.api
        duplicate = api.security.DuplicateToken
        duplicate.argtypes = [api.w.HANDLE, api.c.c_int, api.c.POINTER(api.w.HANDLE)]
        duplicate.restype = api.w.BOOL
        install = api.security.SetThreadToken
        install.argtypes = [api.c.POINTER(api.w.HANDLE), api.w.HANDLE]
        install.restype = api.w.BOOL
        with BOOTSTRAP["_process_token"](api, for_launch=True) as source:
            with BOOTSTRAP["_restricted_primary"](api, source) as restricted:
                reduced = BOOTSTRAP["_status"](api, restricted)
                self.assertTrue(reduced["primary_eligible"])
                self.assertTrue(reduced["owner_sid"] == reduced["user_sid"],
                                "restricted token owner must be its user")
                with self.subTest(proof="privileged-primary-refusal"):
                    if not before["nonordinary_privileges"]:
                        self.skipTest("ordinary primary has no nonordinary privilege; negative proof inapplicable")
                    self.assertFalse(before["primary_eligible"])
                    self.assert_product_custody(False)
                    impersonation = api.w.HANDLE()
                    if not duplicate(restricted, 2, api.c.byref(impersonation)):
                        raise api.c.WinError(api.c.get_last_error())
                    installed = False
                    try:
                        if not install(None, impersonation):
                            raise api.c.WinError(api.c.get_last_error())
                        installed = True
                        during = BOOTSTRAP["windows_test_process_status"]()
                        self.assertTrue(during["thread_impersonating"])
                        self.assertTrue(during["primary_token_id"] == before["primary_token_id"],
                                        "impersonation changed the parent primary token")
                        # Reverting this thread restores privileged authority. A
                        # thread-only product check would incorrectly accept it.
                        self.assert_product_custody(False)
                    finally:
                        try:
                            if installed and not install(None, None):
                                raise api.c.WinError(api.c.get_last_error())
                        finally:
                            api.kernel.CloseHandle(impersonation)
                    print("Verified product custody refusal for privileged primary and restricted thread.",
                          flush=True)

                # The same reduced token must really satisfy the product's
                # ACL/ownership contract when it becomes a child's primary.
                # This is a native process, not a mocked AccessCheck result.
                command = [sys.executable, "-u", "-I", "-S", "-B", "-X", "utf8=1",
                           str(Path(__file__).resolve()),
                           "--reduced-child", str(self.library)]
                code = BOOTSTRAP["_launch"](
                    api, restricted, command, BOOTSTRAP["_native_environment_block"](api),
                )
                self.assertEqual(code, 0, "reduced primary failed the real product positive control")

        self.assertTrue(BOOTSTRAP["windows_test_process_status"]() == before,
                        "product proof changed the parent token")
        after = self.library.stat()
        self.assertEqual((original.st_dev, original.st_ino, original.st_size, original.st_mtime_ns),
                         (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns))

    def test_reduced_primary_positive_control(self):
        self.assertEqual(self.library, Path(EXPECTED_LIBRARY),
                         "child must inspect the same native system DLL as its parent")
        current = BOOTSTRAP["windows_test_process_status"]()
        self.assertTrue(current["eligible"], "positive control requires an ordinary primary token")
        self.assertTrue(current["primary_eligible"])
        self.assertTrue(current["owner_sid"] == current["user_sid"],
                        "child token owner must be its user")
        self.assertFalse(current["thread_impersonating"])
        self.assert_product_custody(True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--reduced-child":
        EXPECTED_LIBRARY = sys.argv[2]
        selected = "NativeProductCustodyTests.test_reduced_primary_positive_control"
    elif len(sys.argv) == 1:
        selected = "NativeProductCustodyTests.test_privileged_primary_remains_authoritative"
    else:
        raise SystemExit("unexpected native custody proof arguments")
    unittest.main(argv=[sys.argv[0]], defaultTest=selected, verbosity=2)
