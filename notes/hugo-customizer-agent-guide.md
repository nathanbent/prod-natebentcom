# Agent Guide — Making Changes to natebent.com

Instructions for an AI assistant helping modify this Hugo + PaperMod site.
Read `CUSTOMIZATIONS.md` alongside this — it's the map of what already exists.

---

## Context you need up front

- **Stack:** Hugo (extended build) + PaperMod theme. Deployed to **Hostinger**
  shared hosting via `hostinger-deploy.sh`: it runs `hugo`, then
  `rsync -avz --delete public/` over SSH. There is **no live dev server in the
  normal workflow** — the user views the deployed production site.
- **The user is technical** (network engineer, runs a homelab, comfortable in a
  terminal and editing files directly). Give real explanations, not hand-holding.
  They value understanding *why*, not just paste-and-pray.
- **Repo layout:** standard Hugo. Site-level overrides in `layouts/`, `assets/`,
  `static/`, `data/`, `content/`. Theme in `themes/hugo-PaperMod/` (read-only —
  see below).

---

## Rules that prevent 90% of the bugs we hit

1. **Never edit `themes/hugo-PaperMod/`.** All changes go in site-level dirs. To
   override a theme file, copy it to the same relative path under the site root and
   edit the copy. (This also means: if you copy a theme template, you now own a
   frozen copy — note that for the user so they know to re-check it after PaperMod
   updates.)

2. **Confirm the Hugo version before using version-sensitive features.** Render
   hooks live in `layouts/_markup/` (Hugo 0.146+). Older Hugo wants
   `layouts/_default/_markup/`. A too-old Hugo **fails silently** — it ignores the
   hook and renders defaults with no error. If a template change "does nothing,"
   suspect the version or the path before anything else. Check with `hugo version`.

3. **"It didn't work" is usually a build/deploy/environment issue, not the code.**
   This came up repeatedly. Before re-writing correct code, verify in this order:
   - Did the deploy script actually run since the edit?
   - Is the edit in the file that's *being built* (right path, right box)?
   - Did the build succeed? (`hugo` output — watch for ERROR/WARN.)
   - Is the browser showing a cached version? (Fingerprinted CSS changes filename
     on real changes; favicons cache hardest — test in incognito or hit the URL
     directly.)
   - Did the file save completely? (`tail` it — truncated saves happen.)

4. **Instrument, don't guess.** When a template renders nothing, add temporary
   *visible* debug output (not HTML comments — Hugo/minify can strip those) that
   prints the intermediate values, deploy, and read them. Example that cracked the
   series-nav bug:
   ```
   SN-raw:[{{ .Params.series }}]
   SN-key:[{{ index .Site.Taxonomies.series (lower (index .Params.series 0)) }}]
   ```
   Reading actual values beats theorizing. If Hugo is available in your environment,
   reproduce the issue in a throwaway minimal site — that's how we found `lower`
   vs `urlize`.

5. **Heredoc safety:** when writing files via `cat > file << EOF` and the content
   contains `$` or backticks (Hugo templates `$var`, SVG, JS), **quote the
   delimiter**: `<< 'EOF'`. Unquoted, bash expands `$opts` etc. and corrupts the
   file. When in doubt, tell the user to use an editor (`nano`) instead.

6. **Encoding:** use escape sequences, not literal special characters, in generated
   files — `\u2014` not a literal em dash, `\2014` in CSS `content`. Literal
   curly quotes / dashes have shown up as mojibake (`â€"`) after editor round-trips.

---

## How things are architected (so new work fits the patterns)

- **Callouts** are variable-driven: each alert type just remaps three CSS custom
  properties (`--callout-border/bg/fg`) that a single base `blockquote` rule reads.
  Add a type by adding an icon to the render hook's `$icons` dict, a color block in
  `callouts.css`, and one mapping line. The designator (`[!FOO]`) lowercases to the
  `AlertType`, which keys the class `callout-foo` and everything else.
- **One accent color** drives the whole site: `--accent` in `custom.css` §1. Reuse
  it (`var(--accent)`) for anything new rather than hardcoding a hex.
- **`custom.css` is organized into 13 numbered sections (§0–§12)** — add new rules
  to the matching section, keep the `prefers-reduced-motion` block last.
