---
title: "Zero to App with AI, Part 7: Multi-User and a Real Name"
date: 2026-07-21T01:00:00Z
author: "Nate"
# aliases: ["/first"]
tags: ["ai-assisted-development", "authentication", "sqlite", "migrations"]
categories: ["Development"]
series: ["Zero to App with AI"]
series_order: 7
showToc: true
TocOpen: false
draft: true
hidemeta: false
comments: false
description: "The migration that touched every table, an auth system that stayed stateless, a fail-closed edge case worth stealing, and the rebrand to RepRepo."
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

From day one the roadmap said multi-user support would come late, deliberately. It touches every table and every query, so the plan (logged in the decision log, of course) was: build the fun features first, have every new table carry a nullable `user_id` from birth, and then let one migration sweep everything at once. This is the part where that bet got called.

## The pre-paid migration

The foresight paid exactly as hoped. Because check-ins and friends had been born with a `user_id` column already in place, the multi-user migration was mostly mechanical: create a `users` table, add `user_id` to the elder tables, assign every existing row to the first user, and scope every query. The dangerous class of migration, reshaping data you already care about, under load, with your own training history as the test data, had been reduced to the boring class.

> [!TIP]
> When you know a column is coming, add it nullable now. The cost is one dead column for a few weeks; the payoff is a migration that's a chore instead of an event. This works for any column you can see coming, not just `user_id`.

## Auth, grown not replaced

[Part 4]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-4" >}})'s auth was one shared password and an HMAC cookie. The multi-user version kept the shape and swapped the parts: each user row holds a bcrypt hash, and the cookie became `userId.hmac` where the HMAC is keyed by that user's password hash.

That one design choice preserves the properties that made v1 nice, without a sessions table:

- Stateless. Nothing to store or expire server-side.
- Change your password and all your devices are logged out (the HMAC key changed), but nobody else's are. Which turns "change password" into a self-service "log out my other devices" button, and it falls out of the design for free.
- Password changes require the current password, so a stolen cookie alone can't take over the account by rotating it.

Nice touches an agent contributes when the spec says "do auth properly": logins against nonexistent usernames still burn one bcrypt verify against a dummy hash, so there's no timing signal for "this user exists." Deactivated accounts fail with the same generic message and the same cost as a wrong password. Boring, standard, correct, and easy to skip when you're hand-rolling at midnight.

## The fail-closed edge case worth stealing

My favorite security decision of the phase handles a scenario most people never consider: what if the users table is empty but the old bootstrap password variable is still set?

> [!CAUTION]
> That's not a dev environment. That's a production box whose database went missing, say, restored from an ancient backup. The lazy behavior, "no users, auth off," would silently hand the app's data to the first visitor, with no error and nothing in the logs to suggest anything is wrong.

Instead: fail closed. That state refuses all requests until a restart re-bootstraps the first user. The general principle is worth more than the specific fix: enumerate the weird states and pick a posture for each, because "whatever the code happens to do" is also a security posture, just not one you chose.

Reality check for balance: the very first production bootstrap hit an environment-file quirk and the admin account came up with the default name, which I fixed by hand in SQL. Multi-user shipped in a day; flawless multi-user did not.

## Becoming RepRepo

Somewhere in here, "workout-tracker" stopped being a folder name and needed to be a thing. The rename phase, branding v2, landed on RepRepo: a repository of reps. It's a pun with a domain (reprepo.app), and it immediately earned a features phase literally titled "lean into the name": a record book, a trophy case for PRs.

A rename late in a project is a real refactor: service names, docs, UI copy, the works. Two things made it cheap: the agent executes mechanical renames tirelessly, and the docs-as-memory system meant there was exactly one place where each fact lived. Update it there, and every future session uses the new name automatically. Old infrastructure identifiers (the systemd unit, the database filename) kept their names until a scheduled migration, on the sound theory that renaming running infrastructure is its own project. That got folded into going public, which is [Part 8]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-8" >}}).

## What I'd tell you

1. Schedule invasive changes last, and pre-pay for them. The nullable column from birth trick works for any column you know is coming.
2. Grow auth; don't rewrite it. Keeping the cookie scheme's shape while upgrading its parts meant the mental model (and half the tests) survived.
3. Key sessions to the password hash. Statelessness plus free "log out everywhere on password change" is a lovely property for small apps.
4. Ask the weird-state question: what does the app do when the database is missing but config says it should exist? Then choose the answer on purpose. Fail closed.
5. Name the thing when it becomes a thing. The rename did real work on motivation. A project with a name and a domain gets finished differently than a folder called `workout-tracker-starter`.

[Part 8]({{< ref "/posts/series/ai-app-vibecoding/ai-app-vibecoding-8" >}}): opening the firewall on purpose. The security-hardening phase that gated it, the new edge gateway, and what "going public, intelligently" looked like for a one-person app.

## References and further reading

- [Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), OWASP. Covers the generic-error-message and uniform-timing guidance behind the dummy bcrypt verify, straight from the source.
