# OpenClaw review execution

The OpenClaw engine runs a restricted `openclaw agent exec` reviewer. The canonical
helper owns Git capture, frozen input checks, pass planning and complete report
validation. There are no reviewer profiles or child-agent collectors.

## Choose the execution route

Honor the [engine-selection rules](../SKILL.md#engines), including explicit engine,
model and effort choices. Select the route before launch; never switch routes after
a failed review. Text review requires Python 3.10+, Git and POSIX private-directory
permissions. Image review remains Codex-only.

On an authenticated host, run the canonical helper directly:

```sh
python3 "$AUTOREVIEW" --mode branch --base "$BASE" --engine openclaw
```

Supply only the target and explicitly requested overrides. Canonical options and
`AUTOREVIEW_*` environment settings retain their normal precedence. With no
review model or effort override, native OpenClaw selects them from its normal
configuration. `--model provider/model` and `--thinking` remain available.
The trusted executable must support `agent exec --message-file --config-override
--cwd --model --thinking --json` and `config get <section> --json`.
`--openclaw-bin` or `OPENCLAW_BIN` can select an external trusted executable.
`--dry-run` checks preparation and CLI support without contacting a provider.

Direct execution inherits native configuration and authentication, including
stored login state. Optional `--openclaw-config /absolute/external/openclaw.json`
(or `AUTOREVIEW_OPENCLAW_CONFIG`) selects an operator-owned alternative file outside
the reviewed repository. Native OpenClaw loads and validates it; the helper never
reconstructs a provider/model catalog or copies credentials. Ordinary environment
inputs, including arbitrary native configuration references such as
`${CUSTOM_PROVIDER_KEY}`, remain available in the trusted host process. They do
not enter the sandbox or settings exchange. Interpreter/loader startup hooks,
inherited Git overrides and package-manager startup variables are excluded;
PATH and known configuration, authentication and certificate paths keep their
existing repository-local rejection. Environment values are never diagnostics.

The helper reads the `agents` and `tools` sections once through the native
configuration command and creates a sparse run-only override: deny tools and tool
discovery, clear inherited tool grants in global, agent, provider and sandbox
policies so intentional no-tools runs pass native validation, disable Code Mode, suppress skills and
workspace context for defaults and existing agents, and clear configured object
model fallbacks, including an empty chain when no primary is configured. String
model selections stay intact. All other configuration,
including the selected authentication owner, remains native-owned. The override
also clears remembered native-runtime consent for this run. The
configured runtime must enforce the review restrictions; unsupported runtimes
remain unavailable. Saved configuration and consent are unchanged. The complete
prompt goes on stdin; execution uses a private empty workspace and native temporary
state. Optional `--engine-timeout-seconds` bounds each configuration-read or reviewer
process; omitted limits retain native behavior. Owned processes and temporary
files are removed on normal exit or handled interruption. Forced termination may
require task-owned scratch cleanup. No failed review triggers another route or model.

Inside an OpenClaw sandbox, use the bound `autoreview` tool with the target and only
explicitly requested review overrides. It runs canonical capture and validation
in the current sandbox and the reviewer on the host. The integration applies current
caller restrictions before execution. If the configured review model is prohibited,
it selects the caller's existing permitted default and records that admitted model
for canonical terminal validation. Do not launch the host CLI from guest shell,
create a reviewer profile, copy host credentials, or substitute an unrestricted
agent. If the tool or qualified helper is unavailable, report unavailable. An explicit
different engine continues to use that engine's eligible route.

## Bound execution contract

This section is for the trusted OpenClaw integration. Ordinary sandbox callers use
`autoreview`; they do not manually orchestrate a reviewer. The integration owns
current caller authority, selected-model admission, executable/configuration
provenance, process cancellation and complete bounded transport. Request identifiers
bind response ownership; they do not grant authority or attest reviewer isolation.

Start the installed canonical helper inside the current invocation's sandbox:

```sh
python3 "$AUTOREVIEW" --mode branch --base "$BASE" \
  --engine openclaw --native-handoff "$PRIVATE/handoff" \
  --json-output "$PRIVATE/report.json" \
  --status-output "$PRIVATE/status.json"
```

The integration derives `$PRIVATE` from its sandbox capability and creates its
private parent outside the repository. The helper creates `handoff` exclusively;
reports stay outside it. Keep the waiting process owned and yielding. Qualify the
installed helper with its source identity (`--version`) before execution. Require
the first request's `admitted_model: true` capability before launching a reviewer;
an older request without it is unavailable and its waiting helper must be stopped.

The existing request files carry canonical-resolved model preference, effort,
pass plan and optional timeout. These are ordinary review settings, never host
permission, executable, path, configuration or credential authority. The host owns
its execution restrictions and current caller authority; no host configuration
object crosses from the sandbox.

Keep native config/auth loading; do not project catalogs, credentials, pricing or
plugin metadata. Bind the native run to the actual caller's owner and permitted
model before execution, deny tools and discovery, suppress workspace context and
skills, and clear model fallbacks and remembered native-runtime consent for that
run. Bind the first request's invocation and plan, and check subsequent requests
consistently. An omitted helper timeout adds no wrapper deadline; caller
cancellation and native process lifetime still apply.

Before creating the exchange, the helper checks every encoded request against the
4,000,000-byte transport limit, including JSON escaping and envelope overhead.
An explicit prompt budget does not raise this transport limit; reduce the prompt
budget if a request is too large. At `native pass ready: N/T`, read the complete
`N.request.json` (at most 4,000,000 bytes). Its fields are:

| Field | Meaning |
| --- | --- |
| `protocol` | `autoreview-exec-v1` |
| `admitted_model` | `true`: this helper validates the additive response model |
| `run_id`, `pass`, `passes` | Invocation identity and sequential pass/count |
| `prompt`, `prompt_bytes`, `prompt_sha256` | Complete UTF-8 prompt, length and digest |
| `model`, `thinking` | Canonical-resolved selection, or null for native defaults |
| `engine_timeout_seconds` | Optional canonical deadline per pass, or null; no integration default |
| `max_result_bytes` | 2,000,000 UTF-8 bytes for the complete encoded response |

The prompt already contains the canonical report schema. Send its bytes intact
through private stdin to fixed restricted `openclaw agent exec --json`; the host
owns its empty cwd, configuration, credentials, deadline and process lifetime.
Never accept host executable/configuration/path authority from the request.

After the process exits, create one response with these fields:

```json
{
  "run_id": "request run_id",
  "pass": 1,
  "prompt_sha256": "request prompt_sha256",
  "status": "done",
  "model": "admitted-provider/admitted-model",
  "output": "complete raw agent-exec JSON stdout"
}
```

Use `done` only for exit 0. Nonzero exit, cancellation, timeout or incomplete output
uses `failed` with `output: null`; never salvage an earlier answer. The host does
not parse the report. The additive `model` field names the model admitted before
execution; it must match the terminal provider/model. Legacy v1 responses may omit
it and retain the original requested-model validation. Failed responses may use
`model: null`. The helper requires one successful terminal envelope and a nonempty
`final`, reports the observed effective model, then applies its existing report
parser and completion/scope validation. CLI success alone is
not a clean review. Oversized output fails without truncating or dropping findings.

Write the bounded response to the sibling spool named
`handoff.RUN_ID.N.response.json`, then commit it with the same installed helper:

```sh
python3 "$AUTOREVIEW" --native-submit "$PRIVATE/handoff" "$RESPONSE_SPOOL"
```

Submission exclusively claims the pass, atomically publishes the complete result
and ready marker, and removes the named spool. It does not perform Git work or
publish a verdict. It cannot recreate a retired exchange. Wait for the next request
or helper exit; never start passes early, resubmit, or resume an old exchange.

Only the helper's final report/status determines the outcome. Preserve its distinction
between findings, incomplete assessment, unavailable reviewer and scoped clean.
The status receipt's optional `effective_models` lists validated terminal model
identities across passes, including an admitted selection that differs from the
configured preference. Return this metadata to the caller rather than parsing
model output or relying on progress logs.
Source changes prevent publication. On parent failure, stop and join both owned
processes before cleanup. The helper removes its exchange on normal exit and handled
interruption; after an unhandled kill, settle readers/writers before removing only
the known private directory and named spool. No failed pass triggers route fallback.
