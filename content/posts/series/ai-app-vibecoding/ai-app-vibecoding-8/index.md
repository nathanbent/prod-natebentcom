---
title: "Zero to App with AI, Part 8: Going Public Without Being Naive"
date: 2026-07-23T01:00:00Z
author: "Nate"
# aliases: ["/first"]
tags: ["ai-assisted-development", "security", "self-hosting", "caddy"]
categories: ["Development"]
series: ["Zero to App with AI"]
series_order: 8
showToc: true
TocOpen: false
draft: true
hidemeta: false
comments: false
description: "A security phase as the hard gate, a CSP bug involving invisible characters, a fresh edge server with a DNS cutover, and the runbook split: agent writes, human executes."
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

The roadmap phase was titled "Go public (for fun, done intelligently)" and it carried one non-negotiable line: security hardening is the gate for opening the firewall, not a nice-to-have. This part is what that gate contained, and how a homelab app ended up at [alpha.reprepo.app](https://alpha.reprepo.app) without me lying awake about it.

## The hardening phase

Multi-user ([Part 7]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-7" >}})) plus a dedicated security pass were hard prerequisites. The pass produced a `SECURITY.md` documenting the posture, and a pile of concrete changes. The flavor of them:

### Headers and CSP, with a war story

Helmet's defaults, tuned to what the app actually is: a same-origin SPA, self-hosted fonts, one inline script (the pre-paint theme snippet that stops dark-mode flash). That script is hash-allowlisted in the CSP rather than allowing `unsafe-inline`, and the hash is computed from the built index.html at boot, so a rebuilt bundle can never silently break it.

The bug that made this fun: browsers normalize CRLF to LF when parsing HTML, so the inline script the browser hashes is always the LF version, no matter what bytes you served. An index.html checked out on Windows with CRLF endings meant the server computed its hash over CRLF bytes while the browser computed its hash over LF text.

> [!CAUTION]
> A CSP hash mismatch from line endings never matches and never will, on any browser, for any user, and nothing in the served file looks wrong. If an inline script that should be allowlisted is blocked everywhere, check the line endings before you check anything else. Line endings: still undefeated (see [Part 4]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-4" >}})).

### Proxy trust as an explicit opt-in

`X-Forwarded-For` is a lie anyone can send. It's a request header, and until a reverse proxy you control is actually the thing setting it, trusting it would let anyone dodge the per-IP login rate limit by typing their preferred identity into a header. So proxy trust sits behind an environment flag, set only on the box where it's true, with exactly one trusted hop.

### Small, deliberate bounds everywhere

An explicit JSON body-size limit ("make the bound a decision, not a default"). Shared input validators. Even the CSV export got a formula-injection guard, because a cell starting with `=` is executable when the file is opened in a spreadsheet, and a gym note is user input. OWASP documents this one under CSV injection; it's exactly the kind of thing an agent adds when the spec says "harden the export" and a human hand-rolling it at midnight skips.

### Backups that leave the building

Nightly SQLite snapshots already existed ([Part 4]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-4" >}})). The hardening phase added an off-machine copy: the backups directory is itself a git repo pushed to a private remote with a dedicated write-only deploy key. Cheap, versioned, offsite. The 3-2-1 rule on a hobby budget.

## The go-public shape

The actual exposure was its own decision, and, worth noting, it's logged in the decision log with a phrase I've started using elsewhere:

> [!QUOTE] docs/DECISIONS.md
> Decided by the human, recorded as givens.

The agent proposed options; where traffic enters my network is not its call.

The shape: a fresh cloud-edge gateway running Caddy (automatic HTTPS, which really is automatic: point the DNS records at it and certificates are obtained and renewed with no ceremony), connected to the app box over a private network, with a DNS-based cutover. Start serving on the new name, watch it, and keep the old path as instant rollback until confidence sets in. Going public also triggered the deferred infra renames from Part 7, but on the new server only, built clean with the RepRepo names, rather than renaming a live box in place.

Monitoring matched the project's scale: an external uptime ping (does it answer from the internet?) and a nightly disk-space guard that complains loudly on stderr, which cron faithfully delivers, when the backups volume runs low. The nightly backup email is supposed to be boring; the guard makes sure it gets noisy the week before the disk fills, not the night it does.

## The runbook split

My favorite process artifact of the phase: the build session produced all the code and config plus a runbook, the manual bring-up steps, in order, for a human to execute. The agent writes the runbook; I run it. Firewall changes, DNS records, credentials on new boxes: those went through my hands, every time, with the runbook making it mechanical instead of error-prone.

This split, automation authors and human executes, for exactly the privileged steps, is the security model that let an AI-paced project go internet-facing without ever handing an agent the keys. And the sysadmin comedy never stopped, for the record: the new boxes' Rust sudo broke my config-management tool's password prompts (workaround duly logged), because ops is ops forever.

## What I'd tell you

1. Make hardening a phase with a deliverable (`SECURITY.md`), and make it a gate. "The firewall opens when this phase closes" is a forcing function that actually forces.
2. Hash your inline scripts instead of allowing `unsafe-inline`, and compute the hash from the built artifact so deploys can't drift.
3. Don't trust forwarded headers until the proxy exists, then trust exactly one hop, by explicit config.
4. Offsite backups can be a git remote and a deploy key. Perfect is the enemy of having offsite backups.
5. Let the agent write runbooks for the steps only you should run. You get the rigor of automation and keep custody of the trust.

[Part 9]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-9" >}}) wraps the series: the unglamorous phases that made it feel like a real product, performance measured before optimized, a stability pass, a UI capstone, plus the Docker and CI pipeline, and the honest retrospective.

## References and further reading

- [CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection), OWASP. Why a cell starting with `=` in an export is a security issue.
- [Automatic HTTPS](https://caddyserver.com/docs/automatic-https), Caddy docs. What the edge gateway gets for free.
- [AutoCsp generates invalid hash for inline script if CRLF](https://github.com/angular/angular-cli/issues/32709), angular-cli issue tracker. The same line-ending CSP bug in the wild, if you want company in your suffering.
