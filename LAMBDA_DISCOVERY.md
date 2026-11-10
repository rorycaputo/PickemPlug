# Lambda Discovery: Pickem Plug

Goal: run this repo's functionality on AWS Lambda on a cron. This document covers only step one: getting the codebase ready to run as a Lambda. Deployment and infrastructure come later.

## Summary

The pipeline itself suits Lambda: fetch four sources, build a table, render a CSV and an HTML readout. It is stateless and short-running. But several things in how it runs today will fail on Lambda whatever the entry point is called, and the biggest is Selenium/Firefox.

`lambda_function.py` is the right idea but the wrong shape. It is currently a 395-line copy of `__main__.py` with only the `main` signature changed, so the name map, display arrows and `build_table` now exist twice and will drift.

## Entry point shape

```
  Lambda (EventBridge cron)          local dev
          |                              |
          v                              v
  lambda_function.py            __main__.py  (python __main__.py)
  lambda_handler(event, ctx)        main()
          \                           /
           \                         /
            v                       v
          pickem_plug.py  (or app.py)   <- today's __main__ body lives here
            run(config) -> result
              |
     +--------+---------+----------+
     v        v         v          v
  pickem  draft_kings  espn_bet  odds_shark ...
```

- Core module: takes config as an argument and returns a result, instead of reading module constants and writing to `./out`.
- Both entry points are about 10 lines each.
- Lambda handler string: `lambda_function.lambda_handler`.
- On the "clash" with other AWS packages: I couldn't confirm it. A file named `__main__.py` is awkward for Lambda anyway, since Python treats that name specially and Lambda imports the handler as a normal module. Moving the logic out is right either way.

## What will break on Lambda

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| 1 | **Selenium + Firefox.** `webdriver.Firefox()` with no headless flag. Lambda has no Firefox, no geckodriver, no display. | `selenium_pa.py` | Blocker |
| 2 | **Read-only filesystem.** Everything writes to `./out` and `./resources`. Only `/tmp` is writable. | `util.write_string_to_file`, `csv_util`, `html_util` | Blocker |
| 3 | **`FETCH_PICKEM = False` path.** Reads `resources/pickem.html`, which is gitignored and not in the zip. All fetches must be live on Lambda. | `pickem.py` | Blocker |
| 4 | **Windows-built zip.** `package.zip` contains `lxml/etree.cp310-win_amd64.pyd`, which won't import on Lambda's Linux. | `package.zip` | Blocker |
| 5 | **Where output goes.** The HTML and CSV are the product, and nothing says where they end up. | n/a | Design decision |
| 6 | **Credentials in source.** Email and a base64 password are committed to git. Base64 is not encryption. | `pickem.py` | Fix before deploying |
| 7 | **Timezones.** Lambda `datetime.now()` is UTC. `date_util` assumes Eastern (8:30 PM MNF cutover) with naive datetimes. Week number flips about 4 hours early; DK 7-day window and CSV filenames shift too. | `date_util.py`, `__main__.py`, `draft_kings.py` | Moderate |
| 8 | **Failure handling.** If DK or ESPN returns `None`, `body.json()` or `espn_marketplace_json['data']` raises, so one flaky source kills the run. Async Lambda invocations retry twice by default, so a crash means three scrapes. | `draft_kings.py`, `espn_bet.py`, `pickem.py` | Moderate |
| 9 | **Datacenter IPs.** DK, ESPN and CBS may block AWS IP ranges even though they work from a home IP. | n/a | Unknown, test early |
| 10 | **Shared `requests.Session()` defaults.** Created once at import, so cookies persist across warm invocations. | `apis.py` | Minor |

## The Selenium question

This decides whether the Lambda is a zip or a container image.

| Option | Pros | Cons |
|--------|------|------|
| **Container image Lambda** (headless Chrome/Chromium + chromedriver, or Firefox + geckodriver) | Keeps the current approach; up to 10 GB | Needs Dockerfile and ECR; browser needs 2 GB+ memory; slower cold start |
| **Replace the browser with `requests`** | Tiny zip, fast cold starts | `apis.py` already has `pickem_login_post`, so it was tried before; may fail if CBS login needs JS or has bot checks |
| **Split it out** (browser scrape elsewhere, Lambda does the API/HTML sources) | Lambda stays simple | More moving parts |

## What's already good for Lambda

- Stateless pipeline that maps onto one short cron invocation.
- Flat imports with modules at the root, so zip or image layout is trivial.
- The `fetch=False` cache reads are a decent local-dev mode. Keep them, gated behind a dev flag so production always fetches.
- Sources are fetched in sequence, and the Pickem login is the slowest at about 50 s worst case. That is far under the 15-minute limit.
- `print` goes to CloudWatch with no changes.

## Open decisions

1. **Where should the result land?** The `# todo format for email` comment hints at email.
   - S3 only: simplest, viewable via static site or presigned link.
   - SES email of the HTML: matches the todo, needs sender verification.
   - Both: S3 archives every CSV the way `out/` does today, email sends the readout.
2. **Pickem login:** try a `requests`-based login first (short spike), or go straight to a container image?
3. **Cron timing:** fixed times, or use `get_nfl_week` to decide whether a run does anything at all?

## Suggested order

1. ✅ Refactor: thin `lambda_function.py`, move the body into a core module, pass config in instead of reading constants. *(Done: archived as `refactor-run-entrypoints`; core is `pickem_plug.py`.)*
   - ⬜ Move credentials to env vars or SSM. *(Still open; credentials are still hardcoded in `pickem.py`.)*
2. Make IO pluggable: the core returns the CSV and HTML as strings or bytes, and a thin layer writes them to disk locally or to S3/SES on Lambda. Use `/tmp` for any caches.
3. Fix timezones: use `ZoneInfo('America/New_York')` throughout.
4. Make failures partial: a missing source becomes an empty list plus a warning, and doesn't take down the whole run.
5. Spike the datacenter-IP question early: run the three HTTP fetchers from a throwaway Lambda before building anything else around them.

## Security note

The CBS credentials are in git history. If the repo is ever pushed anywhere, rotate that password first.

## Next step

Explore mode does not implement. When ready, `/opsx:propose` turns this into a change with specs, design and tasks. Step 1 above is a natural first slice.
