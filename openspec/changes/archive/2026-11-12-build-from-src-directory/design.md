# Design

## Context

The build (`scripts/build-lambda.sh`) installs Linux wheels into `$RUN_DIR/pkg`, then copies `*.py` from the repo root into it, skipping an `EXCLUDE` list. `scripts/lambda_build.py package` then zips `pkg/` as-is. The deploy script's test stage runs `python -m unittest discover tests`. Imports in `src/` are bare (`import apis`), so the code only works with `src/` on `sys.path`: the flat zip root on Lambda, `python src` locally. See proposal.md for motivation.

Only `build-lambda.sh` and `run_tests` in `deploy-lambda.sh` reference the old layout. `lambda_build.py` zips whatever is in `pkg/` and needs no change.

## Goals / Non-Goals

**Goals:**
- Zip contents identical to today's: same modules, flat at the root.
- A test stage that fails loudly if it can't find or import the tests.

**Non-Goals:**
- Turning `src/` into an importable package or changing the handler path.
- Changing `lambda_build.py`, `deploy/lambda.json` or the schedule scripts.

## Decisions

**Copy `src/*.py` non-recursively, with the exclusion list kept as a file-name list.** `src/tests` is a subdirectory, so a non-recursive `*.py` glob already leaves it out. The directory is still named explicitly in the script's exclusion handling so the intent is visible and a future recursive copy keeps it excluded. Alternative: `cp -r src` plus deleting `tests`; rejected because it would also pick up `__pycache__` and any future non-code files, which the spec says must not ship.

**Drop `__init__.py` from the exclusion list.** The file was deleted along with the move to bare imports. Keeping a name for a file that cannot exist invites confusion.

**Fail the build if `src/` has no files to copy or is missing.** An unmatched glob would silently produce an app-less zip. A guard that errors when nothing was copied costs a few lines. (The deploy smoke invoke would also catch it, but only after upload.)

**Run tests with `src/` on the import path via `PYTHONPATH=src`, discovering from `src/tests`.** Mirrors how the app runs, and works with the tests' bare imports. Alternatives: `discover -s src/tests -t src`, rejected because `src/tests` has no `__init__.py`; adding one just for the runner is more structure than needed.

**Guard against zero tests discovered.** `unittest discover` exits 0 when it finds nothing, which would turn the gate into a no-op if the path were ever wrong again. The test stage checks the run discovered at least one test.

## Risks / Trade-offs

- [A `src/` helper added in a subdirectory would be left out of the zip] → The non-recursive copy matches today's top-level-only behavior; a subpackage would need a deliberate build change and a spec update.
- [Windows `PYTHONPATH` handling under Git Bash] → Set it inline for the one command in the bash script, and verify the test stage by running it.
- [Dirty-tree check still counts the unmoved working changes] → Unchanged behavior; deploys need a clean tree or `--allow-dirty` as before.

## Migration Plan

No AWS changes. Verify by running `bash scripts/build-lambda.sh` and comparing the resulting zip's module list to a previous build's `manifest.json`/zip (same `src` modules, no tests). Rollback is reverting the script edits.
