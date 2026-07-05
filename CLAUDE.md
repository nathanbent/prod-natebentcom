# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`natebent.com` — a personal website/portfolio built with **Hugo (extended build) + the PaperMod theme (heavily customized)**, deployed to **Hostinger shared hosting**. There is **no live dev server in the normal workflow**: the user views the deployed production site, so what's "live" is the last deployed build, not a local one.

## Commands

- **Build:** `hugo` → outputs to `public/` (gitignored). Watch the output for `ERROR`/`WARN`.
- **Local preview:** `hugo server -D` (includes drafts).
- **Deploy:** `./hostinger-deploy.sh` — runs `hugo`, then `rsync -avz --delete public/` over SSH to Hostinger, then commits source and pushes. Also has a one-time `--untrack-public` cleanup mode.
- **Reorganize posts into `year/slug/` bundles:** `python3 reorganize_posts.py content/posts` (dry run) / `... --execute`. Year comes from front-matter `date:`, slug from `slug:` or the filename.

### Deploy is a discrete, human-gated decision

**Never run `hostinger-deploy.sh` (or anything else that touches the live site) without explicit approval in the current conversation** — even if the build succeeded and looks correct. A successful build is not license to deploy. Same rule for anything that force-pushes/rewrites git history or reads/writes SSH keys or credentials.

## Hard rules (these prevent almost every bug hit here)

1. **Never edit files under `themes/hugo-PaperMod/`.** All customization lives at the **site level** (`layouts/`, `assets/`, `static/`, `data/`, `content/`). A file at the same relative path in the site root overrides the theme's copy — and once you copy a theme file down, you own that frozen copy and must re-check it after PaperMod updates.
2. **Hugo version matters — 0.146+.** Render hooks live in `layouts/_markup/` (0.146+); older Hugo wants `layouts/_default/_markup/`. A too-old Hugo **fails silently**, ignoring the hook and rendering defaults with no error. If a template change "does nothing," suspect version/path/build/cache *before* rewriting correct code.
3. **"It didn't work" is usually build/deploy/cache, not the code.** Verify in order: did the deploy actually run since the edit? is the edit in the file being built? did `hugo` succeed? is the browser showing a cached version (fingerprinted CSS changes filename on real edits; favicons cache hardest — test in a private window)? did the file save completely?
4. **Config file is `config.yml`** (YAML). Note: the notes in `notes/` sometimes call it `hugo.yaml` — the real file is `config.yml`.
5. **Keep the `notes/` docs in sync.** If a change alters how the site is built, themed, deployed, or colored, update the relevant note in the same session rather than letting docs drift.

## Where the real documentation lives

`notes/` holds detailed, battle-tested reference docs. **Read these before non-trivial work** — they cross-reference each other under aspirational names (in parentheses) that don't match the filenames:

- **`notes/natebent-hugo-papermod-customizations.md`** (aka "CUSTOMIZATIONS.md") — the catalog of every site-level customization: which file does what, feature→file index, front-matter conventions. Start here to find where a feature is implemented.
- **`notes/hugo-customizer-agent-guide.md`** (aka "AGENT_GUIDE.md") — how to make changes safely: the architecture patterns, the debugging playbook, deploy/verify checklist, and working style.
- **`notes/natebent-color-reference-guide.md`** (aka "COLOR-REFERENCE.md") — the full palette, design tokens, callout colors, and the *reasoning* behind them (contrast math, why the green is scoped).
- **`notes/image-generator-agent-guide.md`** — how the hand-written post SVG diagrams are built (colors, fonts, dark mode, XSS-sanitization checklist).

## Architecture cheat-sheet (the big picture)

- **Overrides only.** Everything custom is a site-level override of PaperMod. The theme is read-only.
- **Render hooks** (`layouts/_markup/`): `render-blockquote.html` turns `> [!NOTE|TIP|WARNING|CAUTION|IMPORTANT|INSIGHT|QUOTE]` into styled callouts; `render-codeblock.html` adds language labels.
- **Callouts are variable-driven:** each type just remaps three CSS custom properties (`--callout-border/bg/fg`) that one base blockquote rule reads. Add a type = icon in the render hook's `$icons` dict + a color block in `assets/css/extended/callouts.css` + one mapping line.
- **One accent drives the site:** `--accent` (ocean blue) in `assets/css/extended/custom.css` §1. Use `var(--accent)` for anything new — never hardcode a hex. `--accent-2` (racing green) is deliberately **scoped** to the `[!INSIGHT]` callout only.
- **`custom.css` is organized into 13 numbered sections (§0–§12)** — add new rules to the matching section; keep the `prefers-reduced-motion` block (§12) last. CSS custom properties belong in `:root`/`.dark`; a style rule pasted there is a bug even if native nesting makes it appear to work.
- **`--code-bg` is a multi-consumer token — don't repurpose it.** PaperMod also uses it for list-page backgrounds and the series-nav box. To restyle inline code, target `.post-content :not(pre) > code` (§4) instead.
- **Images flow through `layouts/_shortcodes/figure.html`,** which branches by type: **SVG** served as-is (never call `.Width`/`.Resize` on a vector — it errors), **PNG/JPEG ≥640px** gets build-time WebP + responsive srcset, everything else served as-is. All branches emit `data-full` for the lightbox.
- **Page-level JS all lives in `layouts/partials/extend_footer.html`,** gated to `.IsPage`, each feature in its own IIFE (reading-progress bar, TOC scroll-highlight, image lightbox). `<head>` additions go in `extend_head.html`.

## Content conventions (front-matter)

- `series: ["Name"]` + `series_order: N` — puts a post in a series and orders it *within the series-nav box only* (`series_order` is intentionally separate from `weight`).
- `weight` — Hugo's **global** sort key (affects `/posts/`, tags, everything). **Leave unset** (sorts by date); set only to *pin* a post.
- `summary:` is the site standard for `/posts/` excerpts. **Avoid `<!--more-->`** — a stray divider *silently overrides* your `summary:` (manual > front-matter > auto). If a post's excerpt ignores its `summary:`, `grep` the file for `<!--more-->` first.
- `.Site.Taxonomies` is keyed by `lower`, not `urlize` ("Proxmox SDN" → `proxmox sdn`, with a space).
- New posts: `archetypes/posts.md` is the template (defaults to `draft: true`).

## Gotchas when generating files

- **Heredocs:** quote the delimiter (`<< 'EOF'`) when content contains `$` or backticks (Hugo templates, SVG, JS), or bash will mangle it. When in doubt, use an editor.
- **Encoding:** use escape sequences, not literal special characters — `—` not a literal em dash, `\2014` in CSS `content`. Literal curly quotes/dashes have shown up as mojibake after round-trips.
