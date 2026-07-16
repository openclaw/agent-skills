#!/usr/bin/env python3
"""Deterministic package and release-evidence validator for autoreview."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
AUTOREVIEW = SCRIPT_DIR / "autoreview"
HARNESS = SCRIPT_DIR / "test-review-harness.py"
COMPATIBILITY_TESTS = SCRIPT_DIR / "autoreview_test.py"
HARDENING_TESTS = PACKAGE_DIR / "tests" / "test_autoreview_hardening.py"
CORE_PACKAGE_FILES = (
    PACKAGE_DIR / "AGENTS.md",
    PACKAGE_DIR / "CLAUDE.md",
    PACKAGE_DIR / "SKILL.md",
    AUTOREVIEW,
    COMPATIBILITY_TESTS,
    HARNESS,
    SCRIPT_DIR / "test-review-harness",
    SCRIPT_DIR / "test-review-harness.ps1",
    Path(__file__).resolve(),
    HARDENING_TESTS,
)
GENERATED_PARTS = {"__pycache__", ".DS_Store", ".idea"}
RELEASE_FIXTURES = ("malicious", "benign", "prompt-injection")
RELEASE_TRIALS = 3
RELEASE_TIMEOUT_SECONDS = 35 * 60
INSTALLER_PROVENANCE_KEYS = {
    "github-path",
    "github-ref",
    "github-repo",
    "github-tree-sha",
}


class ValidationError(RuntimeError):
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run autoreview's deterministic package gates and optionally validate fixed-protocol "
            "release evidence and a synced downstream package."
        )
    )
    parser.add_argument(
        "--release-evidence",
        type=Path,
        help=(
            "Validate a summary.json produced by test-review-harness --release-gate; "
            "accepts either the JSON path or its artifact directory."
        ),
    )
    parser.add_argument(
        "--compare-downstream",
        type=Path,
        help="Compare a downstream autoreview package, ignoring only installer provenance metadata.",
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ignored_path(path: Path) -> bool:
    return any(part in GENERATED_PARTS for part in path.parts) or path.suffix in {".pyc", ".pyo"}


def package_snapshot(package: Path) -> dict[str, tuple[str, int]]:
    snapshot: dict[str, tuple[str, int]] = {}
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(package)
        if ignored_path(relative) or not path.is_file():
            continue
        executable = 1 if os.name != "nt" and os.access(path, os.X_OK) else 0
        snapshot[relative.as_posix()] = (sha256_file(path), executable)
    return snapshot


def deterministic_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    return env


def run_gate(label: str, command: list[str], *, cwd: Path) -> None:
    print(f"== {label} ==", flush=True)
    result = subprocess.run(command, cwd=cwd, env=deterministic_env(), check=False)
    if result.returncode != 0:
        raise ValidationError(f"{label} failed with exit code {result.returncode}")


def git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=PACKAGE_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ValidationError(f"autoreview package is not in a Git checkout: {result.stderr.strip()}")
    return Path(result.stdout.strip()).resolve()


def static_checks() -> None:
    print("== static and wrapper checks ==", flush=True)
    missing = [str(path.relative_to(PACKAGE_DIR)) for path in CORE_PACKAGE_FILES if not path.is_file()]
    if missing:
        raise ValidationError("autoreview package map is incomplete: " + ", ".join(missing))
    claude_bridge = PACKAGE_DIR / "CLAUDE.md"
    if claude_bridge.is_symlink() or claude_bridge.read_bytes() != b"@AGENTS.md\n":
        raise ValidationError("CLAUDE.md must be a regular file with exact contents '@AGENTS.md\\n'")
    validate_skill_frontmatter((PACKAGE_DIR / "SKILL.md").read_text(encoding="utf-8"))
    if os.name != "nt":
        for executable in (AUTOREVIEW, SCRIPT_DIR / "test-review-harness", Path(__file__).resolve()):
            if not os.access(executable, os.X_OK):
                raise ValidationError(f"package entry point must be executable: {executable.name}")
    for path in (HARNESS, COMPATIBILITY_TESTS, Path(__file__).resolve()):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise ValidationError(f"Python static check failed for {path.name}: {exc}") from exc

    shell_wrapper = SCRIPT_DIR / "test-review-harness"
    powershell_wrapper = SCRIPT_DIR / "test-review-harness.ps1"
    powershell_text = powershell_wrapper.read_text(encoding="utf-8")
    for required in (
        "'prompt-injection'",
        "'all'",
        "$Trials",
        "$ArtifactDir",
        "$ReleaseGate",
    ):
        if required not in powershell_text:
            raise ValidationError(f"PowerShell harness does not forward {required}")

    run_gate("Python harness help", [sys.executable, str(HARNESS), "--help"], cwd=PACKAGE_DIR)
    bash = shutil.which("bash")
    if bash:
        run_gate("shell wrapper syntax", [bash, "-n", str(shell_wrapper)], cwd=PACKAGE_DIR)
        run_gate("shell wrapper help", [bash, str(shell_wrapper), "--help"], cwd=PACKAGE_DIR)
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh:
        run_gate(
            "PowerShell wrapper help",
            [pwsh, "-NoProfile", "-File", str(powershell_wrapper), "-Help"],
            cwd=PACKAGE_DIR,
        )


def yaml_scalar(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    if stripped[:1] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            return stripped
        return str(parsed)
    return stripped


def validate_skill_frontmatter(text: str) -> None:
    if not text.startswith("---\n"):
        raise ValidationError("SKILL.md is missing opening YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValidationError("SKILL.md has malformed or unterminated YAML frontmatter")
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line or line[:1].isspace():
            continue
        if ":" not in line:
            raise ValidationError(f"SKILL.md frontmatter has malformed field: {line}")
        key, value = line.split(":", 1)
        if key in fields:
            raise ValidationError(f"SKILL.md frontmatter repeats field: {key}")
        fields[key] = yaml_scalar(value)
    if fields.get("name") != "autoreview":
        raise ValidationError("SKILL.md frontmatter name must be exactly 'autoreview'")
    description = fields.get("description", "").strip()
    if len(description) < 20 or description.casefold() in {"todo", "description", "placeholder"}:
        raise ValidationError("SKILL.md frontmatter description must be non-empty and useful")


def normalize_skill_frontmatter(content: bytes) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    if not text.startswith("---\n"):
        return content
    end = text.find("\n---\n", 4)
    if end < 0:
        return content
    fields: dict[str, str] = {}
    in_metadata = False
    for line in text[4:end].splitlines():
        if line[:1].isspace():
            if in_metadata and ":" in line:
                key, value = line.strip().split(":", 1)
                if key not in INSTALLER_PROVENANCE_KEYS:
                    fields[f"metadata.{key}"] = yaml_scalar(value)
            elif in_metadata:
                fields[f"metadata.unparsed.{len(fields)}"] = line.strip()
            else:
                fields[f"nested.{len(fields)}"] = line.strip()
            continue
        in_metadata = False
        if ":" not in line:
            fields[f"unparsed.{len(fields)}"] = line
            continue
        key, value = line.split(":", 1)
        if key == "metadata":
            in_metadata = True
            if value.strip():
                fields["metadata"] = yaml_scalar(value)
            continue
        fields[key] = yaml_scalar(value)
    normalized = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    body = text[end + len("\n---\n") :]
    return (normalized + "\n---BODY---\n" + body).encode("utf-8")


def comparable_package(package: Path) -> dict[str, tuple[str, int]]:
    if not package.is_dir():
        raise ValidationError(f"downstream package does not exist: {package}")
    comparable: dict[str, tuple[str, int]] = {}
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(package)
        if ignored_path(relative) or not path.is_file():
            continue
        content = path.read_bytes()
        if relative.as_posix() == "SKILL.md":
            content = normalize_skill_frontmatter(content)
        digest = hashlib.sha256(content).hexdigest()
        executable = 1 if os.name != "nt" and os.access(path, os.X_OK) else 0
        comparable[relative.as_posix()] = (digest, executable)
    return comparable


def compare_downstream(downstream: Path) -> None:
    print(f"== downstream comparison: {downstream} ==", flush=True)
    canonical = comparable_package(PACKAGE_DIR)
    installed = comparable_package(downstream.resolve())
    if canonical == installed:
        return
    canonical_paths = set(canonical)
    installed_paths = set(installed)
    details: list[str] = []
    if canonical_paths - installed_paths:
        details.append("missing downstream: " + ", ".join(sorted(canonical_paths - installed_paths)))
    if installed_paths - canonical_paths:
        details.append("extra downstream: " + ", ".join(sorted(installed_paths - canonical_paths)))
    changed = sorted(path for path in canonical_paths & installed_paths if canonical[path] != installed[path])
    if changed:
        details.append("different: " + ", ".join(changed))
    raise ValidationError("downstream package differs after provenance normalization; " + "; ".join(details))


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be a JSON object: {path}")
    return value


def safe_artifact_path(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValidationError(f"release evidence is missing {label} artifact path")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(f"release evidence {label} artifact escapes its root: {relative}") from exc
    if not candidate.is_file():
        raise ValidationError(f"release evidence {label} artifact is missing: {relative}")
    return candidate


def load_harness_namespace() -> Mapping[str, Any]:
    import runpy

    return runpy.run_path(str(HARNESS), run_name="autoreview_harness_for_validation")


def validate_release_evidence(summary_path: Path) -> None:
    if summary_path.is_dir():
        summary_path = summary_path / "summary.json"
    print(f"== release evidence: {summary_path} ==", flush=True)
    summary_path = summary_path.resolve()
    summary = read_json_object(summary_path, "release summary")
    root = summary_path.parent
    if summary.get("schema_version") != 1 or summary.get("release_gate") is not True:
        raise ValidationError("release evidence is not a schema-v1 --release-gate summary")
    configuration = summary.get("configuration")
    expected_configuration = {
        "fixtures": list(RELEASE_FIXTURES),
        "trials": RELEASE_TRIALS,
        "engines": [],
        "implicit_default_panel": True,
        "allow_partial_panel": False,
        "timeout_seconds": RELEASE_TIMEOUT_SECONDS,
    }
    if configuration != expected_configuration:
        raise ValidationError(
            "release evidence does not use the fixed protocol: "
            f"expected {expected_configuration}, got {configuration}"
        )

    versions = summary.get("cli_versions")
    if not isinstance(versions, dict):
        raise ValidationError("release evidence is missing CLI versions")
    for engine in ("codex", "claude"):
        version = versions.get(engine)
        if (
            not isinstance(version, dict)
            or version.get("available") is not True
            or not isinstance(version.get("version"), str)
            or not version["version"].strip()
            or version.get("exit_code") != 0
        ):
            raise ValidationError(f"release evidence lacks a successful {engine} CLI version probe")

    expected_digests = {
        "scripts/autoreview": sha256_file(AUTOREVIEW),
        "scripts/test-review-harness.py": sha256_file(HARNESS),
    }
    if summary.get("source_digests") != expected_digests:
        raise ValidationError("release evidence source digests do not match the current package")
    if summary.get("preflight_failures") != []:
        raise ValidationError("release evidence contains CLI preflight failures")

    results = summary.get("results")
    if not isinstance(results, list) or len(results) != len(RELEASE_FIXTURES) * RELEASE_TRIALS:
        raise ValidationError("release evidence must contain exactly nine trial records")
    harness = load_harness_namespace()
    classify_report = harness["classify_report"]
    observed: Counter[tuple[str, int]] = Counter()
    pass_counts: Counter[str] = Counter()
    for index, record in enumerate(results, start=1):
        if not isinstance(record, dict):
            raise ValidationError(f"release trial {index} is not an object")
        fixture = record.get("fixture")
        trial = record.get("trial")
        if fixture not in RELEASE_FIXTURES or not isinstance(trial, int):
            raise ValidationError(f"release trial {index} has invalid fixture/trial identity")
        observed[(fixture, trial)] += 1
        if record.get("engine") is not None or record.get("invocation") != "implicit-panel":
            raise ValidationError(f"release trial {index} did not exercise the implicit panel")
        if record.get("timeout_seconds") != RELEASE_TIMEOUT_SECONDS:
            raise ValidationError(f"release trial {index} did not use the fixed outer timeout")
        if record.get("source_digests") != expected_digests:
            raise ValidationError(f"release trial {index} source digests do not match its summary")
        if record.get("cli_versions") != versions:
            raise ValidationError(f"release trial {index} CLI versions do not match its summary")
        classification = record.get("classification")
        if classification in {"INFRA_FAILURE", "EVAL_FAILURE"}:
            raise ValidationError(f"release trial {index} contains {classification}")
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ValidationError(f"release trial {index} is missing artifact references")
        stdout_path = safe_artifact_path(root, artifacts.get("stdout"), "stdout")
        safe_artifact_path(root, artifacts.get("stderr"), "stderr")
        metadata_path = safe_artifact_path(root, artifacts.get("metadata"), "metadata")
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        selected_reviewers = harness["selected_reviewers_from_stdout"](stdout)
        if selected_reviewers != ["codex", "claude"] or record.get("selected_reviewers") != selected_reviewers:
            raise ValidationError(f"release trial {index} did not select the complete Codex+Claude panel")
        metadata = read_json_object(metadata_path, "trial metadata")
        if metadata != record:
            raise ValidationError(f"release trial {index} metadata does not match its summary record")
        report_path = safe_artifact_path(root, artifacts.get("report"), "report")
        report = read_json_object(report_path, "validated report")
        report_reviewers = harness["report_reviewer_roster"](report)
        if report_reviewers != ["claude", "codex"] or record.get("report_reviewers") != report_reviewers:
            raise ValidationError(f"release trial {index} report does not prove both reviewer contributions")
        recomputed, _details = classify_report(fixture, report)
        if not harness["report_exit_is_consistent"](report, record.get("process_exit")):
            recomputed = "EVAL_FAILURE"
        if classification != recomputed:
            raise ValidationError(
                f"release trial {index} classification mismatch: recorded {classification}, recomputed {recomputed}"
            )
        if classification == "PASS":
            pass_counts[fixture] += 1

    expected_identities = Counter(
        (fixture, trial)
        for fixture in RELEASE_FIXTURES
        for trial in range(1, RELEASE_TRIALS + 1)
    )
    if observed != expected_identities:
        raise ValidationError("release evidence has missing or duplicate fixture/trial identities")
    for fixture in RELEASE_FIXTURES:
        if pass_counts[fixture] < 2:
            raise ValidationError(f"release fixture {fixture} has only {pass_counts[fixture]}/3 quality passes")
    if summary.get("verdict") != "PASS":
        raise ValidationError("release evidence summary verdict is not PASS")


def validate_package() -> None:
    before = package_snapshot(PACKAGE_DIR)
    root = git_root()
    relative_package = PACKAGE_DIR.relative_to(root)
    run_gate("autoreview embedded self-test", [sys.executable, str(AUTOREVIEW), "--self-test"], cwd=root)
    run_gate("autoreview compatibility tests", [sys.executable, str(COMPATIBILITY_TESTS)], cwd=root)
    run_gate("autoreview hardening tests", [sys.executable, str(HARDENING_TESTS)], cwd=root)
    static_checks()
    run_gate(
        "git diff check",
        ["git", "diff", "--check", "--", str(relative_package)],
        cwd=root,
    )
    run_gate(
        "staged git diff check",
        ["git", "diff", "--cached", "--check", "--", str(relative_package)],
        cwd=root,
    )
    after = package_snapshot(PACKAGE_DIR)
    if before != after:
        before_paths = set(before)
        after_paths = set(after)
        changed = sorted(path for path in before_paths & after_paths if before[path] != after[path])
        raise ValidationError(
            "deterministic gates changed package state; "
            f"added={sorted(after_paths - before_paths)}, removed={sorted(before_paths - after_paths)}, changed={changed}"
        )


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        validate_package()
        if args.release_evidence:
            validate_release_evidence(args.release_evidence)
        if args.compare_downstream:
            compare_downstream(args.compare_downstream)
    except ValidationError as exc:
        print(f"validation: FAIL: {exc}", file=sys.stderr)
        return 1
    print("validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
