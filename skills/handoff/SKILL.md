---
name: handoff
description: "Clipboard-ready handoff prompt for another agent to investigate or continue a task."
---

# Handoff

Write a clipboard-ready prompt for another agent to investigate, discuss, or work
on a specific task.

Use when the user asks for `handoff <task>`, "write a handoff", "delegate this",
or wants a prompt for another agent.

## Workflow

1. Identify the task from the user text. If the user gives only a short label,
   infer from the current repo, recent discussion, branch name, linked issue/PR,
   docs, and obvious nearby context.
2. Gather enough context to write a useful handoff: repo/product identity,
   relevant issue/PR/branch names, likely modules, constraints, and known
   symptoms. Do not perform the receiving agent's full independent review or
   decide the final technical direction for them.
3. Write a standalone prompt preserving the requested mode, existing authority,
   accepted decisions, completed proof, remaining work, and completion condition.
4. Copy the full prompt to the clipboard.
5. Final reply: terse confirmation with the task title. Do not paste the full
   prompt unless the user asks.

## Handoff Prompt Rules

The prompt must:

- Preserve the user's requested mode: investigation, discussion, or execution.
- Carry existing authorization and its limits without granting new authority.
- Ask the receiving agent to verify live state and unresolved assumptions.
  Size independent review to the remaining uncertainty and repository requirements.
- Preserve accepted decisions and completed work unless new evidence invalidates
  them. An execution handoff must not reset the task to a proposal.
- Assume the agent starts in the repo, a parent directory, a workspace directory,
  or a home directory and can find the repo itself.
- Avoid filesystem paths. No absolute paths, home-directory paths, checkout
  names, or repo-relative file paths unless the user explicitly requests them.
- Use portable anchors instead: repo owner/name, product/module names, issue/PR
  URLs, branch names, package/plugin names, public symbols, command names, config
  keys, exact error text, docs titles, and search terms.
- Include enough context for the receiving agent to get the right repo, boundary,
  and desired outcome.
- Include constraints, non-goals, validation expectations, and the desired
  output shape.
- Tell the receiving agent to re-check live repo/GitHub/CI state where relevant.
- Tell the receiving agent not to push, merge, close issues/PRs, label, or post
  public comments unless the handoff explicitly asks for it.

## Prompt Template

Adapt this shape to the requested mode:

```text
<Investigate, discuss, or continue execution of>: <short task title>

Context:
- <portable repo/product context>
- <what triggered this task>
- <known current state, branch/issue/PR names or URLs if relevant>
- <important constraints and ownership boundaries>
- <existing authority, accepted decisions, completed work, and remaining gaps>

Resume:
- Find the right repository from the current directory, a parent directory, or the usual workspace.
- Read the local agent/repo instructions.
- Inspect the relevant code, docs, tests, recent commits, and linked issue/PR state.
- Verify unresolved assumptions without repeating completed work or reopening settled decisions absent new evidence.
- Call out stale assumptions, hidden risks, and anything that should stop the work.

Task:
- <next investigation or already-authorized implementation>
- <expected behavior or decision criteria>
- <non-goals>
- <completion condition and concrete stop conditions>

Validation:
- <focused tests/checks/live proof expected>
- <what evidence should be included>
- <what is explicitly not required>

Output:
- For investigation, report findings and recommendation.
- For execution, complete the authorized work and report the result or precise blocker.
- If you edit code, keep changes scoped and report exact proof run.
- Do not push, merge, close issues/PRs, label, or post public comments unless explicitly told.
```

## Clipboard

On macOS:

```sh
pbcopy < /tmp/handoff-prompt.txt
```

Use a temp file or pipe. Avoid inline shell quoting for prompts containing
backticks, `$`, quotes, or user text.

If `pbcopy` is unavailable, use the obvious platform clipboard tool (`wl-copy`,
`xclip`, `clip.exe`) or print the prompt and say clipboard copy was unavailable.

## Quality Bar

- No invented facts. Mark reviewed facts as such only after checking them.
- No path leakage. Rewrite any accidental path as a symbol, module, command,
  issue/PR URL, or search term.
- Enough context for a fresh agent to orient; no giant brain dump.
- A fresh agent can continue in the requested mode without inventing authority
  or losing existing authorization.
