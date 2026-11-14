# Tasks

## 1. Extract the version

- [x] 1.1 Add `get_app_version(chunk_blob)` in `src/espn_bet.py` using the regex in design.md, raising `ValueError` naming the app version on no match. Verify: run it on `resources/espn_chunk.js` (expect `25.19.2`) and on a minified sample `NEXT_PUBLIC_PACKAGE_JSON_VERSION||"26.19.1"` (expect `26.19.1`); a string without it raises.

## 2. Use it in the API calls

- [x] 2.1 Add an `app_version` parameter to `espn_startup_get` and `espn_marketplace_get` in `src/apis.py`; use it for `x-app-version` and `apollographql-client-version`, removing the `26.21.0` literals and the todo comment. Verify: `grep 26.21.0 src` finds nothing.
- [x] 2.2 In `make_api_calls`, call `get_app_version(espn_chunk)` after fetching the chunk and pass it to both calls; update the 403 comment. Verify: `python src --no-fetch-pickem --no-fetch-draftkings --no-fetch-oddshark` completes the ESPN Bet fetch with live data (no 403) and the ESPN lines appear in the output.
- [x] 2.3 Verify the failure path: temporarily feed a chunk without the constant and confirm the error names the app version and no API call is made.

## 3. Docs

- [x] 3.1 Check `README.md` for mentions of the ESPN version headers; none were found in the current README (grep for `espn` shows only flags), so no README change is expected.
