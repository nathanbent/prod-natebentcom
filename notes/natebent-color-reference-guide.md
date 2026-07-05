# Color Reference - natebent.com

The site palette, where each color is used, and the reasoning behind the
decisions. Companion to `CUSTOMIZATIONS.md`. Last updated: 2026-07-04.

Files that define color: `assets/css/extended/custom.css` (sec 1, design
tokens) and `assets/css/extended/callouts.css` (callout palette).

---

## The system in one paragraph

Two accents with a clear hierarchy: **ocean blue leads, racing green is
scoped**. The blue (`--accent`) drives everything structural - links,
headings, nav underline, tags, TOC highlight. The green (`--accent-2`)
appears only in a small number of deliberate places (currently: the
INSIGHT callout). All neutrals are tinted a few degrees toward the blue's
hue rather than being pure gray - individually imperceptible, but it is
why the palette reads as designed instead of "PaperMod with a blue link."
Dark mode flips both accents lighter and desaturated (same hue family,
"moonlit" versions) because saturated dark colors vibrate and vanish on
dark backgrounds.

---

## Accents

| Token        | Light     | Dark      | Meaning              |
|--------------|-----------|-----------|----------------------|
| `--accent`   | `#1B5A7A` | `#7FB3D6` | Maine Atlantic blue  |
| `--accent-2` | `#235B41` | `#7FBFA0` | British Racing Green |

Contrast (WCAG: 4.5:1 = AA, 7:1 = AAA), all approximate:

- `#1B5A7A` on white entries: ~7.5:1. On the `#E9EFF3` page: ~6.5:1.
- `#7FB3D6` on the `#12161B` page: ~8:1.
- `#235B41` on white: ~8:1.  `#7FBFA0` on `#12161B`: ~8:1.

All pass AA comfortably; most pass AAA. This is why the light-mode blue is
darker/grayer than a typical "nice blue" swatch - the depth is what buys
both the cold-Atlantic character and the contrast.

### Usage rules (the decisions)

1. **One accent drives the site.** Anything new that needs "the site
   color" uses `var(--accent)`. Never hardcode the hex in new rules.
2. **The green is scoped, not co-equal.** Two accents used everywhere
   reads as indecision. `--accent-2` gets at most 2-3 deliberate homes.
   Current canonical home: the `[!INSIGHT]` callout (wired directly to
   `var(--accent-2)` in callouts.css). Candidates on the shelf if more
   are ever wanted: `::selection`, link `:hover`, the reading-progress
   bar. Do not use it for structural elements (nav, headings, tags).
3. **Dark accents are lighter + desaturated, never just "the light hex."**
   If a new color is added, make a dark variant the same way.
4. **Tuning knob is saturation, not lightness.** If the blue ever feels
   too gray in practice, try `#155E85` before anything lighter.

### Shelf snippet: selection in green (not currently applied)

```css
::selection       { background: #D8EBE0; color: #173D2C; }
.dark ::selection { background: #24483A; color: #B9E0CB; }
```

Goes in custom.css sec 1 if adopted.

---

## Neutrals (custom.css sec 1)

All tinted toward the blue (hue ~207). The "personal touch" lives here.

| Token             | Light     | Dark      | Role / notes                                    |
|-------------------|-----------|-----------|-------------------------------------------------|
| `--theme`         | `#E9EFF3` | `#12161B` | Page canvas. Light = soft blue-gray paper.       |
| `--entry`         | `#FFFFFF` | `#242D38` | Cards. Lifted off the page in both modes.        |
| `--primary`       | `#1C2733` | `#D8DFE6` | Strong text. Blue-black, not neutral gray.       |
| `--secondary`     | `#5A6B79` | `#92A0AD` | Muted text (meta, dates). Cool slate.            |
| `--tertiary`      | `#C9D4DD` | `#3B4652` | Faint UI (dividers, disabled).                   |
| `--content`       | `#232E3A` | `#C4CDD6` | Body prose.                                      |
| `--code-block-bg` | `#1B222B` | `#242D38` | Fenced code. Dark blue-slate in both modes.      |
| `--code-bg`       | `#F1F5F8` | `#2F3A47` | Inline code. Faint blue wash.                    |
| `--border`        | `#D9E2EA` | `#333F4C` | Hairlines. One step darker than default so cards |
|                   |           |           | still read against the tinted page.              |

### Surface decision (why theme != entry)

- Light mode: the page is deliberately darker than the cards (~15-18% mix
  toward the slate), so white entries float. Side effect: post prose sits
  on the blue-gray page, not white (PaperMod renders post content on
  `--theme`). Accepted as a feature - softer reading background. If a
  stronger page tone is ever wanted, next step down is `#DEE7ED`.
