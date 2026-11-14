# Design

## Context

`make_api_calls` in `src/espn_bet.py` downloads the `pages/index-*.js` chunk and pulls persisted-query SHAs from it with `get_sha_token` (regex on `"<op>":"<sha>"`). The chunk's env module (module 19198 in the saved copy) holds `NEXT_PUBLIC_PACKAGE_JSON_VERSION: a.env.NEXT_PUBLIC_PACKAGE_JSON_VERSION || "<version>"`; the site's header helper reads it for `x-app-version` and the Apollo client for its `version`. `resources/espn_chunk.js` is beautified and old (fallback `25.19.2`); the HAR chunk is minified (`||"26.19.1"`). Whitespace around `||` therefore varies.

## Goals / Non-Goals

**Goals:**
- One source of truth for the version, read at run time from the chunk already fetched.
- No extra network request.

**Non-Goals:**
- Dynamically deriving other hardcoded headers.
- Caching the version across runs.

## Decisions

- **Regex on the chunk**, next to `get_sha_token`: `NEXT_PUBLIC_PACKAGE_JSON_VERSION\s*(?::|\|\|)\s*"(\d+(?:\.\d+)+)"`, which accepts both the `||"<version>"` fallback form and the plain `NEXT_PUBLIC_PACKAGE_JSON_VERSION:"<version>"` literal (the live bundle on 2026-11-14 uses the latter, `26.22.0`). Alternative: scan for any `"NN.NN.N"` literal — too loose. Alternative: read the `/_next/static/.../_buildManifest` or HTML `__NEXT_DATA__` — the version isn't there (checked the saved HTML).
- **Pass the version as a parameter** to `espn_startup_get` and `espn_marketplace_get` rather than a module global, matching how `startup_sha`/`bearer_token` already flow. Both header dicts use it for both headers.
- **Raise `ValueError` naming the app version** when there is no match, so a changed bundle layout gives a clear message instead of a 403. No fallback literal, since a stale fallback reproduces the original failure silently.
- Update the 403 comment in `make_api_calls`, which points at hardcoded headers.

## Risks / Trade-offs

- [Site changes how the constant is emitted (e.g., drops the `||` fallback)] → clear error; regex is one line to adjust.
- [Env var set at build so the fallback literal is absent] → same error path; the HAR and saved chunk both show the literal today.
