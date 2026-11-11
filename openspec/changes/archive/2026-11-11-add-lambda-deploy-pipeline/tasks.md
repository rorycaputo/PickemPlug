# Tasks

## 1. Config and repo setup

- [x] 1.1 Add `build/` and `package.zip` to `.gitignore`; verify `git status` no longer lists the root `package.zip`
- [x] 1.2 Create `deploy/lambda.json` with the shape and starting values from design.md (function `pickem`, `us-east-2`, `python3.14`, `x86_64`, `lambda_function.lambda_handler`, 300 s, 512 MB, `PICKEM_STORAGE=s3`, `PICKEM_BUCKET`, `DISPLAY_TZ=America/Chicago`), asking the operator for the bucket name; verify it parses as JSON and holds no credential or session value

## 2. Build helper

- [x] 2.1 Create `scripts/lambda_build.py` (stdlib only) with a config-validation command: required keys and types, `runtime`/`architecture` checks, and the secret deny list; it prints the derived pip `--platform` and `--python-version`. Verify it accepts `deploy/lambda.json` and exits non-zero naming the key for a copy containing `PICKEM_PASSWORD`, and for one with `architecture: "sparc"`
- [x] 2.2 Add zip/manifest commands: write the zip with `zipfile` in sorted order, compute hex and base64 sha256, write `manifest.json` (sha, dirty flag, timestamp, zip sha256, packages from `*.dist-info`), and reject a zip containing any `.pyd` or `win_amd64` file; verified through 3.2

## 3. Build script

- [x] 3.1 Create `scripts/build-lambda.sh` in the upload script's style (`set -euo pipefail`, `MSYS_NO_PATHCONV=1`, repo-root `cd`): validate config, create `build/<timestamp>-<sha>[-dirty]/` (or reuse the directory passed by the deploy script), write `requirements.txt` with `pipenv requirements --hash`, run the `pip install --platform ... --only-binary=:all: --require-hashes --no-deps --target` from design.md, copy top-level `*.py` minus `__main__.py`/`__init__.py`/`selenium_pa.py`, write zip and manifest, and print the run directory as the last line
- [x] 3.2 Verify on Windows with no AWS credentials set: the build succeeds; `requirements.txt` lists `lxml`, `brotli`, `requests` and their transitive deps with hashes but not `selenium` or `boto3`; the zip has `lxml/etree.cpython-314-x86_64-linux-gnu.so` and no `.pyd`; it contains `lambda_function.py`, `pickem_plug.py`, `storage.py`, but no `__main__.py`, `selenium_pa.py`, `tests/`, `resources/` or `.env`; the manifest's sha256 matches the zip; a second run creates a separate directory
- [x] 3.3 Verify the fail-closed path: temporarily set `--python-version` to one with no `lxml` wheel (e.g. edit a copy of the config to `python3.99`) and confirm the build exits non-zero naming the package and leaves no zip

## 4. Deploy script

- [x] 4.1 Create `scripts/deploy-lambda.sh` with flag parsing (`--allow-dirty`, `--skip-auth-upload`, `--no-invoke`, `--help`; unknown flags error), the `stage` wrapper, teeing to `<run dir>/run.log`, and an `EXIT` trap that appends the `build/deploys.log` line (`ok` or `failed:<stage>`); verify `--help` and an unknown flag behave
- [x] 4.2 Implement preflight (AWS CLI, `sts get-caller-identity`, `lambda get-function` in the config region, clean tree unless `--allow-dirty`, `upload-pickem-auth.sh --check` unless `--skip-auth-upload`) and the test stage (`python -m unittest discover tests`); verify a dirty tree stops before tests, and a wrong function name in a config copy stops at preflight with nothing changed in AWS
- [x] 4.3 Wire the build stage to `build-lambda.sh` with the shared run directory, and the auth-push stage to `upload-pickem-auth.sh` with `AWS_DEFAULT_REGION` set from config; verify with `--skip-auth-upload` that the upload script is not run
- [x] 4.4 Implement the deploy stage: `update-function-code --architectures`, wait, `update-function-configuration` (handler, runtime, timeout, memory, full environment), wait, `publish-version --code-sha256 --description "<sha>: <subject>"`; all calls with explicit `--region`; never touch the role. Verified through 5.1
- [x] 4.5 Implement the smoke stage (`invoke --qualifier <version>` with all `fetch_*: false`, `--cli-read-timeout` above the function timeout, response saved to `smoke-response.json`, fail on `FunctionError`) and the alias stage (create or update `live` only after a passing smoke). Verified through 5.1-5.2
- [x] 4.6 Add a "Deploy" subsection under README's `## AWS`: the two commands, flags, `deploy/lambda.json` as the source of truth, the required IAM actions (including `GetAlias`/`CreateAlias`/`UpdateAlias`), the one-time cache seed, and rollback by repointing `live`; verify the documented commands match the scripts' `--help`

## 5. End-to-end on AWS (operator-run)

- [x] 5.1 Seed `s3://<bucket>/cache/` with the four cache files from a fresh local run (never `pickem_auth.json`), then run `bash scripts/deploy-lambda.sh`; verify with `aws lambda get-function-configuration` that handler, runtime, architecture, timeout, memory and environment match `deploy/lambda.json`, that version 1 exists with the sha in its description, that `live` points at it, and that `build/deploys.log` has an `ok` line
- [x] 5.2 Verify the fail-safe: deploy again with a deliberately failing smoke (e.g. temporarily remove one cache object) and confirm a new version is published, the run exits non-zero naming the smoke stage, and `live` still points at the previous version; restore the cache object
- [x] 5.3 Delete the stale root `package.zip` and, if the README note "the run is not yet Lambda-ready" is now inaccurate, update it with the operator's agreement

## Workflow follow-up

- Confirm on the account that Lambda versions carry no cost beyond the code-storage quota.
- Archive the change after review.