- Dark mode: page dropped ~20% (`#171C22` -> `#12161B`), cards raised
  ~12% (`#202730` -> `#242D38`) for the same separation.
- Screenshots/diagrams with white backgrounds show their edges against
  the tinted page. Fine because figures already get borders/shadows
  (custom.css sec 3).

---

## Callouts (callouts.css)

| Type              | Light                    | Dark                     | Note                            |
|-------------------|--------------------------|--------------------------|---------------------------------|
| default + NOTE    | `var(--accent)`          | `var(--accent)`          | Tracks the site blue.           |
| TIP               | `#8FD4CA` (fg `#14685E`) | `#9BDCD2`                | Pastel teal - see note.         |
| IMPORTANT         | `#8a63d2` (fg `#7b54c8`) | `#b294e8`                | Purple, unchanged from v1.      |
| WARNING           | `#d1a017` (fg `#9c7400`) | `#e3b341`                | Amber, unchanged.               |
| CAUTION           | `#d1453b` (fg `#c23730`) | `#f0857d`                | Red, unchanged.                 |
| INSIGHT           | `var(--accent-2)`        | `var(--accent-2)`        | THE home of the racing green.   |
| QUOTE             | `#A7B3BD` border         | `#46525E` border         | Cool gray, fg = `--secondary`.  |

Background tints: light mode ~7% of the color (tip 12% since pastels need
more presence, warn 10%, imp/caut 8%, quote 6%), dark mode ~10-12%.

Callout reasoning:

- NOTE took the accent so the most common callout reinforces the site
  color instead of introducing a third blue.
- INSIGHT (the signature custom type, used often) owns the green.
- TIP is pastel teal: pastel treatment (user preference - a light, soft
  border that pops against deep-bordered callouts) on the teal hue. A
  pastel BLUE was tried first and reverted: NOTE vs TIP separated only
  by lightness was hard to tell apart in practice, because value
  differences compress under screen brightness, warm/night modes, and
  weaker panels, while hue differences survive them. Lesson recorded:
  when two callouts must be distinguishable, separate them by hue, not
  just lightness. The light-mode fg is NOT the pastel - pastel text on
  white fails contrast (same failure as the v0 accent) - so the title
  uses deep teal `#14685E` (~6:1, AA) while border/tint stay pastel.
  Dark mode uses the pastel for both (light-on-dark contrast is fine).
- IMPORTANT/WARNING/CAUTION kept their v1 colors deliberately - purple,
  amber, and red are not part of the blue/green story and already worked.

### Maintenance gotchas (do not "fix" these)

1. **NOTE and INSIGHT use `var()` + `color-mix()`.** Changing `--accent`
   or `--accent-2` in custom.css sec 1 updates these callouts for free.
   `color-mix()` is Baseline in evergreen browsers since mid-2023; a very
   old browser loses only the background tint (border + text still work).
2. **The var-based lines are declared identically in both `:root` and
   `.dark` on purpose.** Custom properties resolve their `var()` refs
   where DECLARED. `:root` is `<html>`, but PaperMod puts `.dark` on
   `<body>` - so without the `.dark` re-declaration, dark mode would
   inherit the frozen light-mode accent. Deduplicating those lines is
   the bug, not the fix.
3. **Declaration order across files does not matter** for these vars.
   Hugo concatenates `assets/css/extended/` alphabetically (callouts.css
   before custom.css), but custom-property references resolve at
   computed-value time, not source order, so callouts.css may reference
   `--accent` before custom.css defines it.
4. **Encoding:** the QUOTE attribution dash is `content: "\2014\00a0"`
   (escaped em dash + no-break space). The `\00a0` matters twice over:
   CSS eats one plain space after a hex escape as the terminator, and
   the no-break space keeps the dash glued to the name across wraps.
   Never replace with a literal em dash (mojibake risk, see agent guide
   rule 6).

---

## History / superseded values

- v0 accent: `#748CAB` light / `#8fa8c9` dark. Replaced 2026-07: too
  pastel to carry link text (~3.4:1 on white, below AA).
- v1 surfaces: `--theme` white / `#171C22`, `--entry` white / `#202730`,
  border `#E2E9EF` / `#2C3641`. Replaced same session by the darker-page
  / lighter-card values above.
- v1 INSIGHT was teal `#2a9d8f` / `#4fd1c5`.
- v2 TIP was deep teal `#1A7A6E` (fg `#14685E`) / `#5FC5B8`. Replaced
  by pastel sky blue (user preference for a pastel).
- v3 TIP was pastel sky blue `#93C6E8` (fg `#1873A8`) / `#A8D4F0`.
  Reverted same session: two blue-family callouts separated only by
  lightness were hard to tell apart in practice. Current TIP keeps the
  pastel treatment but on the teal hue, so teal is in use again.
