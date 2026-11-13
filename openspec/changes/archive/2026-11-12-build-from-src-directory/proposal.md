# Proposal

## Why

All Python modules now live in `src/`, but the Lambda build still copies the repo root's `*.py` files and the deploy pipeline still runs tests from `tests/`. The build would now ship an empty app and the deploy gate would find no tests.

## What Changes

- The package build copies the files from `src/` instead of the repo root. The zip layout is unchanged: modules sit flat at the zip root, so the handler stays `lambda_function.lambda_handler`.
- Exclusions become `src/tests` (named as a directory) plus `__main__.py` and `selenium_pa.py`. `__init__.py` no longer exists, so it drops off the list.
- The deploy pipeline's test stage runs the tests from `src/tests` with `src/` on the import path.
- The README's test command and file layout table, and the `lambda-deployment` spec's wording about top-level files and `tests/`, are updated to the new layout.

No change to what ships: the same app modules reach the zip.

## Capabilities

### New Capabilities

### Modified Capabilities
- `lambda-deployment`: "Package only runtime dependencies and app code" now sources app code from `src/` and excludes `src/tests`; "Tests gate the deploy" runs the tests from their new location.

## Impact

- `scripts/build-lambda.sh` (copy loop and exclusion list)
- `scripts/deploy-lambda.sh` (`run_tests`)
- `README.md` (Tests section, Layout table)
- `openspec/specs/lambda-deployment/spec.md` (via delta)
- `scripts/lambda_build.py`, `deploy/lambda.json` and the Lambda handler path are unaffected.
