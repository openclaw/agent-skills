# Engine options

Read for model/effort overrides, provider projection, optional engines.

These options configure helper engines, not Copilot model access. When Codex CLI
is unavailable, the skill permits a separate
[Copilot subagent review](../SKILL.md#copilot-subagent-review), preferably with an
accessible Codex model or otherwise a comparable model. Select it before launch;
it is not `--engine copilot`, does not inherit Codex CLI flags/defaults, and
produces no helper-validated machine status or helper isolation guarantees.

- Defaults + engine-selection policy: [SKILL.md](../SKILL.md#engines).
- Explicit `gpt-6.1-sol`: same access-only `gpt-6-sol` retry.
  Explicit `gpt-6-sol`: access-only `gpt-6-luna` retry.
- Other explicit models, including Luna/Astra: no model fallback.
- Explicit `gpt-5.6-sol`: access-only `gpt-5.6-terra` retry.
- GPT-6.1 Sol rejects `none`/`minimal` effort before review preparation;
  GPT-6 Sol/Luna reject `minimal`. Effort-only override keeps default model.
- Honor explicit user engine/model choices. No automatic fallback between engines.

- Override defaults: `--engine`, `--model`, `--thinking`.
- Codex tier: Ultrafast when active model catalog lists it; otherwise Codex silently
  sends standard tier. Raw `--codex-config service_tier=...` keeps its value.
- `--codex-speed fast`: priority service. `--codex-speed default`: standard tier.
- Only Claude accepts `--fallback-model`.
- Per-engine environment overrides: `AUTOREVIEW_<ENGINE>_*`.

Account cannot access Sol/Luna: pin available model.
Require GPT-6 Astra without model fallback: select explicitly:

```bash
"$AUTOREVIEW" --mode local --model gpt-6-astra --thinking high
```

- GPT-6.1 Sol + GPT-6 Astra: `low`, `medium`, `high`, `xhigh`, `max`;
  neither supports `none`/`minimal`.
- GPT-6 Sol + Luna: additionally support `none`, never `minimal`.
- AutoReview default: `medium`; no fallback from explicit Luna/Astra selection.
- Codex `ultra`: automatic delegation; outside helper's supported effort levels.
  Deepest supported review: `max`.
- EU data residency: `--codex-speed default`; GPT-6 fast mode unavailable there.

See [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol), and
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) model docs
and [Codex reasoning modes](https://learn.chatgpt.com/docs/models#know-when-to-use-max-or-ultra).

Default: ChatGPT subscription; preserve only user authentication settings.
Live authentication failure → stop attempt fast; retry pass once on operator's
validated configured named command-auth route, including context + catalogue.
Definite credential failure → immediate stop; generic auth failure → stop after
3 lines within 60s. Single 401: allow Codex's reload/refresh recovery.
Explicit provider / non-auth failure / no valid configured route: no auth fallback.
Profile settings remain ignored. Force configured route before subscription attempt:

```bash
"$AUTOREVIEW" --mode local --codex-config 'model_provider="review_api"'
```

- Selector must match `model_provider` in operator's external `CODEX_HOME/config.toml`.
  Accepts one bare or simply quoted identifier; overrides cannot supply provider
  definitions or other capabilities.
- Projection requires Python 3.11 or `tomli`; default auth-only operation keeps
  existing fallback parser.

- Selected route must use `https://api.openai.com/v1` + command authentication
  with absolute external executable. Fixed arguments belong in executable's wrapper;
  omitted/empty `auth.args` accepted.
- Omitted `wire_api`/`requires_openai_auth`: keep Codex `responses`/`false` defaults,
  respectively. Optional auth timing/context settings: native defaults/semantics.

- POSIX: private launcher restores validated caller `HOME` only for selected
  authentication executable. Engine/reviewer tools keep isolated environment/filesystem access.
- Caller `HOME` must be available absolute directory; no repository-owned path
  or symlink provenance. Windows keeps native executable route.
- Command-auth runs: suppress raw provider diagnostics; report fixed failure
  categories; retain compact progress, usage, assistant report streaming.
- Command-auth runs use a separate empty file credential store, including on
  subscription fallback; they never inherit or refresh subscription credentials.
- Empty final report: fail without exposing captured stdout.

- Catalogue + authentication working-directory paths: resolve relative to operator
  config directory; must stay outside reviewed repository.
- Supplied catalogue: copy byte-for-byte into private client runtime;
  retries use same route/catalogue snapshot.
- Dry runs: same ownership/route shape checks; no authentication execution.
- Codex owns catalogue validation, model access, context clamping.
- Projection selected: other custom provider forms/split context overrides unsupported.

| Optional engine | Prerequisites                                                                                         |
| --------------- | ----------------------------------------------------------------------------------------------------- |
| Claude          | CLI 2.1.169+; safe mode with web-only tools                                                           |
| Amp             | `AMP_API_KEY` for a plugin-free account; local POSIX execution, no custom endpoint or cloud/orb agent |
| Pi              | CLI 0.79.0+; configured model; no tools or project resources                                          |

- `--engine kimi`: recognized, refused for reviews + `--dry-run` before any Kimi
  process, configuration read, or authentication setup.
- Supported Kimi Code prompt mode accepts review content only as command-line
  argument; helper has no supported private prompt input channel.
- Previous Kimi execution path intentionally retired; never expose bundle in
  process arguments. Existing `--kimi-bin` arguments accepted for same clear refusal.
- Never silently select another engine. Custom agent file ≠ equivalent helper
  replacement: changes input into templated system prompt. The documented Copilot
  subagent route is a separate assessment with explicitly reported limitations.

## OpenClaw

`--engine openclaw` uses restricted `openclaw agent exec`, directly on a trusted
host or through the bound sandbox `autoreview` tool. Omitted model and effort use
normal OpenClaw selection; explicit helper options and environment settings retain
their normal precedence. Direct execution inherits native configuration and
authentication; optional `--openclaw-config` selects an external operator config.
The helper owns review restrictions, the empty workspace, private prompt input,
optional timeout and cleanup. Bound integrations apply current caller permissions
before execution and return the admitted model for terminal validation.
There is no child reviewer profile, model fallback or output-schema CLI dependency.
See [execution and integration requirements](openclaw.md) before launch.
