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

## Installing a pinned source

Keep the verified source archive and its extracted directory outside the project
being reviewed. Record its tag, resolved commit, and archive checksum before
installing. A tag names a release; a commit pins the source. `.release-version`
alone does not identify a commit: unreleased changes can retain the last version.
Autoreview's `--version` prints `autoreview source-sha256:` followed by the hash
of the executing helper. This identifies helper bytes, not a release or full skill.

Install only the desired skill from the retained source:

```sh
python3 /path/to/releases/agent-skills-current/scripts/install-skills \
  --target /path/to/shared-skills autoreview
```

The default symlink retains the source location. Resolving the installed link
identifies that directory, whose root contains `.release-version`. Keep the
directory available and unchanged while it is installed. Copy mode installs only
`skills/autoreview`, including its helper, PowerShell launcher, and references;
it omits the root `.release-version`. For copies, retain the source identity and
compare installed files with that source. The helper's `--version` can confirm its
content hash, but does not establish archive or release provenance. Neither mode
verifies a release signature for you.

Run the helper from the Git project being reviewed, not from the source archive:

```sh
cd /path/to/project
python3 /path/to/shared-skills/autoreview/scripts/autoreview --help
python3 /path/to/shared-skills/autoreview/scripts/autoreview \
  --mode local --engine codex --dry-run
```

On Windows, use `python` or the installed `scripts/autoreview.ps1` launcher.
Both PowerShell launchers search native Python applications without importing
PowerShell modules for missing candidates. They try `py -3`, `python3`, then
`python`, and require Python 3.10 or newer.
Existing native flags, executable selection, and trust checks still apply.
Help does not contact a model. Dry-run checks source preparation and local
executable capabilities; it does not prove model access or sandbox execution.

## Upgrade and rollback

Wait for active reviews to finish. Keep the previous verified source directory
for rollback. An existing installation is skipped unless `--force` is explicit;
`--dry-run` previews replacement without changing either source or target.

```sh
python3 /path/to/releases/agent-skills-next/scripts/install-skills \
  --target /path/to/shared-skills --mode copy --force --dry-run autoreview
python3 /path/to/releases/agent-skills-next/scripts/install-skills \
  --target /path/to/shared-skills --mode copy --force autoreview
```

`--force` replaces the entire selected skill entry. A symlink is unlinked without
deleting its source; a copied directory, including local customizations, is
removed. Keep authentication, configuration, and review reports outside that
entry. Unselected skills and files outside the selected entry are preserved.
Replacement is not transactional and creates no backup. If installation fails,
correct the failure and reinstall from a retained verified source.

Rollback uses the same explicit command with the previous source directory and
the desired `--mode`. Do not restore vendored helper copies into downstream repos.

## Qualification boundaries

The current shared workflow downloads the frozen target commit through GitHub's
tarball and zipball endpoints, then inventories and hashes the downloaded files.
Those checks establish archive identity, not installed runtime behavior. Candidate
archive installation checks are separate from publishing a signed release.

The historical v0.5.0 release has no attached release assets; the source-archive,
inventory, and checksum workflow was added afterward. Do not infer that those
assets shipped with v0.5.0 from the current workflow.

Installer tests cover copy/symlink replacement, rollback, outside-state retention,
and the real copied helper's help path from a directory with spaces and Unicode.
Symlink tests skip when Windows lacks permission to create links. This does not
qualify native Windows provider execution or model access.

The separate installed-source CI jobs check exact candidate tar/ZIP bytes against
Git, then copy-install Autoreview outside the checkout. Ubuntu jobs exercise
Python 3.10/3.11; Windows exercises the real copied PowerShell launcher. Each job
uses a fresh Python environment before and after installing pinned Pillow/tomli
proof dependencies. Tests decode a fixture PNG, parse fixture operator TOML, and
check the actionable refusals when a required optional dependency is absent.
Help, exact helper-byte `--version` identity, and a genuine unknown-option refusal
run from a directory with spaces and Unicode; source, installation, and external state must remain unchanged.
Windows profile and application-data directories are separate writable test
paths; PowerShell may populate its own module cache there.

These are no-model installation checks, not published-release certificates,
live auth/scanner/sandbox tests, or coverage of every architecture. ZIP executable
mode portability remains unqualified; Windows invokes the PowerShell launcher.
