# Tasks

## 1. HTTP core in `apis.py`

- [x] 1.1 Add `FIREFOX_VERSION` / `FIREFOX_UA` (Firefox 159), `BROWSER_HEADERS` and `NAVIGATION_HEADERS` as in design Decision 1, and delete the old module-level `headers` dict and its commented `Cookie` line. Verify: `grep -n "rv:1[0-9][0-9]" src` shows the version only in `apis.py`.
- [x] 1.2 Add `new_session()`, `DEFAULT_TIMEOUT = 30`, `log_cache_headers(response)` and `get(session, url, *, headers, params, timeout)`, which logs and then raises on error status (Decision 3). Remove `call_get_api`, `call_get_api_with_session` and `call_post_api`. Verify: `python -c "import sys; sys.path.insert(0,'src'); import apis"` succeeds, and `grep -n "requests.Session()" src/apis.py` shows it only inside `new_session`.
- [x] 1.3 Comment out `pickem_login_post`, replacing the captured `Cookie`, `Next-Action`, `ACTION_KEY` and action id values with `<captured value>` (Decision 7). Verify: `grep -n "_swb_consent_\|601c2c81\|k5351b50c" src` returns nothing.

## 2. Pickem

- [x] 2.1 In `fetch_pickem_html_with_session`, build the session with `apis.new_session()`, seed the saved cookies, send the pool request with `apis.get(..., headers=apis.NAVIGATION_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)`, and catch `requests.RequestException` â†’ return `None` in place of the `isinstance(result, tuple)` check. Verify: a local run with `--no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark` reads spreads from the saved session, and the log shows one cache line for `picks.cbssports.com`.
- [x] 2.2 Verify the fallback path still triggers: temporarily point the call at an invalid host (or disconnect the network), run the Pickem-only command, and confirm it prints `Falling back to browser login` instead of raising. Revert the temporary change.

## 3. DraftKings

- [x] 3.1 Add `DK_FALLBACK_CLIENT_VERSION = '2646.5.2'` and `get_client_version(session)`: a GET of the NFL league page with `NAVIGATION_HEADERS`, the `window.sbwebversion` regex, a comment saying the request isn't strictly necessary, and on `RequestException` or no match a printed fallback message (Decision 5). Verify: a DraftKings-only local run (`--no-fetch-pickem --no-fetch-espnbet --no-fetch-oddshark`) logs the scraped version, with no fallback message.
- [x] 3.2 Update `lines_url` to `templateVars=88808`, and rebuild the markets headers from the 2026-11-14 capture: version in `X-Client-Version` and `x-pe-cv`, widget `3.3.0`, the `x-pe-*` set, the browser's `content-type`, and no `Pragma` / `Cache-Control` / `TE` / trace headers. Wrap the fetch in one `with apis.new_session()` block. Verify: the DraftKings-only run produces lines, and the cache log shows `public,max-age=1` (or similar) for `sportsbook-nash.draftkings.com`.
- [x] 3.3 Verify the fallback: temporarily break the regex, run DraftKings only, and confirm the fallback message appears and lines are still produced. Revert the temporary change.

## 4. ESPN Bet (theScore)

- [x] 4.1 Run the lines HTML, chunk, Startup and marketplace calls through one `with apis.new_session()` session in `make_api_calls`, using `NAVIGATION_HEADERS` for the HTML page, and update the `espn_*` helpers in `apis.py` to take the session and use `apis.get`. Verify: an ESPN-only local run (`--no-fetch-pickem --no-fetch-draftkings --no-fetch-oddshark`) produces lines, and the log shows cache lines for both the `sportsbook.thescore.bet` and `sportsbook.us-il.thescore.bet` hosts.
- [x] 4.2 Change Startup and marketplace to `Sec-Fetch-Site: same-site`, and drop `traceparent`, `tracestate`, `x-datadog-*` and `TE`. Keep the client-name headers, `x-install-id` and `connectToken` as named constants. Verify: `grep -n "datadog\|traceparent\|cross-site" src` returns nothing.
- [x] 4.3 Add `ESPN_GEO` (DMA 602, West Loop 41.8838214 / -87.6517493, accuracy 20), and build the Startup and marketplace query variables with `json.dumps` + `urlencode` instead of hand-encoded strings, sending `x-dma` from the same constant. Verify: the ESPN-only run's Startup returns an `anonymousToken`. If it doesn't, retry with the captured Springfield coordinates (39.7638164 / -89.7408708), keep whichever works, and record the outcome in design.md Risks.
- [x] 4.4 Add `check_graphql(json, operation)`, and call it on the Startup response before reading the token and on the marketplace response before `storage.write_text`. Verify: feeding it `{"errors":[{"message":"x"}]}` in a Python one-liner raises `ValueError` naming the operation, and a normal ESPN-only run still writes `cache/espn_markets_resp.json`.

## 5. covers.com

- [x] 5.1 Send the covers request through `with apis.new_session()` and `apis.get`, keeping only the page-specific headers on top of `NAVIGATION_HEADERS` (drop `Host` and `TE`, and for now keep `Pragma` / `Cache-Control: no-cache`). Verify: a covers-only local run (`--no-fetch-pickem --no-fetch-draftkings --no-fetch-espnbet`) produces spreads and logs a cache line for `www.covers.com`.
- [x] 5.2 Read that cache line. If `Age` is absent or a few seconds, or the response is `no-cache` / `private`, remove the `no-cache` headers and re-run to confirm spreads still come back. Otherwise keep them, and note the observed values in design.md Decision 4.

## 6. Integration

- [x] 6.1 Run a full local fetch (`pipenv run python src`) and confirm all four sources produce rows, every request in the log carries the same UA (spot-check with a temporary debug print or the cache log), and the readout builds.
- [x] 6.2 Run the existing test suite and the Lambda import check (`python -c "import sys; sys.path.insert(0,'src'); import lambda_function"`), and confirm both pass and that `selenium` is not imported.
- [x] 6.3 Check README.md for anything this change affects (nothing is expected, since it documents no headers or versions), and update it only if something is now wrong.
