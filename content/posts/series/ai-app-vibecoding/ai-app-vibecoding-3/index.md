---
title: "Zero to App with AI, Part 3: The Phase Rhythm"
date: 2026-07-13T01:00:00Z
author: "Nate"
weight: 3
# aliases: ["/first"]
tags: ["ai-assisted-development", "claude-code", "testing", "code-review"]
categories: ["Development"]
series: ["Zero to App with AI"]
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Build in one session, review at the boundary, ship, repeat. How the core app came together phase by phase, and what the reviews actually caught."
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

[Part 1]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-1" >}}) and [Part 2]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-2" >}}) covered the setup: docs as memory, cost controls in config. This is the part where the app actually got built, a core logging loop, a plans system, and a PR detection engine, and where the working rhythm emerged that carried the whole project:

One phase per session. Review at every phase boundary. The human tests between phases.

That is the entire method. The rest of this post is what it looks like in practice and what it caught.

## The loop

Each phase ran the same way:

1. Paste the kickoff prompt (pre-written at the end of the previous phase) into a fresh session.
2. The agent builds, explaining non-obvious choices as it goes. That is a CLAUDE.md rule, because I am learning web dev here, not just extracting code from a machine.
3. At the boundary, a review pass: read the diff, run everything, poke the edges.
4. I use the result for real, note what is off, and feed that into the next phase.

The phases were deliberately small. Phase 2 was "pick exercise, enter weight and reps, save set, see today's session." Phase 3 added workout plans, so "start Push Day" pre-populates the session. Phase 4 was the dopamine feature: PR detection with a "New PR!" celebration, and a progress chart per exercise. Each one fit comfortably in a single session, which Part 2 explained is also where the money is.

## Tests first, but only where bugs hide

We did not test everything. We tested the one module most likely to have subtle bugs, a rule written into CLAUDE.md on day zero: the PR math. Weight PRs, rep PRs at a given weight, estimated 1RM (the Epley formula, whose accuracy falls off as reps climb, so the app's 12 rep cutoff is part of the spec, not an implementation detail), and session volume records.

The tests were written against the rules in DATA-MODEL.md before the route existed, each one running against a fresh in-memory SQLite database. And they immediately forced real decisions the prose spec had glossed over. Does a bodyweight set (NULL weight) break a weight PR? No, it is its own "reps at bodyweight" bucket. Does the first set you ever log count as a PR? No, "broken" implies something existed to break. Does a heavy warm-up set the bar? Never. Warm-ups are excluded, and there is a test proving a 500 lb warm-up can't.

Every one of those edge cases would have been a quiet production bug. Instead they are one-line test names.

## What review actually caught

The end-of-phase reviews earned their keep with real finds, not style nits. Highlights, in ascending order of how much they would have annoyed me in production:

**Dormant features.** Review noticed the warm-up exclusion logic was beautifully tested and completely unreachable. The UI had no warm-up checkbox yet, so the flag was always false.

> [!INSIGHT]
> Nothing about "all tests green" tells you a feature can't be triggered. Tests prove the logic is correct if reached. Only tracing the path from the UI proves it is reachable.

**The over-celebrating PR banner.** Session volume PRs originally fired on every set after your session total passed the old record, so on a good day, sets five through ten would each yell "New PR!" at you. Celebration inflation. The fix: only fire on the set that first crosses the record, with a regression test so it stays fixed.

**The evening-workout timezone bug.** The client resumed "today's session" by comparing a UTC timestamp's date prefix to the local calendar date. Which works fine, until you train after 7 PM in a UTC-minus timezone, when the UTC date rolls over and a page refresh mid-workout would silently create a duplicate session instead of resuming.

> [!CAUTION]
> This is the classic shape of a timezone bug: no error, no crash, just quietly wrong data, and it only reproduces in the evening, so it survives every daytime test you run. The fix (compare `Date` objects, not string prefixes) landed with a comment explaining the trap for whoever touches that code next.

## The mistake I kept making

Every phase, the same finding at review time: the work wasn't committed. At one point two entire phases, around eight hundred lines of the best code in the project, existed only in the working tree, one bad `git checkout` away from oblivion. This despite "small commits, one feature per commit" sitting right there in CLAUDE.md since day zero.

The lesson generalizes. An agent optimizes for the thing you are asking about right now (the feature), and the standing rules (commit discipline) quietly lose priority. It is the same failure mode as a junior engineer who nails the change but skips the change ticket, and the fix is the same: not scolding, structure. Commit-and-push became part of an end-of-phase checklist that runs as a single command. Structure beats intention, for AIs exactly as for humans. That checklist became `/ship`, which gets its own war story in Part 4.

## The human is the test between phases

The most valuable QA in the whole project cost nothing: I used the app. Logged sets from my phone. Noticed the exercise dropdown was miserable with 52 entries, which became a type-to-search picker. Noticed starting a workout felt bare, which became check-in cards (sleep, mood) that are deliberately skippable, because nothing is allowed to stand between you and logging a set.

Later, real gym sessions generated a nine-item friction list that became an entire ideation phase (that is Part 6).

> [!TIP]
> None of that feedback is producible by an agent, however good, because it comes from squinting at your phone between sets with chalk on your hands. Be the field test. Your friction list is the roadmap's best input.

## What I'd tell you

1. Size phases to one session. If the kickoff prompt doesn't fit in a paragraph, the phase is too big.
2. Concentrate tests where the subtle bugs are, for us the PR math, and let curl checks cover the plumbing.
3. Review at boundaries, not continuously. Batch review at the phase edge caught everything worth catching, cheaper.
4. Make the standing rules structural. Anything you find yourself repeating at review time (commit! update docs!) should become a checklist the agent executes, not advice it remembers.
5. Use the thing between phases. Real use finds what tests can't.

Part 4 is the deploy story: auth in one file, a homelab VM, and the five sysadmin sharp edges that no amount of AI polish saved me from.

## References and further reading

- [How Claude remembers your project](https://code.claude.com/docs/en/memory), Claude Code docs, on CLAUDE.md rules and why standing instructions still need structural enforcement.
- [Validation of the Brzycki and Epley equations for 1RM prediction](https://opensiuc.lib.siu.edu/cgi/viewcontent.cgi?article=1744&context=gs_rp), if you want the actual research on where 1RM estimation formulas hold up and where they don't.