- **CSS variables must be defined before use** in the cascade; keep the `:root`
  token block at the top. Only custom-property declarations belong inside the
  `:root` / `.dark` blocks — a style rule (selector) pasted inside them is a bug,
  even if native CSS nesting makes it *appear* to work.
- **`--code-bg` is a multi-consumer token — don't repurpose it.** It drives inline
  code, but PaperMod *also* uses it for list-page backgrounds
  (`.list { background: var(--code-bg) }`) and the site uses it for the series-nav
  box. To restyle inline code, target `.post-content :not(pre) > code` (§4)
  instead of redefining the token, or you'll accidentally recolor `/posts/` and
  every taxonomy page.
- **Images** flow through `figure.html`, which branches by type: **SVG** served
  as-is (never call `.Width`/`.Resize` on a vector — it errors), **PNG/JPEG ≥640px**
  gets WebP + responsive srcset, everything else served as-is. All branches emit
  `data-full` (the original) for the lightbox. The lightbox JS in `extend_footer.html`
  reads `data-full` first for full-res zoom and builds the "Download full image"
  link. New image features usually touch both files; SVGs also need an explicit
  width in the lightbox CSS (`img[src$=".svg"]`) or they render at zero size.
- **Page-level JS** all lives in `extend_footer.html`, gated to `.IsPage`, each
  feature in its own IIFE. `<head>` additions go in `extend_head.html`.

---

## Ordering & sorting (a recurring source of confusion)

- **`weight`** is Hugo's *global* sort key — it affects `/posts/`, tags, everything.
  Unset = sort by date. Only set it to **pin** a post. Do **not** blanket-set it.
- **Series order** uses a dedicated `series_order: N` front-matter field, read only
  by `series-nav.html` via `.ByParam "series_order"`. This is intentionally
  separate from `weight` so series order can't disturb the post feed. Use this
  pattern generally: if you need to order something in one place without affecting
  another, use a custom param, not `weight`.
- **Summaries** follow a precedence chain: a *manual* summary (`<!--more-->`
  divider in the body) outranks a front-matter `summary:`, which outranks Hugo's
  *automatic* first-70-words summary. The site standard is the `summary:` field for
  `/posts/` excerpts — so a stray `<!--more-->` **silently overrides it**, and the
  card falls back to body content that reads like an auto summary. This was the
  exact cause of a "why is only this one post's summary auto-generated?" report. If
  a post's excerpt ignores its `summary:`, `grep` the file for `<!--more-->` first.

---

## Deploy & verify checklist

1. Make the change in the correct site-level file.
2. If the change involves a heredoc with `$`/backticks, quote the delimiter.
3. Run `./hostinger-deploy.sh` (builds + rsyncs). Watch the `hugo` output for
   ERROR/WARN.
4. Verify on the live site: view-source or inspect the specific element. For CSS,
   confirm the fingerprinted stylesheet filename changed. For favicons/images,
   test in a private window (caching).
5. If it "didn't work," walk rule #3 above before touching the code again.

---

## Things the user tends to want, and where they go

- New callout type → `render-blockquote.html` + `callouts.css`
- Styling tweak → `custom.css` (find the right numbered section)
- New JS behavior on posts → `extend_footer.html` (new IIFE, inside `.IsPage`)
- Something in `<head>` → `extend_head.html`
- Image behavior → `figure.html` (branch by type — don't resize SVGs) + lightbox JS in `extend_footer.html`
- Config toggles / PaperMod params → `hugo.yaml` (mind YAML indentation; the
  `params.assets` sub-block must come after top-level params)
- New quote on the 404 → `data/quotes.yaml`

---

## Tone / working style that worked well

- Explain the *why* behind a fix, not just the fix. The user retains it and it
  builds their mental model.
- When multiple files are involved, say explicitly which file each edit goes in.
- Flag tradeoffs honestly (e.g. "this overrides a theme file you'll then maintain,"
  or "the original PNG download is big by design").
- One change at a time when debugging; deploy and confirm between steps rather than
  batching risky edits.
- Don't over-claim success — give the user a concrete thing to verify (inspect this
  element, check this attribute) so they can confirm it actually worked.
