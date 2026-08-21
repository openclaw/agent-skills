---
name: lnurl-auth
description: "Authenticate to LNURL-auth (LUD-04) services without a wallet, node, or payment. Use when a site provides an lnurl1... challenge for Sign in with Lightning."
version: 1.4.1
homepage: https://github.com/dyegolara/lnurl-auth-agents
metadata:
  openclaw:
    requires:
      bins: [node]
    envVars:
      - name: LNURL_AUTH_KEYFILE
        required: false
        description: Optional path for the persistent 32-byte master secret.
---

# LNURL-auth (LUD-04)

Use this skill for authentication only. It signs a service-provided `k1`
challenge with a secp256k1 linking key and sends the signature to the service.
It never creates an invoice, makes a payment, or requires a Lightning node or
wallet.

## Inputs

- An `lnurl1...` string from a Sign in with Lightning link, QR code, or page.
- Optional `--dry-run` when the callback must be inspected before submission.
- Optional `--single-key` when one linking key must be shared across domains.

Do not invent or alter the `lnurl1...` value. Ask for a fresh challenge when a
service reports that the challenge was already used.

## Run

The bundled helper uses only Node.js built-ins and is located at:

```text
<skill_dir>/scripts/lnurl_auth.js
```

Inspect the decoded URL and signature without authenticating:

```bash
node <skill_dir>/scripts/lnurl_auth.js "<lnurl1...>" --dry-run --json
```

After the user confirms that the service and callback are expected, submit the
authentication request:

```bash
node <skill_dir>/scripts/lnurl_auth.js "<lnurl1...>" --json
```

The helper requires Node.js 20.19 or newer. The only network requests are the
optional challenge GET and the final callback GET. The callback host comes
from the decoded LNURL unless the user explicitly supplies `--callback`.

## Protocol

1. Decode the bech32 `lnurl1...` value into a service URL.
2. Read the 32-byte hexadecimal `k1` challenge, fetching it with a GET when it
   is not already in the URL.
3. Derive a stable per-domain linking key from the local master secret using
   HMAC-SHA256, unless `--single-key` is selected.
4. Sign the raw `k1` bytes with secp256k1 and encode the signature as DER.
5. GET the callback with the existing query parameters plus `sig` and `key`.

The master secret is generated once at
`~/.config/lnurl-auth/master.key` (or at `LNURL_AUTH_KEYFILE`) and is written
with mode `0600`. Never print, paste, or send the master secret.

## Results and failures

- JSON output contains the decoded service URL, domain, `k1`, compressed
  linking public key, callback URL, HTTP status, and service response.
- Exit `0`: the service returned `status: OK`.
- Exit `1`: malformed input, invalid key/challenge, or a network/client error.
- Exit `2`: missing input or an unknown command-line option.
- Exit `3`: the service returned `status: ERROR`.
- Exit `4`: the service returned a non-200 or non-JSON response.

Do not retry a submitted challenge. A signature verification error usually
means the service received a different key or the challenge was modified.
