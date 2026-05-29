---
name: handoff
description: "Write a path-free, clipboard-ready handoff prompt that lets another agent investigate, discuss, or pick up a specific task."
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
3. Write a standalone prompt for a fresh agent.
4. Copy the full prompt to the clipboard.
5. Final reply: terse confirmation with the task title. Do not paste the full
   prompt unless the user asks.

## Handoff Prompt Rules

The prompt must:

- Start a discussion, not a command-only work order.
- Ask the receiving agent to do an extensive independent review before changing
  anything.
- Make clear that the receiving agent owns that review; the handoff only gives
  starting context and known constraints.
- Ask the agent to decide whether the task is a good idea, stale, already
  solved, over-scoped, or better handled differently.
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

Use this shape by default:

```text
I want to discuss and possibly work on: <short task title>

Context:
- <portable repo/product context>
- <what triggered this task>
- <known current state, branch/issue/PR names or URLs if relevant>
- <important constraints and ownership boundaries>

Before doing any implementation:
- Find the right repository from the current directory, a parent directory, or the usual workspace.
- Read the local agent/repo instructions.
- Inspect the relevant code, docs, tests, recent commits, and linked issue/PR state.
- Decide whether this task is still real, whether the proposed direction is a good idea, and whether a smaller/better fix exists.
- Call out stale assumptions, hidden risks, and anything that should stop the work.

Task:
- <what to investigate or implement if the review supports it>
- <expected behavior or decision criteria>
- <non-goals>

Validation:
- <focused tests/checks/live proof expected>
- <what evidence should be included>
- <what is explicitly not required>

Output:
- Start with your review findings and recommendation.
- Then give the proposed plan or patch summary.
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
- First real instruction to the receiving agent: review, discuss, assess.
