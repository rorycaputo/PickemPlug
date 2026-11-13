## 1. Mobile layout

- [x] 1.1 In `html_util.build_html`, add `<meta name="viewport" content="width=device-width, initial-scale=1">` to the head
- [x] 1.2 Add an `@media (max-width: 600px)` block to the inline stylesheet reducing body padding, table cell padding/font size and heading sizes

## 2. Arrow glyphs

- [x] 2.1 In `pickem_plug.py`, define shared up/down glyph constants (`▲` U+25B2, `▼` U+25BC) and use them in `get_spread_display_arrow`, `get_odds_display_arrow` and `get_cents_display_arrow` in place of `⮝` / `⮟` / `⮟`

## 3. Verification

- [x] 3.1 Run the app and confirm `out/readout.html` has the viewport meta, the media query, and `▲`/`▼` with no U+2B9D/U+2B9F
- [x] 3.2 Open the readout in a ~390px-wide emulated viewport and confirm text is legible at native size and the table scrolls sideways within its wrapper; confirm desktop width looks unchanged
- [ ] 3.3 Run the existing tests (`pipenv run pytest`) and confirm they pass
