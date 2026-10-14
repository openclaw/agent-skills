#!/usr/bin/env python3
"""Qualify exact source archives in an isolated Python environment, without inference."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent


def tree(root: Path) -> dict[str, tuple[str, bytes | str | None]]:
    result = {}
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[name] = ("symlink", os.readlink(path))
        elif path.is_dir():
            result[name] = ("directory", None)
        elif path.is_file():
            result[name] = ("file", path.read_bytes())
        else:
            raise AssertionError(f"unexpected fixture entry: {name}")
    return result


class InstalledAutoreviewTests(unittest.TestCase):
    def test_exact_archives_and_installed_entrypoints(self) -> None:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        entries = subprocess.check_output(["git", "ls-tree", "-rz", head], cwd=ROOT)
        expected = {}
        for entry in entries.split(b"\0"):
            if entry:
                metadata, path = entry.split(b"\t", 1)
                mode, kind, oid = metadata.split()
                self.assertEqual(kind, b"blob")
                self.assertIn(mode, (b"100644", b"100755"))
                expected[path.decode()] = oid.decode()

        for filename in ("source.tar.gz", "source.zip"):
            with (self.subTest(archive=filename), tempfile.TemporaryDirectory() as tmp,
                  tempfile.TemporaryDirectory() as runtime_tmp):
                scratch = Path(tmp).resolve()
                source = scratch / "source"
                archive_path = OPTIONS.archives / filename
                archive_bytes = archive_path.read_bytes()
                if filename.endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                        members = [(m.filename, archive.read(m)) for m in archive.infolist()
                                   if not m.is_dir()]
                else:
                    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
                        self.assertTrue(all(m.isdir() or m.isfile() for m in archive))
                        members = [(m.name, archive.extractfile(m).read())
                                   for m in archive if m.isfile()]
                content = {}
                prefixes = set()
                for name, data in members:
                    path = PurePosixPath(name)
                    self.assertFalse(path.is_absolute())
                    self.assertNotIn("..", path.parts)
                    self.assertGreater(len(path.parts), 1)
                    prefixes.add(path.parts[0])
                    relative = PurePosixPath(*path.parts[1:]).as_posix()
                    self.assertNotIn(relative, content)
                    self.assertNotIn("\\", relative)
                    content[relative] = data
                self.assertEqual(len(prefixes), 1)
                self.assertEqual(set(content), set(expected))
                for name, data in content.items():
                    self.assertEqual(hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(), expected[name], name)
                    destination = source / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(data)

                user = scratch / "user"
                user.mkdir()
                for name in ("auth.json", "config.toml", "report.json"):
                    (user / name).write_text("external fixture\n", encoding="utf-8")
                cwd = scratch / "target with spaces 雪"
                cwd.mkdir()
                env = {name: value for name, value in os.environ.items()
                       if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "LANG"}}
                env.update(HOME=str(user), USERPROFILE=str(user), CODEX_HOME=str(user),
                           PYTHONDONTWRITEBYTECODE="1")
                if os.name == "nt":
                    # PowerShell owns writable profile/cache state separately from
                    # the source, install, target, and operator-state proof trees.
                    profile = Path(runtime_tmp).resolve()
                    roaming = profile / "AppData/Roaming"
                    local = profile / "AppData/Local"
                    roaming.mkdir(parents=True)
                    local.mkdir(parents=True)
                    env.update(HOME=str(profile), USERPROFILE=str(profile),
                               APPDATA=str(roaming), LOCALAPPDATA=str(local))
                env.pop("PYTHONPATH", None)

                def run(args: list[str], status: int = 0, stage: str = "install") -> subprocess.CompletedProcess[str]:
                    print(f"installed-source {filename}: {stage}", flush=True)
                    try:
                        result = subprocess.run(args, cwd=cwd, env=env, text=True,
                                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, timeout=30)
                    except subprocess.TimeoutExpired as error:
                        self.fail(f"{stage} timed out: stdout={error.stdout!r}; stderr={error.stderr!r}")
                    self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                    return result

                installed_root = scratch / "shared skills"
                run([sys.executable, "-B", str(source / "scripts/install-skills"),
                     "--target", str(installed_root),
                     "--mode", "copy", "autoreview"])
                installed = installed_root / "autoreview"
                self.assertEqual(tree(installed), tree(source / "skills/autoreview"))
                before = tree(scratch)
                helper = installed / "scripts/autoreview"
                if os.name == "nt":
                    powershell = shutil.which("powershell") or shutil.which("pwsh")
                    self.assertIsNotNone(powershell, "native PowerShell is required for this platform proof")
                    # The real launcher must choose the isolated proof interpreter,
                    # not a host py.exe that silently escapes the dependency matrix.
                    env["PATH"] = str(Path(sys.executable).parent)
                    for candidate in ("py", "python3"):
                        self.assertIsNone(shutil.which(candidate, path=env["PATH"]))
                    selected = run([powershell, "-NoProfile", "-NonInteractive", "-Command",
                                    "[Console]::Error.WriteLine('python-discovery'); "
                                    "$python = (Get-Command python -CommandType Application).Source; "
                                    "[Console]::Error.WriteLine('python-invocation'); "
                                    "& $python -c 'import sys; print(sys.executable)'"
                                    ], stage="PowerShell interpreter witness").stdout.strip()
                    self.assertEqual(Path(selected).resolve(), Path(sys.executable).resolve())
                    launch = [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                              str(helper.with_suffix(".ps1"))]
                else:
                    launch = [sys.executable, "-B", str(helper)]
                self.assertIn("usage:", run([*launch, "--help"], stage="installed help").stdout.lower())
                version = run([*launch, "--version"], stage="installed helper identity")
                digest = hashlib.sha256(helper.read_bytes()).hexdigest()
                self.assertEqual(version.stdout, f"autoreview source-sha256:{digest}\n")
                self.assertEqual(version.stderr, "")
                self.assertIn("unrecognized arguments: --unknown-option",
                              run([*launch, "--unknown-option"], 2, stage="installed unknown option").stderr)
                self.assertEqual(tree(scratch), before)

                # Import the copied helper in a fresh interpreter: exercise real optional
                # imports and decoders, never the model runner or an import mock.
                probe = r'''
import base64, importlib.util, json, runpy, sys
from pathlib import Path
helper, config, extras = sys.argv[1:]
assert (importlib.util.find_spec("PIL") is not None) == (extras == "present")
assert (importlib.util.find_spec("tomli") is not None) == (extras == "present")
native = runpy.run_path(helper)
Path(config).write_text('[route]\nname = "fixture 雪"\nretries = 2\n', encoding="utf-8")
try:
    result = native["load_codex_auth_config"](Path(config), strict=True)
except SystemExit as error:
    assert sys.version_info[:2] == (3, 10) and extras == "absent", str(error)
    assert "Python 3.11 or tomli" in str(error)
    parser = "unavailable"
else:
    assert result == {"route": {"name": "fixture 雪", "retries": 2}}, result
    parser = "tomllib" if sys.version_info >= (3, 11) else "tomli"
    assert parser in sys.modules
png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
try:
    media_type = native["image_media_type"]("fixture.png", png)
except SystemExit as error:
    assert extras == "absent", str(error)
    assert "requires Pillow" in str(error)
    image = "unavailable"
else:
    assert extras == "present" and media_type == "image/png", media_type
    image = media_type
print(json.dumps({"parser": parser, "image": image}))
'''
                config = scratch / "operator-fixture.toml"
                result = run([sys.executable, "-I", "-B", "-c", probe,
                              str(helper), str(config), OPTIONS.extras], stage="installed optional dependencies")
                config.unlink()
                self.assertEqual(tree(scratch), before)
                print(json.dumps({"archive": filename, "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                                  "head": head, "files": len(content), "python": platform.python_version(),
                                  "os": platform.system(), "arch": platform.machine(),
                                  "extras": OPTIONS.extras, "optional": json.loads(result.stdout)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--extras", choices=("absent", "present"), required=True)
    OPTIONS = parser.parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)
