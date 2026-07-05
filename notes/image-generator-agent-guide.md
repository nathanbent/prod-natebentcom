# Blog Image Guide - natebent.com

How the post SVGs are built: colors, fonts, structure, dark mode, and the
sanitization checklist. Companion to `COLOR-REFERENCE.md`. Written 2026-07-05.

Applies to: `vxlan-terraform-hero-v2.svg`, `vxlan-terraform-resource-detail-v2.svg`,
and any future diagram made the same way.

---

## The approach in one paragraph

Images are hand-written standalone SVGs, not raster exports. All color lives
in a `<style>` block using class names, with a `@media (prefers-color-scheme:
dark)` block that re-declares the same classes with the dark palette. Every
color is a hex pulled straight from the site's design tokens in
COLOR-REFERENCE.md, so the images read as part of the site rather than pasted
into it. Text uses Rubik for titles/labels (weight 500) and Karla for
subtitles and captions (weight 400), matching the site typography.

---

## Colors

Only hexes from the color reference are used. The mapping:

| Image role                        | Light hex | Dark hex  | Site token         |
|-----------------------------------|-----------|-----------|--------------------|
| Primary accent (strokes, FGT fill, tunnel, dep arrows) | `#1B5A7A` | `#7FB3D6` | `--accent`         |
| Page-tone fills (map box, pills)  | `#E9EFF3` | `#12161B` | `--theme`          |
| Card fills (containers, PVE card) | `#FFFFFF` | `#242D38` | `--entry`          |
| Strong text                       | `#1C2733` | `#D8DFE6` | `--primary`        |
| Muted text / gray arrows          | `#5A6B79` | `#92A0AD` | `--secondary`      |
| FortiGate resource fill           | `#E6F1FB` | `#1A2733` | blue-50 tint (custom, dark is a blue-black blend) |
| FortiGate resource text           | `#0C447C` / `#185FA5` | `#B5D4F4` / `#85B7EB` | blue-800/600, blue-100/200 |
| Proxmox resource fill             | `#F1EFE8` | `#242D38` | warm gray-50 / `--entry` |
| Proxmox resource text             | `#2C2C2A` / `#5F5E5A` | `#D3D1C7` / `#B4B2A9` | gray-900/600, gray-100/200 |
| Text on the solid blue FGT card   | `#E9EFF3` / `#B5D4F4` | `#12161B` / `#0C447C` | theme + blue-100 (dark inverts) |

Rules carried over from the color reference:

1. The accent blue leads. FortiGate objects, the overlay tunnel, and
   dependency arrows all take `--accent`; Proxmox side stays neutral so the
   two platforms are visually distinct without introducing a second accent.
2. The racing green (`--accent-2`) is NOT used in diagrams. It stays scoped
   to the INSIGHT callout per the color reference. Do not "add some green
   for variety."
3. Text on a colored fill uses a darker/lighter stop of the same hue, never
   plain black or generic gray (e.g. blue-800 `#0C447C` on blue-50 `#E6F1FB`).
4. When a box has a title and a subtitle, they use two different stops -
   title darker, subtitle one step lighter. Weight alone doesn't separate
   them.
5. Never hardcode a new blue. If a shade is needed, pick from the blue ramp
   already in the images or derive from `--accent` the same way the site
   does (lighter + desaturated for dark mode, never just the light hex).

## Fonts

```css
@import url('https://fonts.googleapis.com/css2?family=Karla:wght@400;500&family=Rubik:wght@400;500&display=swap');
.h{font-family:'Rubik','Segoe UI',Helvetica,Arial,sans-serif;}  /* titles, labels, weight 500 */
.b{font-family:'Karla','Segoe UI',Helvetica,Arial,sans-serif;}  /* subtitles, captions, weight 400 */
```

Sizes: 14-15px for titles/labels, 12px for subtitles and captions, 11px
floor (segment pills). Two weights only, 400 and 500.

**The `<img>` caveat, important.** How the font actually loads depends on
how the SVG reaches the page:

- **Inlined into the HTML** (Hugo shortcode/partial that emits the raw
  `<svg>`): the `@import` works, and if the site already loads Karla/Rubik
  the fonts are cached anyway. This is the recommended path.
- **Referenced via `<img src="...svg">` or Markdown `![]()`**: browsers
  block external resource loads inside image-context SVGs. The `@import`
  silently fails and text falls back to the system sans stack. If `<img>`
  usage is required and the fonts must render, either (a) convert text to
  paths (Inkscape: Path > Object to Path - loses editability and a11y), or
  (b) embed the fonts as base64 `@font-face` data URIs inside the SVG
  (bloats the file ~30-60 KB per weight). Usually the fallback stack is
  acceptable and neither is worth it.

Estimating text width when laying out: at 14px, roughly 8px per character
for weight 500, 7px for weight 400. Box width = longest label x per-char
width + 24px padding minimum. Karla runs slightly narrower than this
estimate, so it errs safe.

