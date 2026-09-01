---
name: guardclaw-audit
description: "Cryptographically logs and verifies autonomous agent tool executions into a tamper-evident, Ed25519 hash-chained GEF ledger."
---

# GuardClaw Cryptographic Execution Audit

Best-effort local-only cryptographic flight recorder for OpenClaw agents. Use during autonomous coding, terminal commands, file mutations, or database operations to produce offline-verifiable proof that agent actions were unaltered.

## Contract

- **Zero network**: Audit ledgers are signed locally with Ed25519 keys and written to the local filesystem.
- **RFC 8785 Canonicalization**: JSON envelopes are canonicalized using RFC 8785 (JCS) before hashing.
- **SHA-256 Causal Chaining**: Every record cryptographically seals the previous event hash.
- **Offline Verifiable**: Any user or CI process can verify chain integrity using `guardclaw verify <DIR>`.

## Quickstart

Install the lightweight audit library:

```bash
pip install guardclaw
```

### 1. Emit Signed Intent & Execution Receipts

```python
from guardclaw import GEFLedger, Ed25519KeyManager, RecordType

# Initialize session ledger in local vault
key_mgr = Ed25519KeyManager.generate()
ledger = GEFLedger(
    key_manager=key_mgr,
    agent_id="openclaw-agent",
    ledger_path="./.agent_audit",
)

# Record intent before running a high-stakes command
intent = ledger.emit(
    record_type=RecordType.TOOL_CALL,
    payload={
        "tool": "terminal.execute",
        "command": "git push origin main",
        "purpose": "Deploying release candidate",
    },
)

# Record result after execution
ledger.emit(
    record_type=RecordType.TOOL_RESULT,
    payload={
        "tool": "terminal.execute",
        "status": "success",
        "intent_record_id": intent.record_id,
    },
)
```

### 2. Verify Ledger Integrity

Verify from the command line:

```bash
guardclaw verify ./.agent_audit
```

Or verify in Python:

```python
from guardclaw import verify_ledger

summary = verify_ledger("./.agent_audit")
if summary["chain_valid"]:
    print(f"Verified {summary['verified_count']} records with zero tampering.")
else:
    print(f"Tampering detected: {summary['failure_detail']}")
```
