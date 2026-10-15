# OpenClaw native review

Use an existing restricted reviewer for text reviews in OpenClaw Code Mode.
The canonical helper prepares each pass and validates the final result.

## Requirements

Follow the [engine-selection rules](../SKILL.md#engines). Before starting, confirm:

- Python 3.10+, Git, a POSIX filesystem and the canonical helper are available.
- Code Mode exposes `agents.run`, `exec` with structured `status`, `exitCode` and
  `aggregated` output plus bounded `env`, and `process` to monitor and stop the helper.
- The reviewer is admitted under the initiating identity and uses isolated context.
  Its enforced policy allows only result delivery: no repository, shell, file,
  network, publishing or delegation access. Do not change permissions, credentials
  or agent configuration to qualify it.
- The intended model/effort is available. CLI settings require an explicitly selected
  or approved native equivalent; never silently replace them with child defaults.
- The full request and result fit the bridge, collector and model limits.
  Supply required unchanged context through the helper; children cannot inherit
  a private parent worktree.

Unknown authentication does not qualify as absent authentication. Do not launch a
review to probe it. Images, Windows, native Codex dynamic-tool output and other
parent transports are unsupported. Report unavailable if requirements are unmet.

## Start

Run from the reviewed repository with `exec` and `yieldMs`; retain its process handle.
Do not use `background: true`. Set the overall timeout to cover all planned passes.
Use a private task directory outside the repository. Let the helper create `handoff`;
keep reports outside that directory.

```sh
python3 "$AUTOREVIEW" --mode branch --base "$BASE" \
  --engine openclaw --native-handoff "$PRIVATE/handoff" \
  --engine-timeout-seconds 900 --max-priority P2 \
  --json-output "$PRIVATE/report.json" --status-output "$PRIVATE/status.json"
```

Choose target, severity and timeout from the request; the values above are examples.
Use `--model <native-model-id>` and `--thinking <level>` for explicit choices;
otherwise the reviewer configuration applies. CLI tuning flags do not configure
native reviewers. The per-pass timeout includes transport. Native `--dry-run` is refused.

## Submit each pass

At `native pass ready: N/T`, run this cell once for that pass. Set its first four
variables and check the current tool declarations. Deliver the complete prompt and
actual terminal structured result; chat previews and saved-result references are
not substitutes.

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

Wait on the helper's process handle for the next pass or exit. Only its final status
and report determine the verdict. Do not launch passes early, resubmit them, reuse
an older child response after failure, or rerun to obtain fewer findings.

## Limits and cleanup

- Keep the cell's paging and environment-chunk transport. File tools, stdin, PTY,
  inherited descriptors and large log output are not supported substitutes.
- Responses must fit 2,000,000 UTF-8 bytes. Never truncate a report or drop inputs.
  Failed, malformed, mismatched or incomplete submissions cannot produce a clean result.
- The parent must deliver the full prompt and actual reviewer output. The pass
  identifiers do not attest reviewer identity or permissions.
- The helper removes `handoff` on normal exit or handled interruption. Late submissions
  cannot recreate it. Existing handoff directories cannot be resumed.
- On parent failure, stop both the helper and accepted child, then verify settlement.
  Stopping the helper alone does not stop the child. Timeout returns
  `reviewer_unavailable` without a validated report or route change.
- After an unhandled kill or interrupted submission, settle all readers/writers before
  removing the known handoff, named response spool and private task directory.
  Keep final reports separately; chat summaries and `results.save` are not durable storage.
