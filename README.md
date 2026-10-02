# OpenClaw Agent Skills

![Agent Skills banner](docs/assets/readme-banner.jpg)

Shared skills for coding agents that work on OpenClaw projects.

This repo is the public canonical source for common workflows such as review
closeout and remote validation. The goal is simple: write a workflow once,
reuse it everywhere, and avoid hand-copying long `SKILL.md` files across every
repo. See [VISION.md](VISION.md) for catalog boundaries and admission principles.

## Included Skills

- `agent-transcript`: local-only, redacted PR/issue transcript provenance.
- `autoreview`: structured closeout/code-review workflow plus helper script.
- `behavior-validator`: source-blind validation of user-visible behavior against
  a contract.
- [`beam`](skills/beam/README.md): self-contained, authenticated, redacted
  publication of local coding sessions to a read-only OpenClaw catalog.
- `crabbox`: Crabbox/Testbox remote validation workflow for broad or CI-parity
  proof.
- `handoff`: path-free prompt handoff workflow for delegating a task to another
  agent.
- `readme-standard`: house README structure, badge row, tone, and verification
  gates for steipete/openclaw repos.
- `session-viewer`: local searchable HTML viewer for agent session JSONL.

Repo-specific product skills should stay in the repo they describe. For example,
an `acpx` usage skill belongs in `openclaw/acpx`; a general review helper belongs
here.

## Quick Start

Clone the repo:

```sh
git clone https://github.com/openclaw/agent-skills.git
cd agent-skills
```

List available skills:

```sh
scripts/install-skills --list
```

Preview an install without changing files:

```sh
scripts/install-skills --dry-run
```

Install all skills into the default agent skill directory:

```sh
scripts/install-skills
```

Install only selected skills:

```sh
scripts/install-skills autoreview crabbox
```

Install somewhere else:

```sh
scripts/install-skills --target ~/.codex/skills autoreview
```

Use copies instead of symlinks:

```sh
scripts/install-skills --mode copy --target ~/.agents/skills
```

Replace an existing installed skill:

```sh
scripts/install-skills --force autoreview
```

Install targets must not contain or sit inside the source skills. The installer
checks every selected destination before changing files, including with `--force`
or `--dry-run`; installing directly over the same source directory is skipped.

Symlinks are best for local development because changes in this checkout are
immediately visible. Copies are better for portable or locked-down setups.
Node-based skills declare their module format locally, so copied helpers also
run inside CommonJS projects without installing dependencies.

## Codex And Claude

For Codex, symlink this repo into `~/.codex/skills`:

```sh
mkdir -p ~/.codex/skills
ln -sfn "$(pwd)/skills" ~/.codex/skills/agent-skills
```

For Claude Code, symlink this repo into `~/.claude/skills`:

```sh
mkdir -p ~/.claude
ln -sfn "$(pwd)/skills" ~/.claude/skills
```

If `~/.claude/skills` already points at another shared skills folder, add
symlinks inside that folder instead:

```sh
ln -sfn "$(pwd)/skills/autoreview" /path/to/shared-skills/autoreview
ln -sfn "$(pwd)/skills/crabbox" /path/to/shared-skills/crabbox
```

Recommended one-liner for repo `AGENTS.md` files:

```text
Shared agent workflows: install or symlink https://github.com/openclaw/agent-skills for `autoreview`, `crabbox`, and other common skills. Autoreview uses one shared installation; repository entrypoints refer to it.
```

## Shared Autoreview

Install autoreview once with `python3 scripts/install-skills autoreview`. The
default `~/.agents/skills/autoreview` symlink serves every repository. On Windows,
use `python`; add `--mode copy` if symlinks are unavailable.

Repositories keep only a `.agents/skills/autoreview/SKILL.md` entrypoint copied
from [the repository template](skills/autoreview/references/repository-entrypoint.md).
Agents read the full installed skill and run its helper from the repository being
reviewed. Repo-specific review thresholds and contribution rules stay in that
repository. Helpers, fixtures, and their tests stay here.

Contribute shared improvements here first. After active reviews finish, update
this checkout once to update every symlinked consumer. Copy-mode installations
need `python3 scripts/install-skills --mode copy --force autoreview` after the
source update. Review runs do not download or update code automatically.

## Zero-Setup Repos

Some important repos should work for contributors who only cloned that repo and
never installed shared skills. Those repos may vendor a generated snapshot under
`.agents/skills/<name>`.

That snapshot is a distribution artifact, not the source of truth:

- edit canonical skills here first
- sync snapshots downstream after review
- keep downstream copies small in number
- add provenance and drift checks when a repo vendors a snapshot

This option does not apply to `autoreview`, which uses the shared installation
above. Vendor other operational skills only when the repo needs them available
without setup.

## Repository Layout

```text
skills/
  agent-transcript/
    SKILL.md
    scripts/
  autoreview/
    SKILL.md
    scripts/
  behavior-validator/
    SKILL.md
    references/
  beam/
    README.md
    SKILL.md
    references/
    scripts/
  crabbox/
    SKILL.md
  handoff/
    SKILL.md
  session-viewer/
    SKILL.md
    scripts/
scripts/
  install-skills
  validate-skills
```

Each skill lives in `skills/<name>/` and must contain `SKILL.md`. Helper scripts
belong inside that skill's `scripts/` directory.

## Validate

Development checks use Python 3.14 and Node.js 26, matching CI. Install the
development dependencies once, then run the shared check command:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts
python scripts/check-skills
```

The check command runs frontmatter validation, syntax checks, all Python and
Node tests, and `npm run typecheck` for the session viewer. The Node packages
are development-only; installed skills do not need `npm install`. The separate
macOS CI job installs a pinned Codex CLI to exercise native sandbox access
controls without a reviewer account or provider request.

For a quick frontmatter-only check, run `scripts/validate-skills`. It checks
every `skills/*/SKILL.md` for YAML frontmatter plus required `name` and
`description` strings. Frontmatter must be a mapping enclosed by standalone
`---` lines; trailing spaces or tabs are allowed on the closing line.

Session exports can contain sensitive conversation data. Treat `session-viewer`
HTML as local/private output unless it has been separately redacted and reviewed.

## Editing Rules

- Keep descriptions short and useful for routing.
- Keep skill bodies operational rather than essay-like.
- Do not include secrets, private hostnames, private account IDs, or private
  URLs.
- Prefer helper scripts for repeatable command logic.
- Do not update vendored downstream snapshots by hand. Update this repo, then
  sync.

See [docs/RELEASING.md](docs/RELEASING.md) for the source-release process.

## License

MIT.
