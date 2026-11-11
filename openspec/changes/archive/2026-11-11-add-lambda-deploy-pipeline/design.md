# Design

## Context

See proposal.md (Why) for the drifted state of the live function. Constraints that shape the approach:

- The operator machine is Windows with Git Bash. `scripts/upload-pickem-auth.sh` already sets the style: `set -euo pipefail`, `MSYS_NO_PATHCONV=1`, `cd` to the repo root, read only AWS settings from `.env` (never `source` it), and a `--check` mode. `zip` may be missing; `pipenv` and `python` (the pipenv venv, 3.14) are available.
- `boto3` is a dev package because the Lambda runtime provides it (`storage.py` imports it lazily). `selenium` is only imported by `selenium_pa.py`, lazily from `pickem.py`.
- `aws lambda update-function-configuration` replaces the whole `Environment` map, and does **not** take an architecture; architecture is set on `update-function-code --architectures`.
- In S3 mode a `fetch_*: false` run reads `cache/pickem.html`, `cache/DK_markets_resp.json`, `cache/espn_markets_resp.json` and `cache/odds_shark.html` from the bucket, and raises `FileNotFoundError` if one is missing. It then writes `out/readout.html` and a new `out/csv/...` object.
- The upload script lets values already in the environment win over `.env`, so exporting `AWS_DEFAULT_REGION` before calling it pins its region without changing it.

## Goals / Non-Goals

**Goals:**
- One command deploys reproducibly from a Windows machine; a second command builds without touching AWS.
- The config file, not the console, is the source of truth for handler, runtime, architecture, timeout, memory and environment.
- Every stage is a function in the script, so a failure names its stage and later stages are skipped.

**Non-Goals:**
- No Python packaging tool, Docker, SAM or CloudFormation.
- No management of the execution role, triggers, S3 buckets, or Lambda version pruning.
- No changes to application code or to `scripts/upload-pickem-auth.sh`.

## Decisions

### Files

| Path | Role |
|------|------|
| `deploy/lambda.json` | Checked-in deploy config |
| `scripts/build-lambda.sh` | Build stage; runnable alone |
| `scripts/deploy-lambda.sh` | Full pipeline; calls the build script and the upload script |
| `scripts/lambda_build.py` | Small Python helper for the parts bash is bad at (see below) |

A Python helper is used for config validation, zip writing and hashing, because Git Bash lacks `zip` and `jq` is not guaranteed. It uses only the standard library and is run with the project's `python`. It is not a top-level module, so it is never shipped. Alternative: inline `python -c` snippets in bash; rejected as unreadable.

### Config file shape

JSON, so both bash (through the helper) and Python read it with no extra dependency:

```json
{
  "function_name": "pickem",
  "region": "us-east-2",
  "runtime": "python3.14",
  "architecture": "x86_64",
  "handler": "lambda_function.lambda_handler",
  "timeout": 300,
  "memory_size": 512,
  "environment": {
    "PICKEM_STORAGE": "s3",
    "PICKEM_BUCKET": "<bucket name>",
    "DISPLAY_TZ": "America/Chicago"
  }
}
```

