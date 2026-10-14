# OpenClaw native review

Use this consumer only in an eligible OpenClaw Code Mode session. The same helper
captures, partitions and validates the review; an existing isolated collector
replaces the external CLI execution. No direct model API or credentials are added.

## Select before execution

Honor explicit engine/provider choices and `AUTOREVIEW_ENGINE`. Preserve explicit
model and reasoning choices; never substitute a configured child default for them.
A model or provider setting intended for a CLI is not automatically an OpenClaw model
id. Use the selected CLI unless the caller has selected or approved its native
counterpart. Keep a working configured CLI as the ordinary default. With no explicit
route, a missing CLI or known absent authentication permits native selection before
execution. Unknown authentication is not evidence of absence. Do not run a review
merely to test authentication. Never switch after launch or work around an isolation
failure. The standalone helper's default remains Codex.

Before selecting native, establish all of these from the current session:

- The canonical helper package, Python 3.10+, Git and a POSIX filesystem are available.
- OpenClaw Code Mode exposes `agents.run`, shell `exec` with structured `aggregated`
  output and bounded `env` values, and `process` to observe and stop the helper.
- The selected existing reviewer agent is admitted under the initiating identity.
  Its effective policy denies repository access, shell/file/network operations,
  publishing and further delegation, retaining only the collector result transport.
  An instruction to be read-only is not enforcement. There is no per-spawn read-only
  flag. Do not add permissions, credentials or agent configuration to make a run pass.
- The child uses isolated context and the intended model/effort. `agents.run` starts
  a non-thread collector with isolated context. It cannot inherit a private parent
  worktree; supply required unchanged context using the helper's existing options.
- The complete request and result fit the active Code Mode bridge, collector and
  model context budgets. A tool preview or chat/history rendering is not a full value.

Native currently supports text reviews in this Code Mode path. Image-bearing changes
are refused by the helper. Native Codex dynamic-tool output, other harness transports,
Windows handoff custody and image attachments are not qualified by this consumer.
Do not drop inputs or reduce finding counts to fit a transport. Use an already
supported explicitly selected route, or report the limitation without a clean verdict.

## Start the helper

Run from the reviewed repository using shell `exec` with `yieldMs` to obtain an
ordinary request-owned process handle; do not use independent `background: true`.
Choose the command's overall timeout to cover the planned review budget. Use a
fresh path under a private task-owned directory outside the repository; do not create
the `handoff` directory yourself. Report destinations must stay outside it.

```sh
python3 "$AUTOREVIEW" --mode branch --base "$BASE" \
  --engine openclaw --native-handoff "$PRIVATE/handoff" \
  --engine-timeout-seconds 900 --max-priority P2 \
  --json-output "$PRIVATE/report.json" --status-output "$PRIVATE/status.json"
```

Choose target and severity from the request; P2 above is an example, not a new default.
Pass `--model <OpenClaw model id>` and `--thinking <level>` for explicit native choices.
Omitted values use the qualified reviewer agent's configuration. CLI tuning options
cannot configure a native child. The per-pass timeout includes transport and collection;
select it before launch, observe the helper's existing process handle, and do not detach
an unowned job. `--dry-run` cannot qualify a native child and is refused.

## Deliver one prepared pass

When the helper prints `native pass ready: N/T`, run the following complete cell in
OpenClaw Code Mode, setting `directory`, `helper`, `passNumber` and `reviewerAgentId`.
Read the current tool declarations first. Shell `exec` must return structured
`status`, `exitCode` and `aggregated`. The cell reads every page, sends the full prepared
assignment, waits for the terminal structured value and writes it before the reply
ends. It never emits a full prompt/report through model-visible output.

```javascript
const directory = "/absolute/private/task/handoff";
const helper = "/absolute/canonical/autoreview/scripts/autoreview";
const passNumber = 1;
const reviewerAgentId = "existing-restricted-reviewer";
const byteLength = s => encodeURIComponent(s).replace(/%[0-9A-F]{2}|./g, "x").length;
const quote = s => "'" + s.replace(/'/g, "'\\''") + "'";
async function python(code, args, env) {
  const result = await exec({command: "python3 -c " + quote(code) + args.map(x => " " + quote(String(x))).join(""),
    ...(env ? {env} : {}), awaitResults: true});
  if (result.status !== "completed" || result.exitCode !== 0)
    throw new Error("Native transport command failed; inspect the owned helper");
  return JSON.parse(result.aggregated);
}
const readPage = `import os,sys,json,stat
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
offset=int(sys.argv[2])
with os.fdopen(fd,"rb") as f:
 info=os.fstat(f.fileno()); total=info.st_size
 assert stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1
 assert 0<total<=4000000 and 0<=offset<total
 f.seek(offset); data=f.read(8192)
print(json.dumps({"offset":offset,"next":offset+len(data),"total":total,"content":data.decode("ascii")}))`;
async function readComplete(path) {
  let offset = 0, total, content = "";
  do {
    const page = await python(readPage, [path, offset]);
    if (!page || page.offset !== offset || !Number.isSafeInteger(page.total) ||
        page.total <= 0 || page.total > 4_000_000 || typeof page.content !== "string" ||
        page.next !== offset + page.content.length || page.next !== Math.min(offset + 8192, page.total) ||
        (total !== undefined && page.total !== total))
      throw new Error("Invalid or incomplete request page");
    total = page.total;
    content += page.content;
    offset = page.next;
  } while (offset < total);
  return content;
}
const appendChunk = `import os,sys,stat,json
from pathlib import Path
p=Path(sys.argv[1]); offset=int(sys.argv[2]); parent=p.parent.stat()
assert parent.st_uid==os.getuid() and not stat.S_IMODE(parent.st_mode)&0o077
data=os.environ["AUTOREVIEW_NATIVE_CHUNK"].encode("utf-8")
assert 0<len(data)<=32768 and 0<=offset and offset+len(data)<=2000000
fd=os.open(p,os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_CREAT|os.O_EXCL if offset==0 else 0),0o600)
with os.fdopen(fd,"ab") as f:
 info=os.fstat(f.fileno())
 assert stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1 and info.st_size==offset
 f.write(data)
