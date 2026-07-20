---
title: "Zero to App with AI, Part 5: Scaling Me, Not the AI"
date: 2026-07-17T01:00:00Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["ai-assisted-development", "claude-code", "agents", "git-worktrees"]
categories: ["Development"]
series: ["Zero to App with AI"]
series_order: 5
showToc: true
TocOpen: false
draft: true
hidemeta: false
comments: false
description: "Parallel sessions in git worktrees, sub-agents with job descriptions, and sub-projects with their own plan docs. How one person's attention became the only real bottleneck, and how we widened it."
canonicalURL: "https://canonical.url/to/page"
disableHLJS: true # to disable highlightjs
disableShare: true
hideSummary: false
searchHidden: true
ShowReadingTime: true
ShowBreadCrumbs: true
ShowPostNavLinks: true
ShowWordCount: true
ShowRssButtonInSectionTermList: true
UseHugoToc: true
cover:
    image: "<image path/url>" # image path/url
    alt: "<alt text>" # alt text
    caption: "<text>" # display caption under cover
    relative: false # when using page bundles set this to true
    hidden: true # only hide on current single page
editPost:
    disaled: true
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link
---

Around the middle of the project something flipped: the agent was no longer the bottleneck. I was. One session built a feature faster than I could specify the next one. [Part 2]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-2" >}}) warned that multiplying agents multiplies cost. This part is about the places where parallelism and delegation genuinely paid, and the structures that kept it from becoming chaos.

## Parallel phases in worktrees

The roadmap had independent phases queued up. Daily check-ins and a settings/themes page touched almost disjoint code. So they ran as separate sessions, simultaneously, each in its own git worktree, launched from pre-written, self-contained prompts.

If you haven't used worktrees: `git worktree add ../feature-x` gives you a second working directory checked out to its own branch, backed by the same repository. No second clone, no stash juggling, and each parallel session gets a filesystem of its own to make a mess in. It is the difference between two people working on two copies of a document and two people fighting over one keyboard.

The mechanics that made this safe:

- Independence first. Phases were picked for minimal overlap. The one predictable collision (both touching the main stylesheet) was flagged in advance as "expect a small merge conflict; resolve at merge time." It was, and it was.
- Self-contained prompts. Each parallel session got the full brief: read these docs, build this phase, end with `/ship`. No session depended on chat history from another.
- The repo as the only communication channel.

> [!INSIGHT]
> Parallel sessions coordinate through commits and docs, never through shared conversational state. Which is exactly how human teams that work, work. If two sessions need to talk to each other, the thing they need to say belongs in a doc anyway.

## Sub-agents with job descriptions

Claude Code lets you define sub-agents as little markdown files: a description of when to use them, which tools they may touch, which model they run on, and a system prompt as the body. Over the project these accumulated into a small staff:

- code-reviewer: read-only tools (it literally cannot edit files, reviews report, they don't meddle), pinned to the big model, briefed on this project's specific bug habitat: PR-math edge cases, NULL weights, business logic leaking into the client.
- docs-keeper: pinned to the small cheap model, allowed to edit, briefed to be terse and never rewrite history in the decision log.
- And later, per-part specialists, which is where it gets interesting.

The job-description framing is the useful part. A sub-agent file answers "when should you call me, what am I allowed to do, and what do I cost," which is the same information you'd want about a contractor. A clever one-off prompt answers none of those and is gone tomorrow.

## Sub-projects: a plan doc plus a team

The best structure of the whole project emerged for a bigger feature ("exercise intelligence": sectioned plans, a metadata-rich exercise database, a drag-and-drop builder, markdown import/export). Too big for a phase, it became a sub-project: one plan document splitting the work into parts A through D, and, this is the part I love, each part got its own scoped sub-agent defined in the repo: a schema-builder, an exercise-enricher, a UI-builder, a porter.

Each part then ran as its own session with its own specialist, against a shared written plan. The plan doc did for the sub-project what CLAUDE.md does for the repo: carried the intent, so no session had to be told twice. Part A (schema plus migration) shipped with a boot-time, idempotent migration that correctly upgraded the live server's real database, old plans got a default section, exercises re-pointed, which I verified against production data before Part B started.

## What stayed human

With all this delegation, the striking thing is what couldn't be delegated:

- Sequencing decisions. Multi-user was deliberately ordered after the fun features. It touches every table, so doing it last let one migration sweep everything (Part 7). An agent proposed the reasoning; choosing it was mine.
- The test between phases. Every parallel stream still funneled through me using the app before the next phase started ([Part 3]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-3" >}})'s rule).

> [!WARNING]
> Parallel building is safe. Parallel unreviewed shipping is how compound misunderstandings happen. The human reviewing at the merge seams is the thing that makes all of this safe to do at all; parallelize the work, never the judgment.

- Anything requiring trust. Sudo passwords, firewall decisions, what goes on the public internet. The agent scripts around these boundaries respectfully; it doesn't cross them.

I looked briefly at the always-on assistant frameworks (the OpenClaw genre) for "have the AI run the whole pipeline itself." Wrong tool for this job: those shine as persistent personal assistants across chat apps. For repo work, the native primitives, slash commands, sub-agents, parallel sessions, and worktrees, turned out to be all the orchestration a one-person project needs, with no extra moving parts to maintain.

## What I'd tell you

1. Parallelize phases, not opinions. Two sessions building disjoint features: great. Two sessions with overlapping judgment calls: merge hell with extra steps.
2. Worktrees are the safety rail. Each parallel session gets its own checkout; the merge is explicit, reviewable, and yours.
3. Write job descriptions, not prompts. A sub-agent file that says when to use me, what I may touch, and what model I run on is reusable forever. A clever one-off prompt is gone tomorrow.
4. Big features want a plan doc and a team of specialists. The sub-project pattern (plan plus part-scoped agents plus one session per part) scales shockingly well.
5. Keep yourself in the merge. Scale your attention, don't remove it.

[Part 6]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-6" >}}) changes register entirely: what happened when I actually took the app to the gym, and how nine annoyances between sets became the most productive planning document in the repo.

## References and further reading

- [git-worktree](https://git-scm.com/docs/git-worktree), git-scm.com. The full mechanics of linked worktrees.
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents), Claude Code docs. The frontmatter format, tool allowlists, and delegation behavior.
- [Model configuration](https://code.claude.com/docs/en/model-config), Claude Code docs, for pinning models per sub-agent.
