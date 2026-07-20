---
title: "Zero to App with AI, Part 9: The Unsexy Twenty Percent"
date: 2026-07-23T01:00:00Z
author: "Nate"
# aliases: ["/first"]
tags: ["ai-assisted-development", "performance", "docker", "retrospective"]
categories: ["Development"]
series: ["Zero to App with AI"]
series_order: 9
showToc: true
TocOpen: false
draft: true
hidemeta: false
comments: false
description: "Measuring before optimizing (and the optimization we refused to build), a stability pass, a UI capstone, tagged releases, Docker, and the honest retrospective on the whole experiment."
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

Features get the blog posts; the last twenty percent gets the users. This final part covers the phases that turned a working app into something that feels finished, and closes with what I'd actually tell you after taking a project from empty folder to public alpha with an AI pair.

## Performance: measure first, refuse gracefully

The performance phase started by writing down baselines (`docs/PERF.md`) before touching anything, and its best outcome was an optimization we didn't build. Optimistic UI for set logging was on the list; measurement showed server-side set logging completing in about a millisecond. You cannot perceive the thing optimistic UI would hide. Verdict, logged in the decision log: not built.

What did land was the boring, high-yield stuff: four database indexes justified by measured query plans (a fifth candidate turned out to be covered already, also logged), and proper cache headers. Vite hashes every asset filename by content, so hashed assets cache forever while index.html always revalidates. Deploys stay instant and the repeat visit is instant.

This phase also closed a standing question honestly: the "should we outgrow SQLite?" evaluation ended with SQLite stays, plus named revisit triggers, the specific future conditions that would reopen the question.

> [!INSIGHT]
> Decisions with expiry conditions beat decisions with vibes. "SQLite stays until X or Y happens" is a decision the project can rely on; "SQLite is probably fine" is a question wearing a decision's clothes, and it will be re-litigated in every architecture conversation forever.

## Stability and the capstone

A code-side stability phase added the things nobody tweets about: a request log (one line per API request), a unified error handler, conventions documented, coverage raised on the tested core. Then a UI capstone did a genuine information-architecture audit: every page's field styles reduced to one base rule; tap targets measured, not eyeballed; a curated icon set replacing ad-hoc emoji (emoji "stays where it's charming," real line from the decision log); contrast fixed to AA where an earlier theme pass had noted a gap and moved on.

The dashboard got reordered around a principle worth stealing for any tool-app:

> [!TIP]
> Start action first, recap second. The thing you came to do beats the review of what you did. If your tool's home screen leads with charts and history, you've built a report that happens to have a workflow attached.

Theming, by the way, had already grown from "dark mode?" into proper presets built from a beloved open palette, adjusted where needed to keep AA contrast. The pre-paint theme script from [Part 8]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-8" >}})'s CSP saga exists because a theme that flashes white at 6 AM is a bug, not a feature.

## Releases and the Docker ending

Somewhere in here, deploys grew up: from [Part 4]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-4" >}})'s `/ship` (push from my desk over SSH) to tag-driven releases. Push a version tag, GitHub Actions builds and deploys it. Versions v1.0.0 through v1.3.x shipped that way, including one release cut from an older commit than master because the newest work hadn't cleared review yet. The pipeline happily pins tags to whatever commit has earned production.

The alpha's final act (in progress as I write) is containerization: a Dockerfile and compose file, a `DATA_DIR` variable so mutable data lives outside the image, CI building images to a registry with deploy-by-pull behind an explicit mode gate, and, my favorite pragmatic compromise, host cron still reaching into the container for backups, because the backup story from Part 4 works and portability didn't require reinventing it. Each step has a runbook: rehearse, cut over, retire the old path. Also a rule learned twice now: `.sh` files and sudoers fragments get pinned to LF in `.gitattributes`. Line endings, my forever nemesis.

## The honest retrospective

### What the numbers say

Empty folder to public, multi-user, release-pipelined alpha in a weekend of real time. A couple hundred commits, six tagged releases, forty-plus logged decisions, and a test suite that runs in about a second.

### What made it work, ranked

1. Docs as memory ([Part 1]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-1" >}})). Still the highest-leverage hour. Every other practice depends on the repo carrying the context.
2. The phase rhythm with a human at every boundary ([Part 3]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-3" >}})). AI pace with human aim. Neither alone gets you both.
3. Structure over intention: checklists (`/ship`), pinned models, job-description agents. Everything I asked anyone to remember failed; everything I encoded worked.
4. Dogfooding as the planning department ([Part 6]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-6" >}})). The gym knew things no brainstorm knew.
5. Cheap by default ([Part 2]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-2" >}})), which is what made "just try it" the default answer all weekend.

### What I'd do differently

Commit discipline from hour one instead of learning it at review time, twice. `.gitattributes` before the first shell script, not after the second line-ending fiasco. And I'd write the friction list from real use even earlier: the pre-gym features I guessed at needed more rework than the post-gym features built from the list.

### The one-sentence version of the whole series

The AI multiplied how fast I could build; the boring structures around it, docs, phases, checklists, reviews, runbooks, multiplied how fast I could build the right thing without breaking what existed. You need both multipliers. The second one is yours to bring.

Thanks for reading. RepRepo is at [reprepo.app](https://reprepo.app), and yes, the PR banner still fires when I hit a rep record, and yes, it still feels great.

## References and further reading

- [Deploy your site](https://vitepress.dev/guide/deploy), VitePress guide, which documents the caching pattern used here: content-hashed asset filenames get immutable long-term caching while the HTML entry point revalidates.
- [git-worktree](https://git-scm.com/docs/git-worktree) and the Claude Code docs on [memory](https://code.claude.com/docs/en/memory) and [sub-agents](https://code.claude.com/docs/en/sub-agents), if you're starting your own version of this experiment and want the primitives the series leaned on.
