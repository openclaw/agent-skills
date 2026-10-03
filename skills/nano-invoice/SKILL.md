---
name: nano-invoice
description: "Bind one Nano (XNO) payment to one order and prove it settled from the public ledger. Use when an agent sells for XNO and needs a non-custodial receipt that a settled block paid for a specific order."
---

# Nano Invoice

Tie a Nano (XNO) payment to the order it pays for, with a receipt anyone can
re-check from the public ledger. An XNO block is signed by the payer's key and
is readable from any public node, but it has no memo field: a settled block only
proves an address paid *something*. `nano-invoice` makes the binding explicit so
a seller never miscounts faucet / self-transfers as income, never issues two
invoices for one order, and refunds the account that actually paid.

Non-custodial: it never holds a key and never sends money. Python 3.10+,
standard library only.

Use when you sell for XNO (an endpoint, a tool, a job) and need to prove that a
payment settled *this* order, or when a buyer asks for a receipt it can verify
without trusting you.

## Install

```bash
pip install git+https://github.com/dhyabi2/nano-invoice
```

Or run without installing: `python -m nano_invoice ...` from a checkout.

## The one idea

```
pay_raw = amount_raw + tag          (1 XNO = 10**30 raw)
```

- The amount is a multiple of 10**6 raw, so the lowest six raw digits of the
  exact payment are a tag unique to one invoice. The tag costs the payer nothing
  measurable.
- One order key gives exactly one invoice (`inv_<hash>`), idempotently. The same
  key with a different price raises `OrderConflict`.
- A block settles an invoice only if it is confirmed, addressed to the
  merchant, sent after creation and before expiry, not from the merchant's own
  accounts or a configured not-income list, and not already bound to any
  invoice. The sender is read from the chain, never from a claim.

## Workflow

1. Create the invoice for a real order:

```bash
nano-invoice create --merchant nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7 \
  --amount-xno 0.25 --order-key order-1001 --expires-s 1800
```

   Give the buyer the exact raw amount (`pay_raw`) or a full-precision `nano:`
   URI, not a rounded decimal — a rounded amount drops the tag and matches
   nothing.

2. Check until it settles:

```bash
nano-invoice check --invoice inv_... --own nano_1cold... \
  --not-income nano_3faucet...=devnet-faucet
```

   It prints `state observations refunds`; states are
   `open -> paid | underpaid | overpaid | expired`, and anything other than
   `open` is final.

3. Emit and verify a receipt when paid:

```bash
nano-invoice receipt --invoice inv_... > receipt.json
nano-invoice verify --receipt receipt.json     # exit 0 only if every check passes
```

   `verify` re-checks the id, the tag arithmetic, and every ledger claim against
   a public node. An unreachable node is reported as not verified, never as
   verified.

4. Refund instructions (nothing is sent by the tool):

```bash
nano-invoice refund-hint --invoice inv_...     # {to, amount_raw, reason, source_block}
```

## Receipts you can hand back

A receipt lists the fields and the exact `block_info` calls that reproduce the
claim, so the buyer (or a third party) re-derives it from any public node without
trusting you. The block IS the receipt: public, un-revocable, feeless, readable
by any agent that can call an RPC.

## Boundaries, stated plainly

- The payer must send the exact amount. A payment that matches no tag is not
  recorded and needs a manual refund.
- One merchant account supports up to ~999,999 open invoices (fewer, counting a
  7-day tag quarantine). Use several receiving accounts if you need more.
- Timing proof uses the node's `local_timestamp` with 120 s tolerance; a node
  that reports no timestamp cannot prove timing and such blocks are ignored.
- The scan reads at most 1000 history entries per check; a busy merchant should
  check often or use a dedicated receiving account.
- The receipt proves a confirmed send of exactly `pay_raw` from sender to
  merchant. That it meant *this order* rests on the tag allocation, which anyone
  holding the order key can re-derive.

## Source

https://github.com/dhyabi2/nano-invoice — MIT. Built as part of our open toolset
for agents paid in XNO (alongside settlement-verification and receipt tools).