print(json.dumps({"next":offset+len(data)}))`;
const request = JSON.parse(await readComplete(`${directory}/${passNumber}.request.json`));
if (request.protocol !== "autoreview-native-v1" || request.pass !== passNumber ||
    typeof request.prompt !== "string" || byteLength(request.prompt) !== request.prompt_bytes ||
    !/^[a-f0-9]{32}$/.test(request.run_id) || !/^[a-f0-9]{64}$/.test(request.prompt_sha256))
  throw new Error("Invalid or incomplete prepared pass");
let report = null, status = "failed", failure;
try {
  // The wrapper keeps the prepared bytes intact even when the collector trims its task.
  report = await agents.run("<autoreview-pass>\n" + request.prompt + "\n</autoreview-pass>", {
    agentId: reviewerAgentId, label: `autoreview-${passNumber}`, schema: request.output_schema,
    ...(request.model === null ? {} : { model: request.model }),
    ...(request.thinking === null ? {} : { thinking: request.thinking })
  });
  if (!report || typeof report !== "object" || Array.isArray(report))
    throw new Error("Collector returned no structured report");
  status = "done";
} catch (error) { failure = error; }
let response = JSON.stringify({ run_id: request.run_id, pass: passNumber,
  prompt_sha256: request.prompt_sha256, status, report });
if (byteLength(response) > request.max_result_bytes) {
  failure = new Error("Complete report exceeds native transport budget");
  response = JSON.stringify({ run_id: request.run_id, pass: passNumber,
    prompt_sha256: request.prompt_sha256, status: "failed", report: null });
}
// Use existing private exec.env transport; report content never enters command argv.
const spool = `${directory}.${request.run_id}.${passNumber}.response.json`;
let bytes = 0;
for (let offset = 0; offset < response.length;) {
  let end = Math.min(offset + 8192, response.length);
  const last = response.charCodeAt(end - 1);
  if (last >= 0xD800 && last <= 0xDBFF) end--; // Keep UTF-16 surrogate pairs intact.
  const chunk = response.slice(offset, end);
  const receipt = await python(appendChunk, [spool, bytes], {AUTOREVIEW_NATIVE_CHUNK: chunk});
  bytes += byteLength(chunk);
  if (receipt.next !== bytes) throw new Error("Incomplete response transfer");
  offset = end;
}
const submitted = await exec({ command: `python3 ${quote(helper)} --native-submit ${quote(directory)} ${quote(spool)}`,
  awaitResults: true });
if (submitted.status !== "completed" || submitted.exitCode !== 0)
  throw new Error("Native response was not committed; inspect the helper and settle the owned child");
if (failure) throw failure;
return { pass: passNumber, delivered: true, passes: request.passes };
```

Use the helper's process handle to wait for the next prepared pass or terminal exit.
Repeat the cell for each newly announced pass exactly once. A successful delivery is
not a review verdict. The helper may reject the schema, scope, attribution or source,
and only its final status/report determines the outcome. Do not launch later passes
speculatively, manufacture missing responses, recover an earlier successful child
message after terminal failure, or retry for a cleaner finding set.

## Lifecycle and limits

Container-only scratch is deliberately accessed through the existing shell tool,
not through host-backed file tools or a new bind mount. Sandboxed exec has closed
stdin and disables PTY, so this consumer does not use stdin, terminal input or
inherited descriptors. Request JSON is ASCII-encoded by the helper and read in
8,192-byte JSON-framed pages with exact offsets and lengths. Never substitute a
large `cat` or a truncated log for those pages. Responses use bounded, single-line
environment chunks through OpenClaw's existing private container env-file transport;
JSON serialization escapes newlines and NULs. This is invocation data, not saved
configuration. A lower aggregate limit, denied environment override or failed
chunk aborts the consumer; it never silently narrows a pass or a report.

The helper owns `handoff` and removes it on normal exit or handled interruption.
Its in-memory capture remains authoritative until all passes and the final source
check finish. Requests are atomic, sequential and identified by a fresh run id,
pass number and prompt SHA-256. `--native-submit HANDOFF RESPONSE` opens the existing
exchange and commits through its directory descriptor, under the same short file
lock used by cleanup. It never creates an exchange. A collector that finishes after
timeout cannot recreate a retired handoff; submission refuses it and removes its
identity-checked spool. Each pass can be submitted only once. This command transports
the result; the waiting original invocation still owns all review validation.
Responses are limited to 2,000,000 UTF-8 bytes;
oversized, malformed, mismatched, missing and uncommitted responses are never clean.
The request/result handshake binds transport to a prepared pass; it is not a signed
reviewer or permission attestation. The qualified parent is trusted to deliver the
complete prompt and the collector's actual terminal result.

An existing directory is refused, so a stale interrupted run cannot be resumed or
mistaken for a new review. On parent failure, stop the owned helper and any accepted
child through their existing process/collector facilities, then verify both settled.
Stopping the helper alone does not cancel an OpenClaw child. A timeout yields
`reviewer_unavailable`, no validated report, and no automatic route change. After an
uncatchable kill, remove only the known task-owned handoff after settling its readers.
If the parent stops between staging and submission, also remove its named response
spool after the child and all owned writers settle. The private task parent remains
the parent's cleanup responsibility; do not replace it with a shared temporary root.
Preserve final reports separately; never use chat summaries or reply-scoped
`results.save` references as durable result storage.
