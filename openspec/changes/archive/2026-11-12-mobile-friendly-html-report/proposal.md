# Proposal

## Why

The HTML readout is hard to read on a phone: the page renders zoomed out with tiny text because it has no viewport declaration, and the up/down value-diff arrows (U+2B9D / U+2B9F) show as missing-glyph boxes on mobile WebKit (iOS Safari). The readout is mainly consumed on a phone, so both need fixing.

## What Changes

- Add a `viewport` meta tag so mobile browsers lay the page out at device width instead of a ~980px virtual width, making text readable at normal size.
- Add a mobile media query that tightens page padding and table cell padding/font size so the wide table scrolls horizontally in its existing scroll wrapper rather than shrinking the page.
- Replace the arrow glyphs U+2B9D / U+2B9F with characters that render on mobile WebKit (`▲` U+25B2 / `▼` U+25BC), keeping the existing three-tier scheme (colored strong arrow, plain arrow, `^` / `v`).

## Capabilities

### New Capabilities
- `html-readout`: how the generated HTML readout is presented, covering mobile-friendly layout and the direction indicators used in the table.

### Modified Capabilities

## Impact

- `html_util.py`: head markup and stylesheet.
- `pickem_plug.py`: the three `get_*_display_arrow` helpers use the new glyphs, so console output and CSV change too (CSV values containing the glyph change from ⮝/⮟ to ▲/▼).
- No new dependencies, no Lambda/config changes. README mentions the HTML readout only generally; no update needed.
