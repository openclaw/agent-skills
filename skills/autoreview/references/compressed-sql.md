# Compressed SQL

Only binary-classified branch additions or modifications at case-sensitive
`.sql.gz` paths receive decoding. Plain text and symlink paths keep their existing
review behavior. Every present side must be a regular committed blob. Working files,
Git textconv and external filters cannot supply the decoded contents. Sensitive
paths are checked before decoding. Binary deletions keep their existing metadata
review. Local and commit mode do not gain compressed-file support.

Each side must contain exactly one complete gzip member with a valid checksum.
Truncation, concatenated members, trailing bytes, invalid UTF-8 and decoded NUL
bytes fail preparation. The helper never executes SQL, writes into the reviewed
repository, or extracts archive filenames. It creates transient decoded files in a private
temporary directory outside the reviewed repository and removes them after diff
preparation. Gzip header names and comments are not
interpreted or displayed. Exact encoded hashes bind those bytes as provenance.

Limits apply before reading the compressed blob and while decoding:

- 20 MiB encoded per side and 100 MiB encoded across all decoded sides.
- 32 MiB decoded per side and 100 MiB decoded across all decoded sides.
- 30 seconds per decoded text diff. A timeout fails preparation.

The textual projection uses the original `.sql.gz` path. Finding lines refer to
its decoded SQL, with line 1 for a compression-only finding. Every projection
records both sides' full Git object IDs, modes, encoded and decoded byte counts,
and SHA-256 hashes. That provenance repeats in continuation context when a diff
is partitioned. Recompression with identical decoded text still produces review
input. It is never silently classified as clean.

Git patch capture remains strict UTF-8. Attributes that force gzip bytes into a
text patch may therefore fail preparation even when decoding would succeed.
They cannot bypass decoding or binary refusal. Explicit `--review-batches`
continues to require its existing text-only range and refuses these projections.

This checks gzip structure and text reviewability, not SQL syntax, generator
reproducibility, database equivalence, or the safety of applying the SQL. Supply
needed generator and manifest context through the normal context flags. Reviewers
still assess the complete supplied assignment and report incomplete assessments.
