# natebent.com — Customization Reference

A catalog of every customization made on top of the stock Hugo + PaperMod setup.
Everything here lives at the **site level** (not in `themes/hugo-PaperMod/`), so it
survives theme updates. If something breaks after a PaperMod update, this is the
list of things to re-check.

**Stack:** Hugo (extended) + PaperMod theme, deployed to Hostinger via
`hostinger-deploy.sh` (`hugo` build + `rsync --delete` over SSH).

---

## Golden rules (learned the hard way)

- **Never edit files under `themes/hugo-PaperMod/`.** All overrides go in the
  site-level `layouts/`, `assets/`, `static/`, `data/` directories. A file at the
  same relative path in the site root overrides the theme's copy.
- **Hugo version matters.** Site uses features requiring a recent Hugo (0.146+ for
  `layouts/_markup/` render hooks). The distro `apt` package is often too old —
  install via snap or pin a known-good version. A too-old Hugo *silently* falls
  back to defaults with no error.
- **What you see live is the deployed build**, not a local server. After any change,
  run the deploy script; confirm changes by checking the fingerprinted CSS filename
  changes or by view-source.
- **`.Site.Taxonomies` is keyed by `lower`, not `urlize`.** ("Proxmox SDN" → key
  `proxmox sdn`, with a space — not `proxmox-sdn`.)
- **`weight` is a global sort override.** Unset = sort by date. Only set it to *pin*
  a specific post. Don't put `weight: 1` on everything.
- **Heredocs:** quote the delimiter (`<< 'EOF'`) when the content contains `$` or
  backticks (Hugo templates, SVG), or bash will mangle it.
- **SVGs are not rasters.** They have no intrinsic pixel dimensions, so `.Width`/
  `.Resize` error on them — the figure shortcode branches on `MediaType.SubType
  "svg"` and serves them untouched. In the lightbox they need an explicit width
  (`img[src$=".svg"]`) or they collapse to zero size.

---

## Files touched

### Layouts — render hooks

| File | Purpose |
|------|---------|
| `layouts/_markup/render-blockquote.html` | Typed callouts (GitHub-style alerts). Turns `> [!NOTE]`, `[!TIP]`, `[!WARNING]`, `[!CAUTION]`, `[!IMPORTANT]`, plus custom `[!INSIGHT]` and `[!QUOTE]` into styled, icon-labeled boxes. `[!QUOTE]` uses the alert title slot for attribution. |
| `layouts/_markup/render-codeblock.html` | Code-block language labels. Wraps Hugo's default highlight output in `.code-wrap[data-lang]` so a language tag shows top-right; preserves PaperMod's copy button. |

### Layouts — templates & partials