## Dark mode

The files use `@media (prefers-color-scheme: dark)`, which follows the OS
setting. **PaperMod's theme toggle does not change `prefers-color-scheme`** -
it toggles a `.dark` class on `<body>`. So:

- As `<img>`: only the OS preference can apply. A reader on a light OS who
  toggles the site dark gets a light image on a dark page. Acceptable but
  visible, especially since the image fills are tied to `--theme`/`--entry`.
- Inlined: replace the media query with descendant selectors so the image
  tracks the site toggle exactly:

```css
/* instead of @media (prefers-color-scheme: dark){ .mapbox{...} } */
body.dark .mapbox{fill:#242D38;stroke:#7FB3D6;}
body.dark .map-title{fill:#7FB3D6;}
/* ...same substitution for every class in the dark block */
```

Better still, when inlining, swap the hardcoded hexes for the site's actual
custom properties (`fill:var(--accent)`) and delete the dark block entirely -
the site variables already flip. The hardcoded version exists so the file is
self-contained and portable (RSS readers, direct file opens, social embeds).

## Structure conventions

- `viewBox="0 0 680 H"`, width fixed at 680, height sized to content plus
  ~30px bottom padding. Content stays inside x=40..640 except deliberate
  center-outs.
- `role="img"` on the root plus `<title>` and `<desc>` as the first
  children. Screen readers announce these; they also serve as the
  image's self-documentation.
- One shared arrowhead in `<defs>` using `stroke="context-stroke"`, so
  every arrow's head inherits its line color automatically.
- **Unique marker IDs per file** (`hero-arrow`, `detail-arrow`). If two
  inlined SVGs on one page both define `id="arrow"`, the browser resolves
  `url(#arrow)` against the first one only - arrowheads render in the wrong
  color or not at all. Prefix every `id` with the image name.
- Connector `<path>`/`<line>` elements always carry `fill="none"` (SVG
  defaults paths to black fill; a curved connector without it renders as a
  filled blob).
- `dominant-baseline="central"` + y at slot center for vertically centered
  text; `text-anchor="middle"` + x at box center horizontally.
- Strokes: 1px for boxes, 0.75px for small pills, 1.5px for the emphasized
  tunnel. Dashes: `4 3` for logical containers, `5 5` for the overlay.

## Sanitization checklist

Run before publishing any SVG, especially anything touched by external
tooling or destined to be inlined:

1. **No `<script>` elements, no `on*=` event attributes** (onclick,
   onload, onmouseover...). Inlined SVG executes in the page context;
   this is the XSS surface.
2. **No `<foreignObject>`.** It embeds arbitrary HTML.
3. **No external references except the intended font `@import`**: no
   `<image href>`, no `<use href>` pointing off-site, no `url()` in styles
   fetching remote resources. For strict-CSP contexts, delete the
   `@import` too and rely on the fallback stack.
4. **`xmlns="http://www.w3.org/2000/svg"` present on the root.** Required
   for `<img>`/standalone use; harmless when inlined. Note the `&` in the
   Google Fonts URL must be `&amp;` in a standalone XML file.
5. **No editor metadata.** Inkscape/Illustrator exports carry
   `sodipodi:`/`inkscape:` namespaces, `<metadata>`, and embedded thumbnails.
   Strip with svgo: `npx svgo --multipass file.svg`. If running svgo on
   these hand-written files, keep `<title>`/`<desc>` and the `<style>`
   block: disable the `removeTitle`, `removeDesc`, and `inlineStyles`/
   `minifyStyles` merging of media queries if it mangles the dark block
   (verify dark mode still works after optimizing).
6. **Unique IDs across the page** (see structure conventions). Grep each
   file's `id=` values before inlining two on one post.
7. **ASCII-safe text.** No literal em dashes or exotic Unicode in labels
   (mirrors the site's encoding rule); hyphens and plain punctuation only.
8. Quick visual QA in both modes: open the file directly in a browser,
   toggle OS dark mode (or DevTools > Rendering > emulate
   prefers-color-scheme), confirm every text element stays readable and no
   fill goes invisible.

## Reproducing / making the next one

1. Start from one of the v2 files as a template - the style block and defs
   are the reusable part.
2. Sketch the layout math first: box widths from longest label, 60px+
   between sibling boxes, 20px+ padding inside containers, arrows never
   crossing unrelated boxes.
3. Assign colors by meaning: accent blue = FortiGate/the site's "main
   thread," neutral gray/white = Proxmox/structure, and keep it to those
   two families per diagram.
4. Write the light palette, then derive dark the site's way: backgrounds to
   `--theme`/`--entry` dark values, accents to the moonlit variants,
   text stops flipped (800->100, 600->200).
5. Run the sanitization checklist, view in both modes, ship.
