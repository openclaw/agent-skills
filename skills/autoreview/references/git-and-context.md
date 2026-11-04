# Git collection and context

## Git collection

- Registered nested linked checkouts from same repository: outside current review
  scope; presence/edits do not make parent dirty. Ordinary adjacent files stay included.
- Revalidate worktree boundaries without changing Git ignore rules.

- Local status columns come from the captured base → index and index → working-tree
  diff queues, not a separate HEAD-relative status. Paths are JSON strings; renames
  appear as add/delete transitions, matching the no-renames patches.

- Git display settings cannot suppress context markers or add patch colors;
  repository configuration unchanged. Source paths/text retain literal whitespace.
- Empty present source: line 1, column 1, empty excerpt. Empty physical lines:
  empty excerpt at column 1. Source identity mandatory.

- Binary deletions stay in scope as Git deletion metadata; former contents neither
  included nor reviewed. Check each local transition independently:
  deleting working-tree file cannot hide staged binary change.

- Finding locations may use native absolute paths resolving inside reviewed
  repository; convert to repository-relative before scope/attribution checks.
  Preserve changed symlink's path when target also inside.
- Parent traversal/paths resolving outside repository: invalid.
  Invalid location fails report; never silently drop findings.

- Local selection honors external operator Git `core.autocrlf`; repository-local
  values/attributes keep precedence. Only validated scalar value reaches diff/status;
  other global/system Git configuration stays disabled.
- Never import repository-owned/relative global-config overrides or rewrite reviewed source bytes.

- Local collection disables effective Git clean/process commands; conversion must
  succeed. Unused drivers, unchanged filtered neighbors, staged-only changes,
  deletions: reviewable without executing converters.
- Git needs executable conversion to assemble diff: fail collection before reviewer
  starts. Can include unchanged filtered file whose stat cache needs refreshing.
  Use explicit branch/commit mode for committed content then.
- Built-in line-ending normalization stays enabled; raw bytes never substitute
  for required executable conversion.
- PR-base discovery: trusted external Git + scoped GitHub CLI environment;
  preserve external authentication/configuration + proxy settings; exclude inherited
  Git routing, `GH_REPO` redirection, checkout-owned executables.
- Differently named `AUTOREVIEW_GIT` override child cannot also select as `git`:
  explicit `--base` required. Rejected GitHub configuration paths: same requirement.

## Submodule pins

Gitlink changes (mode `160000`) include full old/new commit IDs and the path's
URLs from the corresponding `.gitmodules` states. Branch/commit mode reads frozen
blobs; local mode reads base, index and working-tree mappings independently.
Local Git config, URL rewrites, includes and submodule update commands are not used.
Missing mappings are explicit `null` values; ambiguous mappings fail preparation.

This reviews the superproject pin and integration, not the upstream code. No
network fetch or submodule checkout runs. To review upstream changes, explicitly
fetch the range in a separate checkout and supply relevant evidence with
`--dataset`; that context does not expand finding scope beyond the superproject.
Uncommitted submodule contents and mixed staged/unstaged gitlink changes remain
unsupported; use committed branch/commit mode for pin reviews. Other source,
authentication, sandbox and mutation checks remain enabled.

## Committed source context

