---
title: "Zero to App with AI, Part 4: Shipping Is Still Sysadmin"
date: 2026-07-15T01:00:00Z
author: "Nate"
weight: 1
# aliases: ["/first"]
tags: ["ai-assisted-development", "deployment", "linux", "self-hosting"]
categories: ["Development"]
series: ["Zero to App with AI"]
series_order: 4
showToc: true
TocOpen: false
draft: false
hidemeta: false
comments: false
description: "Auth in one dependency-free file, a deploy to a homelab VM over SSH, and the BOM, CRLF, and sudo war stories the AI and I debugged together. Plus /ship, the one word deploy."
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

By the end of [Part 3]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-3" >}}) the app worked great, on my desk. This is the part where it had to run somewhere else, and where "AI writes the code" met "computers are still computers." Spoiler: the app-side work was almost eerily smooth, and every single problem lived in the last mile of Linux plumbing. As the guy whose day job is networks, I found this both humbling and deeply familiar.

## The app side: deliberately boring

Auth started as the simplest thing that genuinely locks a door: one password in an environment variable, an HMAC-signed httpOnly cookie, zero new dependencies, about 70 readable lines. Unset the variable and auth is off, so local dev is unchanged. Change the password and every device is logged out, which is the feature, not a bug. The decision log records why not the alternatives: proxy-level basic auth couples the app to the proxy and looks awful on a phone, and JWT libraries are dependency weight with no benefit at one user. It later grew into real per-user auth with bcrypt (Part 7), and the upgrade path was clean precisely because v1 was small.

Production shape: one process, one port. Express serves the API and the built client, with an SPA fallback. A `/api/export` endpoint dumps all your data as JSON. Never build a personal-data app without an exit door.

Backups use SQLite's online backup API, stamped daily, pruned to fourteen, run by cron.

> [!CAUTION]
> A naive file copy of a live SQLite database can catch it mid-write, especially in WAL mode where recent transactions live in a separate -wal file next to the main one. The copy looks fine, restores fine, and is quietly missing or corrupting data. The online backup API exists specifically to take a consistent copy while the database is in use.

The full local smoke test, no cookie 401s, wrong password rejected, login sets the cookie, export works, static app serves, SPA fallback falls back, passed 8-for-8 before anything left my machine.

## The VM side: five sharp edges in one afternoon

Deploying to a fresh Ubuntu VM in the homelab produced, in order:

### The invisible byte

First deploy script, piped over SSH: `bash: line 1: #!/usr/bin/env: No such file or directory`. The script had a UTF-8 BOM, three invisible bytes (`EF BB BF`) that Windows tooling loves to prepend, and bash tried to execute `\xEF\xBB\xBF#!/usr/bin/env` as a command. The shebang line was fine. The file just didn't start with it.

### The 700 house

`useradd -m` created the app user's home directory with owner-only permissions, so the deploying user couldn't `cd` into the directory it had just created. One `chmod 755` later, the whole install script ran clean.

### The firewall that was doing its job

App live on the VM, health check green on the VM, and total silence from my desk. UFW default-deny with only SSH allowed. This is the one I should have predicted before the agent did, given what it says on my resume. The fix wasn't "open everything"; it was one rule allowing the app port from private-network addresses only.

### The sudoers ordering trap

For unattended deploys I dropped a NOPASSWD rule into `/etc/sudoers.d/99-deploy`, and sudo kept prompting anyway.

> [!INSIGHT]
> Sudoers drop-ins load alphabetically and the last matching rule wins. A NOPASSWD rule early in the alphabet is silently overridden by any later file that matches the same user. My `99-deploy` lost to an existing file further down the list; renaming mine `zzz-` fixed it.

Bonus discovery: this VM's Ubuntu ships sudo-rs, the Rust rewrite of sudo that became the default in Ubuntu 25.10, and its error messages are just different enough from classic sudo to gaslight you mid-debug.

### PowerShell's CRLF ambush

The polished deploy pipeline piped the update script to the VM through PowerShell, which helpfully rejoins piped lines with Windows line endings. Bash met `$'\r'` and quit.

> [!TIP]
> Fix the instance, then make the class impossible: stop piping (scp the file, strip `\r` on the far side) and add a `.gitattributes` pinning `*.sh` to LF forever, so a Windows checkout can never re-poison the scripts. Any time an OS boundary bites you, look for the one-line config that removes the whole category.

None of these are AI problems or AI solutions, but debugging them with an agent was genuinely faster: it read the error, named the BOM, knew the sudoers ordering rule, wrote the `.gitattributes`. What it couldn't do was hold my sudo password, by design. The privileged bootstrap steps stayed human. Then a deliberately narrow permanent rule (run commands as the app user plus restart this one service, nothing else) let everything after be unattended.

## /ship: the phase-ending word

All of it condensed into a slash command. Saying `/ship` at the end of any session now runs the checklist: update the docs (roadmap ticks, decision log entries), commit and push in logical chunks, deploy committed HEAD to the test server, verify from the outside, report. The deploy script runs the test suite first and refuses to ship red. It archives committed HEAD only. Uncommitted work deliberately doesn't deploy, which quietly enforces the commit discipline I kept flunking in [Part 3]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-3" >}}).

The target is a parameter, so "add a second test server" is an argument, not a new script. And because it's a checklist in a file rather than a habit in a head, every future session, mine or the agent's, ends phases exactly the same way.

## What I'd tell you

1. Make v1 auth small enough to read in one sitting. You can grow it later. You can't easily shrink a framework.
2. One process, one port, one SQLite file is a gloriously deployable shape for a personal app. Resist the urge to be web-scale.
3. Expect the last mile to be sysadmin, and let the AI pair on it. It has read more man pages than you have.
4. Keep privileged access narrow and boring. Broad temporary sudo for bootstrap, then a scoped permanent rule for the pipeline.
5. Turn your deploy into one word. If shipping takes a checklist you must remember, you'll skip steps. If it's a command, you won't.

[Part 5]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-5" >}}): the multiplier. Running phases in parallel sessions, scoped sub-agents with their own job descriptions, and where "more agents" actually earned its cost.

## References and further reading

- [Using the SQLite Online Backup API](https://sqlite.org/c3ref/backup.html), sqlite.org. Why a live database wants this instead of `cp`.
- [Adopting sudo-rs by default in Ubuntu 25.10](https://discourse.ubuntu.com/t/adopting-sudo-rs-by-default-in-ubuntu-25-10/60583), Ubuntu Discourse announcement.
