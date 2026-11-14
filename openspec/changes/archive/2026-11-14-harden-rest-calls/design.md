# Design

## Context

- `src/apis.py` holds three GET/POST helpers, a module-level `headers` dict (Firefox 134, `Accept-Encoding: utf-8`), and per-site functions for ESPN Bet plus a dead CBS login POST. `call_post_api` and `call_get_api_with_session` default `session=requests.Session()`, which is evaluated once at import.
- Callers: `draft_kings.py` and `odds_shark.py` call `call_get_api` with their own header dicts. `espn_bet.py` chains HTML, chunk, Startup and Lines. `pickem.py` calls `call_get_api_with_session` with its own cookie-seeded session and the default headers, and checks `isinstance(result, tuple)` to detect failure.
- Evidence comes from three gitignored captures in `resources/`:
  - **theScore, 2026-09-27 (Firefox 156):** the client-name headers are unchanged since the rebrand. API calls send `Sec-Fetch-Site: same-site`. Lines responds `max-age=1, stale-while-revalidate=5, public` through Cloudflare; Startup is `private` / `BYPASS`.
  - **DraftKings, 2026-11-14 (Firefox 159):** markets carries `x-client-version: 2646.5.2`, `x-client-widget-version: 3.3.0`, new `x-pe-cn/cv/ep/loc` headers and `templateVars=88808`, and responds `public, max-age=1`. The NFL page (`/leagues/football/nfl`, `no-store`, about 2.2 MB) contains `window.sbwebversion = "2646.5.2";`. The browser really does send `content-type: application/json charset=utf-8` on that GET.
  - **CBS, 2026-11-10 (Firefox 159):** a navigation with `DNT: 1` and `Sec-GPC: 1`. The page responds `max-age=3600, public, no-cache, must-revalidate`.
  - Every capture shows `Pragma` / `Cache-Control: no-cache` on browser requests, which is consistent with DevTools "Disable Cache" being on while recording.
- There are no tests on `apis.py` or the fetch modules. The run has no per-source error isolation: any source exception fails the run.

## Goals / Non-Goals

**Goals:**
- Make every source request look like one current Firefox, and make each source's request chain look like one visitor.
- Make failures explicit and early, without changing the Pickem fallback contract.

**Non-Goals:**
- Changing the transport or the TLS fingerprint (`curl_cffi` was declined).
- Persisting cookies across runs.
- Per-source error isolation (letting the run continue when one source fails).
- Scraping the DraftKings widget version.

## Decisions

### 1. Header profile as layered constants in `apis.py`

```
FIREFOX_VERSION = '159.0'
FIREFOX_UA      = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:159.0) Gecko/20100101 Firefox/159.0'

BROWSER_HEADERS      UA, Accept-Language, Accept-Encoding: gzip, deflate, br,
                     DNT: 1, Sec-GPC: 1, Connection: keep-alive
NAVIGATION_HEADERS   Accept: text/html..., Upgrade-Insecure-Requests: 1,
                     Sec-Fetch-Dest: document, -Mode: navigate, -Site: none,
                     -User: ?1, Priority: u=0, i
```

`BROWSER_HEADERS` replaces the session's defaults when a session is created, which also removes `python-requests` and `Accept: */*`. Each request then layers `NAVIGATION_HEADERS`, or site-specific API headers, on top. Site-specific dicts keep only what differs: `Accept`, `Referer`, `Origin`, `Sec-Fetch-*`, the `x-*` app headers.

- *Why one version constant:* the four UA strings drifted independently. Bumping one value is the whole upgrade.
- *Why `br` and not `zstd`:* `brotli` is in the Pipfile. zstd decoding depends on the urllib3 build and isn't verified. Advertising an encoding the app can't decode risks unreadable bodies.
- *Alternative:* a full header dict per call, as today. Rejected: it's how the drift happened.

### 2. Sessions created per source, per run

`apis.new_session()` returns a `requests.Session` with `BROWSER_HEADERS` set. Each fetch function creates one at the start of its live fetch, passes it through its request chain, and closes it with a `with` block. `pickem.py` already creates its own session; it switches to `new_session()` and then seeds the saved cookies. No helper accepts a default session, so the import-time `requests.Session()` disappears.

- *Alternative:* a module-level registry of sessions keyed by site, created on first use. Rejected: it would survive a warm Lambda container, which is the state the change removes.

### 3. One `get` helper that raises

```
apis.get(session, url, *, headers=None, params=None, timeout=DEFAULT_TIMEOUT) -> Response
    response = session.get(...)
    response.raise_for_status()
    return response
```