- Basic context flags/safety rules: [SKILL.md](../SKILL.md#context-and-severity).
- Repeated paths in same evidence role share one validated capture. Equal content
  at different paths and prompt-file versus dataset roles stay distinct.

- Unchanged committed source: repeatable `--source-context <repo-relative-path>`
  with branch/commit mode. Source must stay intact every review pass:
  `--source-context-file <repo-relative-path>`.
- Both read exact regular-file blob from frozen reviewed commit (branch HEAD or
  `--commit`), including executable source files.
- Local mode, including auto-selected local target: unsupported.
  No separate context revision or working-copy substitution accepted.
- Checkout path must stay regular file; revalidate bytes/path topology throughout review.
- Repeated normalized source-context paths share one capture after validating every
  argument; different paths/evidence roles stay distinct.

- Both roles: tracked-source filename classification; source names such as
  `src/token_count.py` accepted. Credential directories, stores, keyfiles forbidden.
  Existing prompt-file/dataset restrictions unchanged.
- Every source block: path, commit, blob, mode provenance.
- `--source-context` bytes: partition with change when needed.
- `--source-context-file` blocks: complete every pass; must fit with instructions
  + change framing. Over-capacity plan: refuse, never drop required evidence.
- Context never adds finding targets/instruction authority.
  Contract: source-provenance, not secret-content scanning.

```bash
"$AUTOREVIEW" --mode branch --base origin/main --source-context src/token_count.py
"$AUTOREVIEW" --mode branch --base origin/main --source-context-file src/token_count.py
```

## External committed source

When a change integrates another repository, supply its required source with
`--external-source-context-file <repo-relative-manifest.json>`. The manifest lives
in the reviewed repository; an ignored directory keeps it out of the change.
The source checkout must be a separate, canonical absolute Git worktree path.
The helper does not clone, fetch, install dependencies, or execute source code.

```json
{
  "version": 1,
  "root": "/absolute/path/to/upstream-checkout",
  "commit": "<full source commit OID>",
  "files": [
    {"path": "src/owner.ts", "blob": "<blob OID at that commit>", "mode": "100644"}
  ]
}
```

Resolve the exact commit and each blob/mode with Git before constructing this
inventory. Mutable refs, unknown fields, duplicate paths, missing files and
blob/mode mismatches fail preparation. Both SHA-1 and SHA-256 repositories are
supported. A linked worktree is permitted. For both the reviewed repository and
external sources, roots and Git metadata paths must not traverse symlinks or
Windows junctions; alternate object stores are unsupported. External source paths
have the same traversal restriction. The source root cannot contain or be inside
the reviewed repository. Before any Git probe, the helper discovers the reviewed
and external repositories' Git, common and object directories without running Git. These
directories and source roots are excluded from host executable selection, child
`PATH`, authentication and configuration paths, including reviewer probes and
trusted wrappers. A trusted `PATH` directory is excluded if
any entry redirects into a source root. Paths with source-owned intermediate
symlinks are also rejected, even when their final target is outside the source tree.
The same entry checks apply to selected executables' original and resolved
installation directories, including directories outside `PATH`.
Reports, status files and diagnostic outputs must stay outside every source root
and its Git metadata, including linked-worktree common directories and object
stores. Git rejects source-owned `HOME`, default ignore files and global
configuration paths that could hide changes. Trusted caller exclusions retain
their existing behavior.

Shared hardlinks in executable search directories or selected executable,
configuration, authentication and certificate files require custody independent
of the caller. Caller-owned read-only hardlinks are insufficient; use independent
single-link copies. On Linux, shared-file custody requires an empty permitted
capability set. On Windows, it allows only traversal, shutdown, undocking,
working-set and time-zone privileges; other available privileges fail custody
even when disabled, in either the process primary or effective thread token.
This conservative check applies only to shared inodes and does not assert
universal immutability. Independent single-link files bypass this custody check,
but do not relax the checks for other selected files. Native positive
verification uses a standard-user primary process, not temporary impersonation.

Windows Git preflight and reviewer launches use an owned Job Object and the
installed Python supervisor. These processes and their descendants join before
they execute and remain owned after their leader exits. Cleanup does not invoke
`taskkill.exe` or inspect its installation directory. The supervisor runs with
the direct base Python interpreter, avoiding a virtual-environment redirector
that could retain job or pipe handles. The supervisor and base Python installation
still pass the ordinary source-boundary checks. Target arguments and environment
are preserved. An incompatible enclosing job fails startup; there is no breakaway
or executable cleanup fallback.
Lost startup acknowledgement after permission to launch is a terminal
uncertain-launch error, so it cannot silently repeat a possibly executed command.
Startup cleanup waits are bounded. A stalled acknowledgement reader retains its
pipe descriptors until its I/O ends, but cannot keep the helper alive after
cleanup returns. Bounded waiting does not establish that failed cleanup completed.
Git startup timeouts and execution errors report cleanup failure types without printing command
arguments or raw exception messages.

Handled interrupts attempt termination for every registered process even if one
attempt fails. The first signal retains its exit status through buffered and
streaming cleanup; later handled signals do not restart the sweep. Cleanup
failures are reported by exception type, without changing cancellation into a
retryable launch failure.

Normalized `PATH`, `SSL_CERT_DIR` and `OPENCLAW_INCLUDE_ROOTS` entries must
survive path-list serialization unchanged.
`SSL_CERT_DIR` also checks its directory entries for source ownership and file
custody, including certificate and CRL links.
An unsafe or malformed nonempty `SSL_CERT_DIR` stops preparation before a child
starts: removing it could select the same rejected store through TLS defaults.
Configure independently held certificate directories outside the source roots.
Unset or empty selectors retain normal default lookup; implicit system stores
are not inventoried. Malformed include lists are omitted from reviewer
environments; an empty filtered executable `PATH` fails preparation.

The helper reads complete UTF-8 regular-file blobs from the declared commit,
not the source checkout's working bytes. Headers retain the original path,
source worktree, commit, blob and mode. Existing committed-source protections
still reject credential directories, stores and keyfiles. This role does not
relax `--prompt-file` or `--dataset` filename rules. Do not rename or concatenate
blocked evidence to bypass those rules.

The helper retains the initial Git metadata binding from before output preparation
through source capture and publication. Git collection rechecks that binding
before launch, after preparation queries such as executable-filter discovery.
The manifest, source paths, checkout identity, Git metadata/object-store paths
and captured source fingerprints are revalidated before every send, including
helper-initiated retries, and before publication.
Changes fail the review rather than silently rebinding a source. Freeze source
checkouts during the review, including their working files and metadata.

External source is context only. It does not add finding targets or certify the
upstream repository, release provenance, or runtime behavior. The operator must
establish that the chosen source commit matches the dependency being reviewed.
Report missing required contracts instead of inferring them from a source pin.

This option is repeatable, supports committed branch/commit mode, and composes
with `--review-batches`. Every selected external file stays whole in **every**
pass, including allocated passes. It cannot be partitioned by an allocation.
The complete input must fit the explicit prompt budget and model context; an
oversized plan fails before a reviewer starts.

## Runtime diagnostics

- Before repository detection/target selection: Git must pass `--version` within
  10 seconds. Failure: exit `2`, `incomplete` diagnostic + resolved executable
  (or unresolved selection); never `scoped-clean`.
- Executable discovery skips inaccessible search candidates;
  inaccessible explicit executable override still fails preflight.
- Set `AUTOREVIEW_GIT` to trusted external Git executable: override every
  helper-owned Git invocation.
  If an installation directory contains a rejected shared hardlink, select an
  independently admitted installation; the override still checks its directory
  entries. The diagnostic names the first rejected entry and reason.
- macOS, broken selected Xcode: use
  `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` for invocation.
- Git sanitized environment additionally retains only absolute, external
  `DEVELOPER_DIR`; neither override forwarded to isolated reviewer environment.

## Partition planning

- Text review files: no size/count cap; never truncate. Image inputs:
  [image safety limits](images.md). Partition large diffs/datasets automatically.
- Change partitions retain complete datasets when they fit with sufficient change
  space. Preference may cost more passes/prompt bytes than evidence batching;
  explicit pass budget still applies.
- Terminal fallbacks preserve feasible complete-evidence plan when batch framing cannot fit.
- Intact instructions, source-context files, required mixed source context must fit
  per-pass prompt budget. Failed pass never produces partial clean verdict.
- `--max-prompt-bytes N` selects that UTF-8 byte budget for dry-run and live review
  (default `512000`). The plan reports its limit and largest rendered prompt.
  A larger explicit budget admits more complete context only when it fits;
  it does not change engine/model context limits or guarantee token capacity.
- Otherwise compare bounded evidence allocations; keep existing plan unless total
  prompt bytes improve without more passes, or equal bytes need fewer passes.
- By default, every change is reviewed against every evidence batch.

## Explicit branch allocations

`--review-batches <repo-relative-json>` is an opt-in alternative to the default
cross-product planner. It allocates **one frozen complete branch capture**, never
independent path-filtered Git reviews. Version 1 accepts text additions, changes,
deletions and executable-mode changes. It refuses local/commit mode, sensitive
omissions, images, binary changes/deletions, symlinks and gitlinks. Use the ordinary
route for unsupported forms; do not remove them to obtain a clean allocation.

First run the ordinary branch `--dry-run` to obtain `bundle identity` (resolved
merge-base, HEAD, SHA-256 of the exact captured bundle). Keep the same `--base`
argument: its label is part of those bytes. Declare each source context's exact
HEAD blob and mode from Git. Store the operator manifest in an ignored directory
inside the reviewed repository, so a preflight export can still require a clean
branch. The helper rejects symlinked/unsafe inputs and revalidates manifest bytes
and path identity before every send and before publishing the aggregate.

```json
{
  "version": 1,
  "base": "<full resolved merge-base OID>",
  "head": "<full reviewed HEAD OID>",
  "bundle_sha256": "<dry-run bundle SHA-256>",
  "contexts": [
    {"path": "src/owner.py", "blob": "<HEAD blob OID>", "mode": "100644"}
  ],
  "batches": [
    {
      "name": "owner-and-caller",
      "kind": "integration",
      "changes": ["src/owner.py", "src/caller.py"],
      "contexts": ["src/owner.py"],
      "obligations": ["Verify the caller consumes the owner's settled result before publication."]
    }
  ]
}
```

- Exact fields and canonical paths only; no globs, commands, duplicate keys or
  relevance inference. Every changed path in the original range and every declared
  context must occur in an assignment. Repeating a changed unit or context across
  assignments is allowed for integration; repetition cannot hide an omission.
- Each assignment has a unique name, kind `owner` or `integration`, nonempty
  changed units, and explicit obligations. More than one assignment requires an
  integration assignment. The operator must supply its actual caller/callee
  contracts; naming it integration does not prove the chosen context sufficient.
- Units retain complete original patch headers/bytes and Git-owned before/after
  modes/OIDs. The helper checks exact reconstruction and records byte offsets,
  digests, manifest identity, assigned contexts and rendered prompt identities.
  Whole source blobs retain commit/blob/mode provenance and existing source checks.
- Each assignment is one intact pass. All assignments must fit the existing
  `--max-prompt-bytes` and `--max-review-passes` limits before any reviewer starts.
  The helper does not split required contracts or automatically raise a limit.
- `--source-context-file` and prompt instructions remain whole in **every** pass.
  `--source-context` and `--dataset` cannot combine with this mode; declare the
  complete source inventory in the manifest instead. Without this flag, existing
  context flags and cross-product planning are unchanged.
- Finding scope is the assignment's changed units. Out-of-assignment findings
  remain visible as scope-rejected and make the aggregate incomplete. An accepted
  integration finding remains actionable in the merged report. Every assignment
  independently returns complete/incomplete; missing contracts, invalid/failed
  reports, filtered findings and changed inputs cannot produce aggregate clean.
- Dry and live planning use the same capture/allocation/rendering path. JSON
  output retains `review_allocation` and per-assignment outcomes. Native preflight
  export retains its clean committed full-range requirement and projects aggregate
  completion/status, never an individual assignment's success.

This mode changes evidence placement, not authority, review status, model,
transport, sandbox, timeouts or publication gates. A successful fit only admits
the review; the reviewers still decide whether the supplied evidence is sufficient.
