---
title: "Zero to App with AI, Part 2: Keeping It Cheap"
date: 2026-07-11T01:00:00Z
author: "Nate"
weight: 2
# aliases: ["/first"]
tags: ["ai-assisted-development", "claude-code", "ollama", "cost-optimization"]
categories: ["Development"]
series: ["Zero to App with AI"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Model routing, a free local LLM tier, and why session hygiene beats clever automation. The cost control setup that let me build all weekend without watching a meter."
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

The dirty secret of AI-assisted development is that the naive way to do it, one enormous chat session, the biggest model, all day, is expensive out of proportion to what you get. Before writing much code for [RepRepo](https://reprepo.app), I set up cost controls. The interesting part is that almost none of them rely on me remembering to do anything, which turns out to be the whole trick.

If you missed it, [Part 1]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-1" >}}) covered the docs-as-memory setup this all builds on.

## The routing table

My `docs/AI-WORKFLOW.md` starts with a table that says which model does which job:

| Task | Model | Why |
|---|---|---|
| Day-to-day coding, CRUD, UI, tests | Mid-tier (Sonnet) | Great at it, cheap |
| Architecture, schema review, stuck bugs | Big model, one focused session | Deep reasoning is worth paying for *occasionally* |
| Doc updates, checkbox-ticking, bookkeeping | Small model (Haiku) | It's bookkeeping |
| Commit messages, fake seed data, "what is middleware?" | Local LLM (free) | Iteration costs nothing |

The rule of thumb that emerged: the big model is for decisions, the mid model is for code, the small model is for chores, and the free model is for anything where "okay" is good enough.

If you have ever done QoS design, this will feel familiar. You are not trying to give everything the best treatment. You are trying to make sure the expensive queue only carries traffic that deserves it.

## Config beats discipline

A routing table you have to remember is a routing table you will ignore by Tuesday. So the routing went into configuration:

- Sub-agents carry their own model. In Claude Code, a sub-agent is a markdown file with YAML frontmatter, and one of the frontmatter fields is `model`. My code-reviewer agent is pinned to the big model in its config file, and my docs-keeper agent is pinned to the small one. When a review runs, the right model runs. Nobody chooses.
- Slash commands carry their own model too, via the same `model` frontmatter field. `/wrap-up`, the end-of-session command that ticks roadmap checkboxes and drafts decision log entries, runs on the small model, always.
- A git alias handles commit messages for free. `git aimsg` pipes the staged diff through a code-tuned model on my home server's Ollama instance and prints a conventional commit message. Costs nothing, runs on hardware I already own.

> [!QUOTE] docs/DECISIONS.md
> Cost control that relies on remembering to switch models fails; encoding it in config makes the cheap path the default path.

That entry from my own decision log says it better than I can in prose. The pattern shows up in networking all the time: policy that lives in muscle memory drifts, policy that lives in config holds.

## The free tier is better than you think

I run Ollama on a homelab box with a decent GPU, with a browser chat UI for me and a raw API for scripts. The models on it (a 14B code model, a couple of general models in the 14B to 24B range) are nowhere near frontier quality, and it does not matter, because I only send them work where mediocre is fine: commit messages, learning questions ("explain Express middleware like I'm new"), rubber-ducking, and generating fake seed data.

The first time I tested the pipeline, the local model confidently explained that OLLAMA stands for "Online Learning and Language Acquisition for Mathematics and Arithmetic." It does not stand for anything. That hallucination was clarifying rather than alarming: this is the tier where confident nonsense is acceptable, because everything it produces is either checked by me in two seconds (a commit message) or purely educational scaffolding I will verify against real docs anyway. Route accordingly.

## Session hygiene: the biggest lever isn't a tool

Here is the thing that actually dominates cost: every message you send re-sends the whole conversation. The API is stateless, so your entire history rides along with each new message. Caching softens this (Claude Code caches your session automatically, so previously processed history is re-read at a steep discount instead of full price), but the history still gets re-read and billed on every turn, so a long meandering session still gets more expensive per message the longer it runs. The fix is structural, not heroic:

One session, one task, then end it. Start a session, build the phase, run the wrap-up, close. The next session starts fresh, and because of the docs-as-memory setup from Part 1, it starts fresh with full context, for free. CLAUDE.md and the docs folder carry everything between sessions. Chat history carries nothing but cost.

This is also why the phase structure matters financially, not just organizationally. A phase is sized to fit comfortably in one session. "Scaffold the client" is a session. "Also fix that bug and discuss deployment strategy" is a second one.

## The counterintuitive one: automation isn't cheaper

When I first asked "can we automate this more?", the honest answer I got, and later verified, was that most automation increases spend.

> [!CAUTION]
> Multi-agent orchestration, agents controlling agents, parallel everything: these burn several times the tokens of a single focused session, because every agent carries its own copy of the context. The bill scales with the number of contexts, not the amount of work done.

The economical version of automation is boring: pinned models, one-keystroke commands for repetitive prompts, a local model for the free tier, and docs that eliminate re-explanation. Fancy orchestration has its place (Part 5 covers where parallel sessions genuinely earned their cost), but as a default it is a bill, not a feature.

## What I'd tell you

1. Write the routing table down, then push it into config, per-agent models and per-command models, so the cheap path is the default path.
2. Stand up a free tier. Even a modest local model absorbs a surprising amount of work once you are honest about which tasks tolerate "okay."
3. Treat sessions like transactions. Open, do one thing, commit, close. Long sessions are where money goes to die.
4. Let the repo be the memory. Every fact in a doc is a fact you never pay to re-explain.
5. Distrust automation that multiplies contexts. More agents does not mean more productivity per dollar. Usually the opposite.

Next, [Part 3]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-3" >}}): the actual build. The phase rhythm, what end-of-phase reviews caught (including a timezone bug that would have eaten my evening workouts), and the one mistake I kept making anyway.

## References and further reading

- [Model configuration](https://code.claude.com/docs/en/model-config), Claude Code docs. Covers the `model` frontmatter field for sub-agents and commands.
- [How Claude Code uses prompt caching](https://code.claude.com/docs/en/prompt-caching), Claude Code docs. Why long sessions cost what they cost, and what invalidates the cache.
- [Prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching), Claude API docs, if you want the underlying mechanics.