| File | Purpose |
|------|---------|
| `layouts/_default/single.html` | Copied from theme; added one line — `{{ partial "series-nav.html" . }}` — at the top of `.post-content`. |
| `layouts/_default/rss.xml` | Full-content RSS. Swaps `.Summary` → `.Content` so feed readers get whole posts. Also uses `site.Language.Locale` (not the deprecated `LanguageCode`). |
| `layouts/404.html` | Custom 404 page. Accent "404", a quip, and a randomly-rotating quote pulled from `data/quotes.yaml` via JS on each page load. |
| `layouts/partials/series-nav.html` | Series navigation box. Reads a post's `series` taxonomy, lists all parts ordered by the custom `series_order` front-matter field (falls back to date), marks the current one. Looks up taxonomy with `lower`. |
| `layouts/partials/extend_head.html` | Light/dark favicon `<link>`s that follow `prefers-color-scheme`. |
| `layouts/partials/extend_footer.html` | All the page-level JS: reading-progress bar, scroll-tracking TOC highlight, and the image lightbox. Lightbox opens the full-resolution original (reads `data-full` first, falls back to `currentSrc`/`src`), shows the figure caption, has a "Download full image" link (with `stopPropagation` so it doesn't close the box), closes on click or Esc, and locks background scroll. Gated to `.IsPage`. |
| `layouts/partials/cover.html` | Copied from theme; the `<figure>` line stamps extra classes — `entry-cover-list` on list pages and `entry-cover-thumb` when a post sets `cover.thumb: true` — to drive the two cover styles. |

### Shortcodes

| File | Purpose |
|------|---------|
| `layouts/_shortcodes/figure.html` | Image handling. Bundled page-resource images with three branches: **SVG** (served as-is, no resize/width — vectors have no pixel dimensions and `.Width` errors on them); **PNG/JPEG ≥640px** (build-time WebP + responsive srcset at 640/1024/1600, auto width/height for no layout shift); and **small/other raster** (served as-is). All branches add a `data-full` attribute pointing at the original for the lightbox, plus lazy loading and a build-time error if the image path is wrong. |

### Assets — CSS

| File | Purpose |
|------|---------|
| `assets/css/extended/callouts.css` | The callout/alert color system: per-type CSS variables (light + dark), base blockquote styling, the icon/label title row, quote-specific italic + citation styling, list spacing inside callouts. |
| `assets/css/extended/custom.css` | Everything else, organized into 11 labeled sections: design tokens (`--accent`, `--main-width`, `--measure`), typography (narrow-prose/wide-media, accent headings, text-wrap, tabular tables), media (image borders/shadows, lightbox at 98vw/98vh, an SVG-specific lightbox rule via `img[src$=".svg"]` since vectors have no intrinsic size, and `.lightbox-download` link styling), code-block labels, reading aids (progress bar, TOC), post-list cards (hover lift), cover images (list/thumbnail/single), nav + tags (animated underline), profile/landing page, misc embeds, and a site-wide `prefers-reduced-motion` guard (kept last). |

### Static & data

| File | Purpose |
|------|---------|
| `static/favicon-light.png`, `static/favicon-dark.png` | Light/dark favicons (referenced by `hugo.yaml` assets block + `extend_head.html`). |
| `static/.htaccess` | `ErrorDocument 404 /404.html` — tells Hostinger's Apache/LiteSpeed to serve the custom 404 for missing URLs. |
| `static/files/CVs/Resume.pdf` | Resume (moved here from `public/` so it's version-controlled and survives clean builds). |
| `data/quotes.yaml` | Quote pool for the 404 page. Each entry: `text` + optional `source`. |

### Config

| File | Changes |
|------|---------|
| `hugo.yaml` | Favicon assets block (light PNG for all icon slots); `minifyOutput: true`; `pagination: pagerSize: 10`; `ShowWordCount: true`; `editPost` "Suggest changes" links; Search menu entry (needs `content/search.md`); `languageName` → `label`. |

### Content conventions

| Front-matter key | Effect |
|------------------|--------|
| `series: ["Name"]` | Puts the post in a series (drives `/series/` pages + the series-nav box). Must be a list. |
| `series_order: N` | Orders posts within the series-nav box, independent of date or `weight`. |
| `cover.image` / `cover.thumb: true` / `cover.relative: true` | Cover image (bundle-relative); `thumb: true` renders the small left-of-title thumbnail style. |
| `weight` | **Leave unset normally** (sorts by date). Set only to pin a post to the top of the feed. |

---

## Feature → file quick index

- **Callouts / alerts** → `render-blockquote.html` + `callouts.css`
- **Code language labels** → `render-codeblock.html` + `custom.css` (§4)
- **Reading progress / TOC highlight** → `extend_footer.html` + `custom.css` (§5)
- **Image lightbox / full-res zoom / download link** → `extend_footer.html` + `figure.html` + `custom.css`
- **WebP / responsive images** → `figure.html` (PNG/JPEG branch)
- **SVG diagrams** (render + zoom) → `figure.html` (SVG branch) + `custom.css` (`img[src$=".svg"]` lightbox rule)
- **Cover thumbnails** → `cover.html` + `custom.css` (§7)
- **Series navigation** → `series-nav.html` + `single.html` + `custom.css`
- **Favicons (light/dark)** → `hugo.yaml` + `extend_head.html` + `static/`
- **Custom 404 + quotes** → `layouts/404.html` + `data/quotes.yaml` + `static/.htaccess`
- **Full-content RSS** → `rss.xml`
- **Accent color / layout width** → `custom.css` (§1 design tokens: `--accent`, `--main-width`, `--measure`)