- The helper validates it (required keys, types, `runtime` matches `python3.N`, `architecture` is `x86_64` or `arm64`) and rejects any environment key in a deny list: `PICKEM_EMAIL`, `PICKEM_PASSWORD`, and any key containing `AUTH`, `SESSION`, `PASSWORD`, `SECRET` or `TOKEN`. This runs before any AWS call, in both scripts.
- The build derives pip's `--python-version` from `runtime` (`python3.14` -> `3.14`) and `--platform` from `architecture` (`x86_64` -> `manylinux2014_x86_64`, `arm64` -> `manylinux2014_aarch64`), so the two can't disagree.
- Timeout 300 s and 512 MB are starting values: well above the ~50 s worst-case Pickem fetch, and more memory also means more CPU for `lxml`. They are tunable in the file.
- **Role / account-specific values** (resolves the proposal's open question): the config never sets `Role`, so the role ARN stays whatever the function already has and no account ID is committed. The bucket name is account-specific but not secret, so it lives in the file.

### Build

1. Validate config; create `build/<UTC yyyymmddTHHMMSSZ>-<shortsha>[-dirty]/`.
2. `pipenv requirements --hash > requirements.txt`: the lock's `[packages]` only (dev packages are excluded by default), pinned, with markers and every hash. No custom lock parsing.
3. `python -m pip install -r requirements.txt --require-hashes --target <dir>/pkg --platform <plat> --python-version <ver> --implementation cp --only-binary=:all: --no-deps --no-compile`. `--only-binary` is what turns "no wheel" into a hard error; `--no-deps` because the lock already lists the full closure; hashes make the install match the lock exactly.
4. Copy top-level `*.py` except `__main__.py`, `__init__.py`, `selenium_pa.py` into `pkg/`.
5. Helper writes `package.zip` with `zipfile` (deflated, fixed file order so the same inputs give the same file list), computes sha256 (hex for the manifest, base64 for Lambda's `CodeSha256`), and writes `manifest.json` (sha, dirty flag, timestamp, zip sha256, resolved packages read from `pkg/*.dist-info`).
6. Helper rejects a zip containing any `.pyd` or `win_amd64` file, a generic platform guard against pip resolving markers for the Windows host. There is no list of forbidden package names: "`[packages]` only" holds by construction, since only what `pipenv requirements` emits is installed.

The build script prints the run directory path as its last line, which is how the deploy script finds it. Alternative considered: parsing `Pipfile.lock` in the helper; rejected as custom code for a format pipenv already owns, and the project already depends on pipenv for setup.

### Deploy pipeline

Stages, each a bash function run through a `stage <name> <fn>` wrapper that records the current stage name for the failure message and the deploy-log line (an `EXIT` trap writes the line on success or failure):

1. **preflight**: AWS CLI present, `sts get-caller-identity`, `lambda get-function --function-name <fn>` in the config region, `git status --porcelain` empty unless `--allow-dirty`, `upload-pickem-auth.sh --check` (skipped with `--skip-auth-upload`, since its permission is then not needed).
2. **test**: `python -m unittest discover tests`.
3. **build**: `scripts/build-lambda.sh`, reusing the run directory the deploy script already created (passed through an env var) so one run has one directory.
4. **auth push**: `AWS_DEFAULT_REGION=<config region> bash scripts/upload-pickem-auth.sh` unless `--skip-auth-upload`. It inherits the terminal, so its interactive prompts still work, and fails closed without one.
5. **deploy**: `update-function-code --zip-file fileb://... --architectures <arch>`, `wait function-updated`, `update-function-configuration` (handler, runtime, timeout, memory, full environment), `wait function-updated`, then `publish-version --code-sha256 <base64> --description "<sha>: <subject>"` (truncated to Lambda's 256-character limit). `--code-sha256` makes publishing fail if `$LATEST` code changed after our upload.
6. **smoke**: `lambda invoke --qualifier <version> --cli-binary-format raw-in-base64-out --payload '{"fetch_pickem":false,"fetch_draftkings":false,"fetch_espnbet":false,"fetch_oddshark":false}' --cli-read-timeout <timeout+30>`, response saved to `smoke-response.json`. Pass means the CLI exits zero and the output has no `FunctionError`. Skipped with `--no-invoke`.
7. **alias**: only when smoke ran and passed: `update-alias --name live --function-version <v>`, or `create-alias` if `get-alias` reports not found.

All AWS calls pass `--region` from the config explicitly rather than relying on the environment. Output is teed to `<run dir>/run.log` from the start. The deploy log is `build/deploys.log`, one tab-separated line: UTC time, sha, version (or `-`), `ok` or `failed:<stage>`.

Ordering choice: code before configuration, because the architecture can only change with the code; both happen before publishing, so the published version always has the new code and the new config together. `$LATEST` is briefly inconsistent between the two updates, which is harmless since nothing targets it.

### Flags

`--allow-dirty`, `--skip-auth-upload`, `--no-invoke`, `--help`. Unknown flags are an error. With `--no-invoke` the alias does not move (the alias only ever points at a version that passed); the operator can point it by hand.

## Risks / Trade-offs

- [The first smoke invoke fails because the bucket's `cache/` is empty] → One-time seeding in the migration plan. Until then the version is published but `live` is not created, which is the intended fail-safe.
- [The smoke invoke has side effects: it rewrites `out/readout.html` from cached data and adds a CSV under `out/csv/`] → Accepted; the readout is re-rendered from the same last-fetched data, and CSVs are an append-only history anyway.
- [pip evaluates environment markers like `sys_platform` against the Windows host, not the target] → No current runtime dependency has a platform marker; the build's zip check catches Windows binaries if one ever appears.
- [`python3.14` or a `cp314` wheel disappears or changes] → The build fails closed (`--only-binary`), and `update-function-configuration` rejects an unknown runtime before any version is published.
- [`--require-hashes` fails if `Pipfile.lock` lacks a hash for the Linux wheel] → pipenv locks hashes for all published files, so this holds; if it ever fails it fails closed and points at relocking.
- [IAM: the proposal's permission list omits alias calls] → The operator also needs `lambda:GetAlias`, `CreateAlias` and `UpdateAlias`; listed in the README section.

## Migration Plan

1. Fill in `PICKEM_BUCKET` in `deploy/lambda.json`.
2. Seed the bucket cache once from a fresh local run: `aws s3 cp` each of `resources/pickem.html`, `DK_markets_resp.json`, `espn_markets_resp.json`, `odds_shark.html` to `s3://<bucket>/cache/`. Never copy `pickem_auth.json`.
3. Run `bash scripts/build-lambda.sh` and inspect the zip and manifest.
4. Run `bash scripts/deploy-lambda.sh`. Expect version 1 and `live` -> 1.
5. Delete the stale untracked `package.zip` at the repo root (now gitignored).

Rollback: `aws lambda update-alias --function-name pickem --name live --function-version <earlier>`. Configuration is versioned with the code, so an earlier version brings back its own handler, timeout and environment.

## Open Questions

- Confirm on the account that Lambda versions incur no cost beyond the code-storage quota; if they do, add pruning in a later change.
- Final timeout and memory values after a few real runs.
