# Design

## Context

See proposal.md - Why. Current I/O:

```
  module          write                                      read back
  --------------  -----------------------------------------  ----------------------------------
  pickem.py       util.write_string_to_file -> resources/     open() when fetch_pickem=False
                  pickem.html, save_auth_file -> resources/    load_auth_cookies() every live fetch
                  pickem_auth.json
  draft_kings.py  util.write_string_to_file(Response)          open() when fetch=False
  espn_bet.py     util.write_string_to_file(Response)          open() when fetch=False
  odds_shark.py   util.write_string_to_file(str)               open() when fetch=False (no encoding)
  csv_util.py     open(out_name, 'w') -> ./out/spreads_...      -
  html_util.py    open(output_filename, 'wb')                  open(csv_filename) -- reads back the CSV
```

Writes are UTF-8, but three reads use `open()` with no encoding, which is cp1252 on Windows. `pickem.load_auth_cookies` / `save_auth_file` were already split out so the session's location could change later (archived `pickem-session-cookie-fetch` design). Lambda's Python runtime ships `boto3`. The S3 layout, CloudFront plan and SSM choice were settled in exploration. See specs for the exact behavior.

## Goals / Non-Goals

**Goals:**
- One module owns "where files live". Source modules name a key and never build paths or call `open()`.
- Local runs produce the same files in the same places (except `out/csv/`).
- Everything S3 needs (bucket, content metadata, SSM name) is in one place for the later deploy work.

**Non-Goals:**
- Writing to AWS from local runs, or any sync between local files and S3.
- Making the bucket or SSM parameter name configurable beyond `PICKEM_BUCKET`.
- Retries, multipart uploads or concurrency control: objects are a few KB, and the last writer winning on `out/readout.html` is fine.

## Decisions

**1. A `storage.py` module with module-level functions, resolved from the environment.**

```
  pickem.py / draft_kings.py / espn_bet.py / odds_shark.py / pickem_plug.py
            |  storage.read_text(key)  storage.write_text(key, text)
            |  storage.read_session()  storage.write_session(text)
            v
      storage.py --- backend() reads PICKEM_STORAGE / PICKEM_BUCKET once, caches it
            |
     +------+---------------------------+
     |                                  |
  LocalBackend                       S3Backend (boto3 imported in __init__)
   cache/x -> resources/x             put_object / get_object on PICKEM_BUCKET
   other   -> ./<key>                 ContentType by extension, CacheControl no-cache
   session -> resources/              session -> ssm.get_parameter(WithDecryption=True)
              pickem_auth.json        write_session -> no-op, returns False
```

Also `storage.validate()`, called at the top of `run()` next to `time_util.get_display_tz()`. It builds the backend, so a bad mode or a missing bucket fails before any fetch. In S3 mode it also confirms `boto3` imports. It doesn't call AWS. A `storage.reset()` clears the cached backend so tests and scripts can change the environment.

Alternatives: pass a storage object through `RunConfig` into every source function. That is cleaner for injection, but it changes every source's signature, and the mode is per process, not per run, so module-level resolution is enough. A filesystem abstraction library such as `fsspec`/`s3fs` adds a heavy dependency for four operations.

**2. Logical keys with a per-backend mapping.**
Source modules keep a key constant in place of `OUTPUT_FILE` (for example `SAVED_PAGE_KEY = 'cache/pickem.html'`). File names stay as they are (`DK_markets_resp.json` and so on), so only the `cache/` -> `resources/` prefix needs mapping locally. Any other key maps to the same path, which lets `--override-csv out/spreads_output_..._UTC.csv` keep working for CSVs already in `out/`. Renaming the cache files to nicer names was considered and rejected: it adds a mapping per file for no behavior gain.

**3. Read errors are normalized.**
`read_text` raises `FileNotFoundError` naming the key in both backends (`NoSuchKey` is translated), so `pickem.load_auth_cookies`' existing "missing" handling and the offline-run error look the same in both modes. `read_session` returns `None` when the file or `ParameterNotFound` is missing, and `load_auth_cookies` keeps its JSON and version validation, now applied to text from either source.

**4. Session: read from SSM, never written there.**
`pickem.save_auth_file` calls `storage.write_session(json_text)`. The local backend writes the file. The S3 backend returns False, and `pickem` prints "new session not saved in S3 mode". In practice Lambda never gets this far, because the browser fallback fails on the missing selenium. The no-op covers a local run with `PICKEM_STORAGE=s3`. `GetParameter` with decryption on the default `aws/ssm` key needs only `ssm:GetParameter` on the parameter ARN (the AWS-managed key's policy covers decryption through SSM). The value is about 1.6 KB, under the Standard tier's 4 KB limit.

**5. CSV text built once, written, and parsed in memory for the HTML.**
`csv_util.build_csv(rows) -> str` (the existing header-union logic writing into `io.StringIO`). `pickem_plug.run` writes it with `storage.write_text`, then parses the same text with `csv.reader` to get the HTML rows. Feeding the HTML from the CSV text rather than the dicts guarantees the readout matches the CSV cell for cell (missing columns become `''` exactly as `DictWriter` does). `html_util.create_html` becomes `render_html(rows, generated_at, ...) -> str`, and `run` writes the result to `out/readout.html`. With `--override-csv`, `run` reads the CSV text through storage and follows the same parse and render path.

**6. Content metadata from a small extension table in the S3 backend.**
`{'.html': 'text/html; charset=utf-8', '.csv': 'text/csv; charset=utf-8', '.json': 'application/json'}`, falling back to `text/plain; charset=utf-8`. Every S3 write sets `CacheControl='no-cache'`. Only the readout needs it, but one rule is simpler, and nothing else is served. Text is encoded to UTF-8 bytes before `put_object`. When CloudFront is set up later, it needs a cache policy with a minimum TTL of 0 (for example `CachingDisabled`) to honor this header. That's noted here for the deploy work.

**7. `boto3` as a lazy import, listed in `[dev-packages]`.**
Same pattern as selenium: imported in `S3Backend.__init__`, and an `ImportError` becomes "S3 storage needs boto3". It's in `[dev-packages]` so local S3-mode verification can import it. Lambda uses the runtime's copy until packaging decides whether to pin one.

**8. `util.write_string_to_file` is left in place but unused by the run.**
Its `Response` handling moves to callers (`body.text`). Deleting it is fine if nothing else imports it at apply time.

## Risks / Trade-offs

- [Runtime `boto3` version drifts from local] → Only `put_object`, `get_object` and `get_parameter` are used, which have been stable for years. Pinning is a packaging decision.
- [Session in SSM expires (~30 days) and Lambda starts failing] → The existing clear "both strategies failed" error. Refreshing SSM is a manual step outside this change, and alerting is later work.
- [Local CSVs split between `out/` (old) and `out/csv/` (new)] → Old files stay usable through `--override-csv`. Moving them is optional and manual.
- [Cached backend hides an environment change within one process] → Only tests or scripts would change the environment mid-process, and they can use `storage.reset()`.
- [Mis-scoped CloudFront policy could expose `cache/`] → A deploy-time concern, recorded for the pipeline work: origin path `/out`.

## Migration Plan

1. Apply the change. Local runs keep working with no environment changes. New CSVs land in `out/csv/`.
2. Later deploy work: create bucket `pickemplug-<account-id>` and SSM parameter `/pickemplug/pickem-auth` (SecureString, value = `resources/pickem_auth.json`), and set `PICKEM_STORAGE=s3` and `PICKEM_BUCKET` on the Lambda. Seed `cache/` only if offline runs are wanted in AWS.
3. Rollback: revert the commit. Local files are unaffected.