- `DEFAULT_TIMEOUT = 30` seconds, matching `pickem.REQUEST_TIMEOUT_SECONDS`, which Pickem keeps passing explicitly.
- `call_get_api`, `call_get_api_with_session` and `call_post_api` are removed. With no POST callers left, there's no POST helper.
- Errors propagate as `requests.RequestException` subclasses. `pickem.fetch_pickem_html_with_session` catches `requests.RequestException` and returns `None`, preserving "Request failure → browser login". DraftKings catches it only around the optional league-page request (Decision 5). ESPN Bet and covers let it propagate.
- Per-request cache-header logging was built and used to verify Decision 4, then removed at the user's request to keep run logs quiet.
- No retry adapter is mounted. requests' default (`max_retries=0`) already satisfies "no automatic retries"; the design records it so nobody adds one.

### 4. `no-cache` handling per source

- DraftKings, ESPN Bet, CBS: drop `Pragma` / `Cache-Control`. The captures show `max-age=1`, `private` or `must-revalidate`, and the headers were a DevTools artifact.
- covers.com: there's no capture, so this was checked live on 2026-11-14. The response has no `Age` or `Cache-Control`, and `X-Cache: Miss from cloudfront` on back-to-back runs with and without the headers. CloudFront doesn't cache the page, so the `no-cache` headers were removed.

### 5. DraftKings version page

```
with apis.new_session() as session:
    version = get_client_version(session)    # never raises
    markets = apis.get(session, lines_url, headers=markets_headers(version))
```

- `get_client_version` GETs `https://sportsbook.draftkings.com/leagues/football/nfl` with `NAVIGATION_HEADERS` and searches with `window\.sbwebversion\s*=\s*"(\d+(?:\.\d+)+)"`. A comment says the request is not strictly necessary, because the markets API accepts a stale version.
- On `requests.RequestException` or no match, it prints `Using fallback DraftKings client version 2646.5.2` and returns `DK_FALLBACK_CLIENT_VERSION = '2646.5.2'`.
- `sbwebversion` was chosen over the Datadog RUM config's `"version"`, which carries the same value: it's a dedicated variable, so it's less likely to change shape.
- This deliberately differs from ESPN Bet's no-fallback rule in `AGENTS.md`. The user chose it for DraftKings, and the fixed value is the current version, not an arbitrary guess.
- Markets headers follow the 11-14 capture: `x-client-widget-version: 3.3.0` (hardcoded), `x-pe-cn: web`, `x-pe-cv: <version>`, `x-pe-ep: SB`, `x-pe-loc: US-IL`, the same `content-type` the browser sends, `Sec-Fetch-Site: same-site`. `lines_url` is updated to `templateVars=88808`.

### 6. ESPN Bet

- `get_espn_html` takes the session and uses `apis.get` with `NAVIGATION_HEADERS`. The chunk, Startup and Lines calls reuse that session in order.
- `Sec-Fetch-Site: same-site` on Startup and Lines. Trace headers and `TE` are dropped. `x-install-id` and `connectToken` stay as named constants.
- Geo is grouped in one constant:
  ```
  ESPN_GEO = {'dma': '602', 'latitude': 41.8838214, 'longitude': -87.6517493, 'accuracy': 20}
  ```
  The point is in Chicago's West Loop: deliberately not the canonical city-centre geocode, and at 7-decimal browser precision. The Startup variables are built with `json.dumps` + `urllib.parse.urlencode` from `ESPN_GEO`, so the location can't drift from the DMA. The marketplace variables are built the same way.
- `check_graphql(json, operation)` raises `ValueError(f'ESPN Bet {operation} failed: {first error message}')` when `errors` is non-empty or `data` is missing. It runs on Startup before reading the token, and on Lines before `storage.write_text`.

### 7. Dead CBS login

`pickem_login_post` is commented out as a block. In the comment, the `Cookie` value, `Next-Action`, `ACTION_KEY` and the `$ACTION_3:0` id are replaced with `<captured value>`. The commented ritual `Cookie` line in the old default headers goes away along with that dict.

## Risks / Trade-offs

- [The Chicago location may not suit the captured `connectToken`, so Startup errors] → Checked on 2026-11-14: Startup returned an `anonymousToken` with the West Loop coordinates, and the marketplace call succeeded, so the token isn't tied to the captured location.
- [The DraftKings version page adds about 2.2 MB per run] → Accepted by the user and marked unnecessary in code. It fails soft.
- [The fallback `2646.5.2` ages] → The fallback is logged on every run that uses it, so a persistent fallback shows up in the logs. The markets API has tolerated stale versions so far: the code ran for months on `2537.2.1.7` while the site moved to `2646.5.2`.
- [Raising errors turns some silent failures into run failures] → They already failed with misleading errors. Pickem keeps its fallback via the explicit catch.
- [`Accept-Encoding` without `zstd` differs from real Firefox] → A small fingerprint difference, preferred to undecodable bodies.
- [The Firefox version goes stale] → One constant to bump. No automation.

## Migration Plan

There's no data migration. Deploy with the normal `scripts/deploy-lambda.sh`: its smoke invoke runs with every `fetch_*` off, so it exercises imports but not these requests. The first scheduled live run is the real check. To roll back, point the `live` alias at the previous version.
