from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


WORKSPACE = Path(os.environ["GITHUB_WORKSPACE"])
SOURCE = WORKSPACE / "source"
VARIANT = os.environ["PROOF_VARIANT"]
PHASE = os.environ["PROOF_PHASE"]
HEADS = {
    "baseline": "82ed255a43c1bc141f94f0b1053566910d3a32bf",
    "candidate": "4a9d6b6b6410a8d6c0d17093ceff4cec47d36f34",
}
RESULTS = {"variant": VARIANT, "phase": PHASE, "hot": [], "controls": []}


def command(root: Path, args: list[str], success: bool = True):
    started = time.perf_counter()
    program = args[0] + ".cmd" if os.name == "nt" and args[0] == "npm" else args[0]
    result = subprocess.run([program, *args[1:]], cwd=root, text=True, capture_output=True, timeout=1000)
    elapsed = (time.perf_counter() - started) * 1000
    output = result.stdout + result.stderr
    if success and result.returncode:
        print(output, flush=True)
        raise RuntimeError(f"{args} failed with {result.returncode}")
    return elapsed, result.returncode, output


def qualify(root: Path, label: str):
    assert command(root, ["git", "rev-parse", "HEAD"])[2].strip() == HEADS[label]
    workflow = root.joinpath(".github/workflows/validate.yml").read_text()
    expected = "if: ${{ matrix.group == 'all' || matrix.group == 'core' }}"
    assert (expected in workflow) == (label == "candidate")
    assert not root.joinpath("node_modules").exists()


def install(root: Path, label: str):
    started = time.perf_counter()
    if label == "baseline":
        return command(root, ["npm", "ci", "--ignore-scripts"])[0]
    assert not root.joinpath("node_modules").exists()
    return (time.perf_counter() - started) * 1000


qualify(SOURCE, VARIANT)
RESULTS["versions"] = {
    "python": sys.version,
    "node": command(SOURCE, ["node", "--version"])[2].strip(),
    "npm": command(SOURCE, ["npm", "--version"])[2].strip(),
}
RESULTS["installMs"] = install(SOURCE, VARIANT)
elapsed, _, output = command(SOURCE, [sys.executable, "-B", "scripts/check-skills", "--group", "boundaries"])
counts = re.findall(r"Ran (\d+) tests? in ([\d.]+)s", output)
assert counts
assert "FAILED" not in output
RESULTS["realBoundaryGroup"] = {
    "ms": elapsed,
    "counts": counts,
    "ok": "OK" in output,
    "compilerPresent": SOURCE.joinpath("node_modules/typescript").exists(),
    "outputSha256": hashlib.sha256(output.encode()).hexdigest(),
}
assert RESULTS["realBoundaryGroup"]["compilerPresent"] == (VARIANT == "baseline")
assert RESULTS["realBoundaryGroup"]["ok"]

if VARIANT == "candidate" and PHASE == "restored":
    baseline = WORKSPACE / "hot-baseline"
    qualify(baseline, "baseline")
    RESULTS["hotPrimeInstallMs"] = install(baseline, "baseline")
    for repeat in range(3):
        order = ["baseline", "candidate"] if repeat % 2 == 0 else ["candidate", "baseline"]
        for label in order:
            root = baseline if label == "baseline" else SOURCE
            RESULTS["hot"].append({"label": label, "repeat": repeat + 1, "installMs": install(root, label)})
    for label, root in (("baseline", baseline), ("candidate", SOURCE)):
        _, status, output = command(root, [sys.executable, "-B", "scripts/check-skills", "--group", "ci-proof-invalid"], False)
        assert status != 0 and "invalid choice" in output
        RESULTS["controls"].append({"label": label, "control": "invalid validation group", "rejected": True})
        command(root, ["npm", "ci", "--ignore-scripts"])
        invalid = root / "skills/session-viewer/scripts/ci-proof-invalid.ts"
        assert not invalid.exists()
        try:
            invalid.write_text("const ciProofInvalid: string = 42;\nexport { ciProofInvalid };\n")
            _, status, output = command(root, ["npm", "run", "typecheck"], False)
            assert status != 0 and "TS2322" in output
            RESULTS["controls"].append({"label": label, "control": "real retained compiler rejects invalid TypeScript", "rejected": True})
        finally:
            invalid.unlink()
        command(root, [sys.executable, "-B", "scripts/check-skills.test.py"])
        RESULTS["controls"].append({"label": label, "control": "eight dispatcher tests including failed-gate/missing-executable rejection", "passed": True})

print("PROOF_JSON=" + json.dumps(RESULTS), flush=True)
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf8") as summary:
    summary.write("\n```json\n" + json.dumps(RESULTS, indent=2) + "\n```\n")
