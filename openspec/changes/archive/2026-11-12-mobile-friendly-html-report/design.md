# Design

## Context

`html_util.build_html` builds the page with lxml: `<head>` has only a charset meta, title and an inline `<style>`. Body padding is a fixed `2rem`, the table uses `white-space: pre` with `6px 10px` cell padding inside a `.table-scroll` wrapper (`overflow-x: auto`). Without a viewport meta, mobile browsers use a ~980px layout viewport and scale the page down, which causes the "zoomed out" look.

The arrows come from `get_spread_display_arrow`, `get_odds_display_arrow` and `get_cents_display_arrow` in `pickem_plug.py` (only the cents one is currently active; the others are commented out at call sites). They emit U+2B9D / U+2B9F, in ANSI green/red for the strong tier, which flow through the CSV into the HTML via the ANSI-to-span conversion.

## Goals / Non-Goals

**Goals:**
- Readable text at native size on phones, with the table scrolling sideways in its wrapper.
- Direction indicators that render on iOS Safari.

**Non-Goals:**
- Restructuring the table (stacked/card layout), hiding columns, or changing the dark theme.
- Changing tier thresholds or the CSV column layout.

## Decisions

1. **Viewport meta `width=device-width, initial-scale=1`** added in `build_html`'s head. This alone fixes the zoomed-out layout; the table stays wide and scrolls inside `.table-scroll`.
2. **`@media (max-width: 600px)` block** in the inline stylesheet: body padding `0.75rem`, cell padding `4px 6px`, table font size slightly smaller, headings scaled down. Desktop styles are untouched. Alternative considered: a fluid font size everywhere; rejected as it risks changing the desktop look.
3. **Arrow glyphs `▲` (U+25B2) / `▼` (U+25BC)** replace U+2B9D / U+2B9F. U+2B9x is from the Supplemental Arrows-C block that iOS system fonts lack; the geometric-shapes triangles are widely supported and not emoji-presented by default. Alternatives: ASCII `^`/`v` for all tiers (loses the tier distinction), or CSS-drawn arrows (more machinery than needed). The `^` / `v` slight tier already exists and stays.
4. **Change at the source (`pickem_plug.py`)** so console, CSV and HTML are consistent, as a single shared constant per direction rather than repeated `⮝` literals in three functions.
5. **No legacy-glyph substitution.** Old saved CSVs keep their U+2B9D/U+2B9F; HTML rebuilt from them will still show the old arrows. Accepted, since only new runs matter.

## Risks / Trade-offs

- Console users on terminals that rendered the old arrows now see triangles; triangles are broadly supported, so low risk.
- Saved CSVs gain a mixed glyph history; harmless as only display is affected.
- Cannot be verified on a real iPhone from this environment; verification uses a narrow-viewport browser emulation and inspecting the generated markup.
