# Releasing

This catalog distributes skills and helper scripts directly from Git. Its private
npm manifests are development tooling, not registry packages. `release-source.yml`
runs the catalog checks and publishes frozen-commit source tar/zip archives with
the exact changelog notes, inventory, and `SHA256SUMS`. Independent push CI must
also pass Linux, Windows, and native macOS sandbox checks.

The `Release` workflow calls the shared OpenClaw archetype at `@v1`. It
requires a protected `main`, matching version metadata, a dated changelog section,
and successful independent **push** CI on the exact release commit. It verifies
SSH-signed annotated tags against `.github/release-allowed-signers` and rejects
moved tags or an existing GitHub Release.

Prepare the version and dated `## X.Y.Z - YYYY-MM-DD` changelog section in a PR,
retain `## Unreleased`, and merge only after CI and review. After explicit release
authorization, create and push an SSH-signed annotated `vX.Y.Z` tag at that merged
commit using an allowed signing key. Tag pushes publish through Actions; manual
GitHub Release creation is retired. A live dispatch cannot create a missing signed
tag: create the signed tag first.

For a no-publish rehearsal, dispatch `release.yml` on current `main` with a version
that already has a dated changelog section and `dry_run=true` (the default):

```sh
gh workflow run release.yml --ref main -f version=0.5.0 -f dry_run=true
```

The rehearsal exercises current protected main, even when the version already has
an older tag. It creates no tag, release, or registry publication. Inspect every
job and the retained verification artifacts before release. Real releases never
move a tag or overwrite an existing version.

Update `.release-version` with the changelog version in each release preparation PR.
