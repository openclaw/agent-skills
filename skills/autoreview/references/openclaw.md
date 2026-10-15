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
python3 "$AUTOREVIEW" --mode branch --base "$BASE" \
  --engine openclaw --model "$MODEL" --thinking "$THINKING" \
  --openclaw-config "$MODEL_CONFIG" \
  --engine-timeout-seconds 900 --max-priority P2
```

Use the model and effort the caller selected. Direct execution requires an explicit `provider/model`. The trusted `openclaw` executable
must support `agent exec --message-file --config --cwd --model --thinking --json`.
`--openclaw-bin` or `OPENCLAW_BIN` can select an external trusted executable.
`--dry-run` checks preparation and CLI support without contacting a provider.

The helper sends the full prompt on stdin and runs in a private empty workspace.
It generates a configuration denying all tools, disabling Code Mode, skills,
workspace context injection and model fallback, and pins the OpenClaw runtime.
Temporary state and processes are owned by this invocation and removed on exit or
handled interruption. The process timeout is a total per-pass deadline, including
startup and transport. Forced termination may require task-owned scratch cleanup.

Direct execution requires `--openclaw-config /absolute/external/models.json`
(or `AUTOREVIEW_OPENCLAW_CONFIG`) with an explicit catalog entry for the selected
provider/model, including its API, endpoint and model metadata. Only that provider
and model are projected; other catalogs are excluded. Provider credentials come
from the supported provider environment variables or that selected configuration.
`AUTOREVIEW_PROVIDER_ENV_ALLOW` may name additional credential variables
for a custom provider. Ambient OpenClaw state, Gateway tokens, project configuration,
plugins and shell environment import are not inherited. The configuration must be
an operator-owned JSON file outside the reviewed repository; an existing operator
config with the selected catalog is sufficient, without a separate reviewer
profile. Only known inference fields are copied; provider local-service commands
and provider/model runtime selectors are excluded. A local endpoint must already
be running. Other configuration fields cannot change reviewer permissions. Environment secret references must name forwarded variables;
file/command secret resolvers and ambient login profiles are not projected. No
configuration or credentials are copied into the reviewed repository.

Inside an OpenClaw sandbox, use the bound `autoreview` tool with the selected
`model`, `thinking`, target and `maxPriority`. It runs canonical capture and
validation in the current sandbox and only the restricted reviewer on the host.
Do not launch the host CLI from guest shell, create a reviewer profile, copy host
credentials, or substitute an unrestricted agent. If this tool or the qualified
canonical helper is unavailable, report unavailable. An explicit different engine
continues to use that engine's eligible route.

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
  --engine-timeout-seconds 900 --model "$MODEL" --thinking "$THINKING" \
  --max-priority P2 --json-output "$PRIVATE/report.json" \
  --status-output "$PRIVATE/status.json"
```

The integration derives `$PRIVATE` from its sandbox capability and creates its
private parent outside the repository. The helper creates `handoff` exclusively;
reports stay outside it. Keep the waiting process owned and yielding. Qualify the
installed helper with its source identity (`--version`) before execution. A helper
with the old structured-child protocol is not compatible.

At `native pass ready: N/T`, read the complete `N.request.json` (at most 4,000,000
bytes). Its fields are:

| Field | Meaning |
| --- | --- |
| `protocol` | `autoreview-exec-v1` |
| `run_id`, `pass`, `passes` | Invocation identity and sequential pass/count |
| `prompt`, `prompt_bytes`, `prompt_sha256` | Complete UTF-8 prompt, length and digest |
| `model`, `thinking` | Explicit selection, or null when the trusted caller supplies it |
| `max_result_bytes` | 2,000,000 UTF-8 bytes for the complete encoded response |

The prompt already contains the canonical report schema. Send its bytes intact
through private stdin to fixed restricted `openclaw agent exec --json`; the host
owns its empty cwd, configuration, credentials, deadline and process lifetime.
Never accept host executable/configuration/path authority from the request.

After the process exits, create one response with exactly these fields:

```json
{
  "run_id": "request run_id",
  "pass": 1,
  "prompt_sha256": "request prompt_sha256",
  "status": "done",
  "output": "complete raw agent-exec JSON stdout"
}
```

Use `done` only for exit 0. Nonzero exit, cancellation, timeout or incomplete output
uses `failed` with `output: null`; never salvage an earlier answer. The host does
not parse the report. The helper requires one successful terminal envelope, a
nonempty `final`, and the explicitly selected model when supplied, then applies
its existing report parser and completion/scope validation. CLI success alone is
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
Source changes prevent publication. On parent failure, stop and join both owned
processes before cleanup. The helper removes its exchange on normal exit and handled
interruption; after an unhandled kill, settle readers/writers before removing only
the known private directory and named spool. No failed pass triggers route fallback.
