---
title: "Zero to App with AI, Part 6: The App Taught Us What to Build"
date: 2026-07-19T01:00:00Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["ai-assisted-development", "product", "dogfooding", "side-projects"]
categories: ["Development"]
series: ["Zero to App with AI"]
series_order: 6
showToc: true
TocOpen: false
draft: true
hidemeta: false
comments: false
description: "Real gym sessions produced a nine item friction list that out-planned every brainstorm. Plus a survey of the apps that already solved this, and an ideation phase with zero code."
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

Everything up to here was built from imagination: what I thought logging a workout should feel like. Then I trained with it for real, phone in hand, chalk on fingers, rest timer running, and the roadmap got humbled. This part is about the highest-signal planning input the project ever had: actual use.

## The friction list

After the first real gym sessions I dumped every annoyance into a list. Nine items, all of them things no amount of desk-testing had surfaced, because they only exist under gym conditions: tired, hurried, one-thumbed. The highlights:

- Set grouping. A wall of individual sets is unreadable between exercises; sets want to cluster by exercise visually.
- Post-hoc editing. Fat-fingered 135 as 125? There was no way to fix a set after saving. At a desk you'd never notice. At the gym it's constant.
- Smart defaults. The app made me re-enter the weight I just used. The previous set is almost always the best guess for the next.
- Sort order, collapsible sections, calmer check-ins. The start-of-workout screen had grown enthusiastic; under time pressure you want it quiet and fast.
- A Manage Plans page and plan archiving. Plans accumulate, and the picker shouldn't scroll forever past experiments you're done with.

None of these is clever. That's the point. They're obvious in use and invisible in theory.

> [!TIP]
> Write the friction list in the moment or right after. These observations evaporate within hours, and once they're gone you're back to designing from imagination.

## Steal like a product manager

Before turning the list into work, one session did something teams skip: surveyed the incumbents. Strong, Hevy, FitNotes, Jefit. What do apps with millions of gym-hours of accumulated feedback all agree on? The survey confirmed the friction list from the outside: auto-fill defaults from the previous set are table stakes everywhere, rest timers matter, set editing is universal.

When your dogfooding complaints and the market's converged solutions agree, you can build without second-guessing. Where they diverge is interesting too: you either have a differentiator or a blind spot, and it's worth a minute deciding which.

## An ideation phase with no code

The friction list and the survey merged into a formal roadmap phase whose entire output was a document: a rated backlog, one line per idea, rated easy, medium, or hard, with just enough context to build from later, committed to the repo as `docs/FEATURE-IDEAS.md`.

Then the roadmap grew three implementation phases sorted by that rating: quick wins (the easy column, knocked out in one session), medium features, and the one genuinely hard interaction, supersets, which got a phase to itself rather than being wedged into a grab-bag.

This sounds like bureaucracy for a hobby app. It's the opposite. It's what let an AI-paced project stay aimed. When building costs hours instead of weeks, the scarce resource is knowing what's worth building. A rated backlog in the repo means every future session picks from a priority queue instead of improvising, and, per the docs-as-memory principle from [Part 1]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-1" >}}), it lives where the agent can actually see it: not in my head, not in chat history, not in a notes app.

## The check-in lesson: features must earn their place in the flow

An earlier phase had added daily check-ins (sleep, mood) as cards when you start a workout, designed skippable from day one, on the principle that nothing stands between you and logging a set. Real use upgraded that principle from design guideline to law: even optional cards read as noise at 6 AM, which is why "calmer check-ins" made the friction list. The dopamine feature ("New PR!" celebrations) survived contact with reality. The earnest wellness features had to learn to whisper.

> [!INSIGHT]
> The flow you optimize is the one you're in when you're weakest: tired, rushed, low-patience. Design reviews happen at desks by people at their sharpest. Your users, even when that's just you, are neither.

## What I'd tell you

1. Ship to yourself early, then actually use it. The milestone "log a real workout from my phone" was in the roadmap from day zero, and everything after it was better-aimed than everything before it.
2. Write the friction list immediately, in the moment or right after.
3. Survey the incumbents once, deliberately. Where your complaints and their solutions agree, build with confidence. Where they diverge, you might have a differentiator, or a blind spot.
4. Make ideation a phase with a committed artifact. A rated backlog in the repo beats ideas in your head, in your chat history, or in a notes app the agent can't see.
5. Rate by effort and let the easy column fund momentum. A session of quick wins after a heavy phase keeps the project fun, and fun is the actual fuel of side projects.

Part 7: the app grows up. Real multi-user auth, the migration that touched every table, and how "workout-tracker" became RepRepo.

## References and further reading

- [Create custom subagents](https://code.claude.com/docs/en/sub-agents) and [How Claude remembers your project](https://code.claude.com/docs/en/memory), Claude Code docs, if you're wiring the ideation-phase pattern into your own repo: the backlog doc only works because the agent reads the repo.
