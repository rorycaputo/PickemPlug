# Tasks

## 1. Build from src/

- [x] 1.1 In `scripts/build-lambda.sh`, change the copy loop to read `src/*.py` (non-recursive), drop `__init__.py` from `EXCLUDE`, and name the `src/tests` exclusion explicitly. Verify: a build's `pkg/` has the `src/` modules flat at its root and no `tests`, `__main__.py` or `selenium_pa.py`.
- [x] 1.2 Make the build fail with a clear message when `src/` is missing or contributes no files. Verify: temporarily pointing the script at an empty source directory exits non-zero and writes no zip.
- [x] 1.3 Run `bash scripts/build-lambda.sh` and compare the zip's file list against the previous build in `build/`. Verify: the same app modules appear, and `unzip -l` shows no `src/` or `tests` paths.

## 2. Test stage

- [x] 2.1 In `scripts/deploy-lambda.sh`, change `run_tests` to run `unittest discover` from `src/tests` with `PYTHONPATH=src`, and fail when zero tests are discovered. Verify: the stage runs the 17 current tests and passes; pointing it at an empty directory fails.
- [x] 2.2 Update the README's Tests command to match. Verify: running the README's command exactly passes.

## 3. Docs and spec

- [x] 3.1 Update the README Layout table so file paths are under `src/` and the Lambda section's description of what ships still matches. Verify: every file named in the table exists at the stated path.
- [x] 3.2 Run `openspec validate build-from-src-directory`. Verify: it reports the change as valid.

## Workflow follow-up

- A full `scripts/deploy-lambda.sh` run changes AWS state, so it is left to the user after apply.
