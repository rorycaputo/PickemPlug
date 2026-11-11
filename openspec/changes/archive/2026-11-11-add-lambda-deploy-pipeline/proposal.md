# Proposal

> **Status: draft for review.** Captured from explore sessions on 2026-11-11. Only the proposal exists so far; design, specs and tasks are deliberately not written yet.

## Why

Deploying the `pickem` Lambda today is manual and has drifted badly. A read of the live function on 2026-11-11 showed handler `lambda_function.main` (the code exposes `lambda_handler`), a 3 s timeout (the Pickem fetch alone can take about 50 s), 128 MB of memory, no environment variables (so it would run in local storage mode on a read-only filesystem), only `$LATEST` with no versions or aliases, a python3.10 runtime, and code from the Windows-built October `package.zip` (Windows-built, so its compiled `lxml` and `brotli` can't load on Lambda's Linux). A repeatable local pipeline that builds the package, ships the code *and* enforces the function's configuration removes the need to log in to the console, and keeps this state from coming back.

## Assumptions

- The project is already on Python 3.14 (`Pipfile [requires]`, lock and local venv), so there is no runtime-upgrade prerequisite.
- The Lambda `python3.14` runtime is available in `us-east-2`, which is where the function lives. The config file sets runtime `python3.14` and the build targets CPython 3.14.
- Linux x86_64 wheels exist for the compiled dependencies on 3.14 (checked 2026-11-11 with a read-only `pip install --dry-run`: `lxml-6.1.3` and `brotli-1.2.1`, both `cp314 manylinux2014_x86_64`). No separate build spike or change is needed.

## What Changes

- New local, operator-run deploy script (bash, same style as `scripts/upload-pickem-auth.sh`), run in stages:
  `preflight -> test -> build -> auth push -> deploy (config + code + publish version) -> smoke invoke`.
- **Build** (a stage of this pipeline, also runnable alone as `scripts/build-lambda.sh` for "build, don't deploy"):
  - Exports `[packages]` only from `Pipfile.lock` (no `[dev-packages]`, so no selenium or boto3) and installs them with `pip --platform manylinux2014_x86_64 --python-version 3.14 --only-binary=:all: --target`, so the result is Linux wheels even when run from Windows.
  - Takes the platform/architecture and Python version from the deploy config file, so the build and the function setting can't disagree.
  - Adds the app modules (top-level `.py` files only, minus a small exclude list; see Decisions) and writes the zip with Python's `zipfile` (Windows git-bash may not have `zip`).
  - Fails if any dependency has no matching binary wheel, rather than falling back to a source build.
  - Gitignores `build/` and `package.zip`. The existing untracked `package.zip` is the stale Windows/py3.10 artifact.
- **Preflight** checks AWS credentials, that the function exists, and a clean git tree (overridable with an explicit flag such as `--allow-dirty`), and runs `upload-pickem-auth.sh --check` so a missing AWS permission fails before tests or the build.
- **Auth push** runs `scripts/upload-pickem-auth.sh` as a step, and a flag (e.g. `--skip-auth-upload`) disables it. In a terminal it may stop and wait on an expired session; without one it fails closed, as its spec already requires.
- **Config enforcement:** a checked-in config file (handler `lambda_function.lambda_handler`, runtime `python3.14`, architecture, timeout, memory, region, non-secret env vars such as `PICKEM_STORAGE=s3`, `PICKEM_BUCKET`, `DISPLAY_TZ`) is applied with `update-function-configuration` on every deploy. It must never hold `PICKEM_EMAIL`, `PICKEM_PASSWORD` or the session (per `AGENTS.md`).
- **Code deploy:** `update-function-code`, wait for the update, then `publish-version` with the git sha and subject as the description, so every deploy is an immutable, numbered version you can roll back to.
- **Build history:** each run keeps `build/<timestamp>-<sha>/` (zip, manifest with sha, zip sha256, resolved packages and timestamp, and a tee of the run log), plus a one-line-per-run deploy log.
- **Smoke invoke** (on by default, with a flag such as `--no-invoke` to skip) invokes the new version with all `fetch_*: false` (reads only the S3 caches) and reports success or failure.
- **`live` alias:** after a successful smoke invoke the pipeline points a `live` alias at the new version. If the smoke invoke fails, the alias stays on the previous version, so the alias only ever points at a version that passed. Rollback is repointing `live` at an earlier version.

Tooling decision: plain bash plus the AWS CLI. We considered make/just, SAM, local Jenkins, `act`/GitHub Actions and CodePipeline/CodeBuild. They are heavier than one operator and one function need. SAM would mean adopting the existing function into a CloudFormation stack.

## Out of scope

- Creating or configuring S3 buckets (the bucket *name* only appears as an env var).
- The cron/scheduler itself, IAM role changes and CI servers. No trigger exists yet; when one is created it should target `pickem:live` rather than `$LATEST`.

## Decisions

- **Alias:** no trigger or cron exists yet, so there is nothing to retarget. The pipeline maintains the `live` alias from the first deploy, and the future scheduler targets `pickem:live` from day one.
- **Smoke invoke:** on by default, cheap mode (all `fetch_*: false`). The live-fetch variant (which would answer the datacenter-IP question in `docs/LAMBDA_DISCOVERY.md` #9) is not part of the default; it could be an opt-in flag later.
- **Retention:** keep local `build/` dirs unlimited, with no pruning. Lambda versions are not pruned unless they turn out to cost money. To my knowledge versions are free and only count against the per-region code storage quota (75 GB; at roughly 5 MB per package that is thousands of versions), so there is nothing to prune, but this should be confirmed on the account.
- **Which files ship:** a rule, not a list: **ship only code, meaning the top-level `*.py` files**, with a small exclude list. No non-`.py` files are needed, since all data goes through `storage.py` (S3 in Lambda) and no bundled data files are read at runtime. Because the rule only takes top-level files, `tests/`, `docs/`, `resources/`, `scripts/`, `openspec/`, `out/`, `.env` and any other non-code files stay out automatically, and a new module is picked up without editing anything. The exclude list is `__main__.py` (the local CLI; Lambda enters through `lambda_function.py`), `__init__.py`, and `selenium_pa.py`. Leaving selenium out also proves Lambda never needs it, since the import in `pickem.py` is lazy and only runs on the local browser-login path.

## Open questions

- **Architecture:** x86_64 is assumed, matching the current function. Switching to arm64 would only be a config-file change.
- How config enforcement handles a role ARN or anything else that is account-specific.

## Capabilities

### New Capabilities
- `lambda-deployment`: building (Linux wheels for the target runtime, `[packages]` only), configuring, publishing and verifying the `pickem` Lambda from a local machine, including build history and the optional session-upload step.

### Modified Capabilities
<!-- None expected: the pipeline invokes scripts/upload-pickem-auth.sh as-is, within its existing session-upload requirements. -->

## Impact

- New: the deploy script, the build script, and the Lambda config file. `.gitignore` gains `build/` and `package.zip`.
- Uses: `scripts/upload-pickem-auth.sh`, `Pipfile.lock`, `tests/`.
- AWS: the `pickem` function's configuration and versions in `us-east-2`, and SSM `/pickemplug/pickem-auth` (through the existing script only). The operator's IAM user needs `lambda:UpdateFunctionConfiguration`, `UpdateFunctionCode`, `PublishVersion`, `GetFunction*` and `InvokeFunction`.
- README: a new deploy section when this is implemented.
