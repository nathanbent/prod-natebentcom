---
title: "Zero to App with AI, Part 1: Write the Docs Before the Code"
date: 2026-07-09T01:00:00Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["ai-assisted-development", "claude-code", "side-projects", "process"]
categories: ["Development"]
series: ["Zero to App with AI"]
series_order: 1
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "How an empty folder became a working REST API in one day, and why the boring markdown files I wrote first were the highest leverage hour of the whole project."
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

This is a different kind of post for this blog. Less BGP, more JavaScript.

I built and shipped a real app, [RepRepo](https://reprepo.app), a workout tracker, essentially over one weekend, working with an AI coding agent (Claude Code, in my case, though most of this translates to any of them). Not a todo list demo either. It has a plans system, PR detection with unit tests, multi-user auth, security hardening, nightly backups, and tagged releases deployed by CI, and it is running on the public internet where I actually use it at the gym.

I should be clear about my starting point, because it matters for how you read this series. I am a network engineer. I can script, I can read code, and I run a homelab full of self-hosted services, but I had never built a web application. The agent wrote nearly all of the code. My job was direction, review, testing, and the sysadmin work at the end. Whether that counts as "building an app" is a philosophical question I will leave to the comments section I do not have.

This series is the honest write-up: what worked, what bit me, and what I would tell anyone starting the same experiment. Part 1 is about the counterintuitive first step, the one hour that made everything after it possible.

## The empty folder

Day zero looked like this:

```
workout-tracker/
├── README.md
├── CLAUDE.md
├── docs/
│   ├── ROADMAP.md
│   ├── DATA-MODEL.md
│   ├── DECISIONS.md
│   └── AI-WORKFLOW.md
└── .claude/agents/
```

No code. Not one line. Just markdown.

That felt backwards. Every instinct says start with `npm create vite` and get pixels on screen. But AI-assisted development changes the economics of documentation completely, for one reason.

> [!INSIGHT]
> The docs are the agent's memory. An AI coding session starts from zero every time. Anything you don't write down, you will re-explain every session, forever, at token prices. Write it down once and every future session starts already knowing the project.

This is not a metaphor. A coding agent does not remember yesterday's session, your preferences, or why you chose SQLite. Chat history dies when the session ends, and while it is alive it costs money to carry, because it rides along with every message you send. The repo, on the other hand, is free, permanent, and versioned. So the docs are not documentation in the usual sense, written after the fact for some hypothetical future reader. They are load-bearing infrastructure, consumed by the agent at the start of every single session.

Once that clicked, spending the first hour on markdown stopped feeling like procrastination and started feeling like configuring the router before plugging in the clients.

## The four files that matter

**CLAUDE.md** is the file Claude Code reads automatically at the start of every session (other tools have equivalents: rules files, instructions files, whatever your agent auto-loads). Mine is short and rule-dense: the stack, the architecture rules ("ALL business logic lives in the server, the client renders and calls /api"), workflow rules ("small commits, one feature per commit"), and cost rules (Part 2 is entirely about those). The guidance from the Claude Code docs is to treat it as the place you write down whatever you would otherwise re-explain, and to keep it concise, because shorter instruction files get followed more reliably.

One sentence in mine paid for itself fifty times over: "The developer is learning, explain non-obvious choices briefly as you go, and prefer simple, readable code over clever code." Every session, every explanation, calibrated to me, for free. If you are using a project like this to learn a stack, put a line like that in on day zero.

**docs/ROADMAP.md** breaks the project into phases with checkboxes. Phase 1: foundation. Phase 2: core logging loop. Phase 3: plans. Phase 4: PRs and progress charts. Each phase is small enough for one focused session, and each ends with its checkboxes ticked. This file became the heartbeat of the whole project, which is Part 3's story.

**docs/DATA-MODEL.md** is the schema, written in SQL, before any code existed. Five tables, and, crucially, the business rules in prose: how PR detection should work, what the Epley 1RM formula is and where it stops being trustworthy, what a "workout" even is. Code can tell you what the app does. Only a doc can tell you what the app is supposed to do, which is exactly the distinction an agent needs when it writes tests.

The file ended with a section called "Open questions (answer these before Phase 2)": lbs or kg? Track RPE? How do bodyweight exercises work? I answered them inline like a form. That ten minute exercise surfaced decisions I would otherwise have made accidentally, mid-implementation, three phases deep, and at least one of them (bodyweight exercises) would have meant a schema migration if I had discovered it late.

**docs/DECISIONS.md** is a decision log with a rigid little format, three lines per entry:

```
Decision: <what we chose>
Why: <the reason, one or two sentences>
Alternatives: <what lost, and why>
```

It started with two entries. It now has over forty, and it is the file I would rescue from a fire. When a fresh session asks "why is weight stored in lbs only?" the answer is in the repo, dated, with the alternatives that lost. Future me does not do archaeology, and the agent does not re-litigate settled questions. If you have ever kept a change log for a firewall, this is the same instinct pointed at software decisions.

## Day one, measured

With the docs in place, day one went: install Node, `git init`, resolve the open data-model questions, then paste a kickoff prompt (pre-written at the bottom of the roadmap) that scaffolded the Express + SQLite server. Schema, a seed script with 52 exercises, and the first three API routes. The agent tested everything with curl before calling it done, including the failure cases: bad exercise IDs got clean 400s, not stack traces.

By evening there was a working API with validated inputs. The next morning there was a React client. The docs took about an hour of that. Everything else in this series runs on the rails laid in that hour.

## What I'd tell you

1. Write CLAUDE.md first, or whatever your tool's auto-loaded context file is. Rules you write once are rules you never repeat.
2. Put the schema and the business rules in a doc, not just in code. Code says what. The doc says why, and what counts as correct, which is exactly what an agent needs to write real tests.
3. Keep a decision log with a format. Decision, why, alternatives considered. Three lines per entry. It compounds.
4. Answer the open questions before building. Make the doc ask you questions. The ten minutes I spent answering "how should bodyweight exercises work?" saved a schema migration later.
5. Pre-write the next kickoff prompt. Ending each phase by writing the prompt that starts the next one means zero cold-start cost.

The pattern under all five: move context out of your head and out of the chat history, into the repo. Chat history dies with the session and costs money to carry. The repo is free, permanent, and versioned.

Next up, [Part 2]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-2" >}}): how I kept the whole thing cheap. Model routing, running the boring work through a local LLM on the homelab, and why more automation usually means a bigger bill.

## References and further reading

- [How Claude remembers your project](https://code.claude.com/docs/en/memory), Claude Code docs. Covers CLAUDE.md loading behavior and what belongs in it.
- [Claude Code overview](https://docs.claude.com/en/docs/claude-code/overview), the official starting point if the tool is new to you.
