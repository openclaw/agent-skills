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

Install the lightweight audit library (pinned release):

```bash
pip install "guardclaw==0.8.2"
```

### 1. Emit Signed Intent & Execution Receipts

```python
from pathlib import Path
from guardclaw import GEFLedger, Ed25519KeyManager, RecordType

# 1. Load or persist trusted signing key outside the audited directory
trusted_key_dir = Path.home() / ".openclaw" / "keys"
trusted_key_dir.mkdir(parents=True, exist_ok=True)
key_file = trusted_key_dir / "agent_signing_key.json"

if key_file.exists():
    key_mgr = Ed25519KeyManager.load(str(key_file))
else:
    key_mgr = Ed25519KeyManager.generate()
    key_mgr.save(str(key_file))

# Store the expected public key in a secure, trusted configuration location
trusted_pubkey = key_mgr.public_key_hex

# 2. Initialize ledger
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

### 2. Verify Ledger Integrity Against Pinned Signer

Verify from the command line:

```bash
guardclaw verify ./.agent_audit --pinned-key "$TRUSTED_PUBKEY"
```

Or verify in Python against the pinned trusted public key:

```python
from guardclaw import verify_ledger

# Verifier supplies expected public key anchored outside the ledger
summary = verify_ledger("./.agent_audit")

# Ensure the chain is mathematically valid AND signed by the trusted agent identity
if summary["chain_valid"] and summary.get("signer_public_key") == trusted_pubkey:
    print(f"Verified {summary['verified_count']} records with zero tampering from trusted agent.")
else:
    print(f"Verification failed or untrusted signer: {summary.get('failure_detail')}")
```
