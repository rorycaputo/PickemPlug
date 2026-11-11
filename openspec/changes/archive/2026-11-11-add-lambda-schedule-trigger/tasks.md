# Tasks

## 1. Config and validation

- [x] 1.1 Rewrite `deploy/schedule.json` as the list of six schedules in design.md (live payload, all enabled). Verify: the file parses as JSON, contains no secret keys, and the helper accepts it.
- [x] 1.2 Update the `schedule` and `event-json` subcommands in `scripts/lambda_build.py` for the list shape (per design.md validation), with `event-json` taking a schedule name. Verify: a valid file exits 0; a bad cron, an unknown event key, a non-boolean flag, a denied key, an empty list, a bad name and a duplicate name each exit non-zero naming the problem.
- [x] 1.3 Verify the expressions fire when intended: list each expression's firing dates (a quick script, not committed) and confirm they start Thu Nov 12 / Fri Nov 13 00:00Z / Sun Nov 15 and end Thu Jan 7 / Fri Jan 8 00:00Z / Sun Jan 10, with Fri Jan 1 00:00Z (Thu Dec 31 evening) included.

## 2. Script

- [x] 2.1 Update `scripts/deploy-schedule.sh` for the list: preflight (AWS CLI, credentials, `live` exists), per-schedule put-rule, alias-scoped permission when missing, put-targets and removal of extra targets; removal of managed rules (and their permission statements) no longer listed; `--check` and `--disable`. Verify: `--help` prints usage; an unknown flag exits non-zero; `bash -n` passes.
- [x] 2.2 Apply against the real account. Verify: six enabled rules with the expected expressions and payloads, the old `pickem-schedule` rule and its permission removed, `get-policy` shows six schedule statements on `live`, and a second run changes nothing.
- [x] 2.3 Verify `--check` changes nothing and `--disable` leaves every rule's schedule and payload intact with state DISABLED; re-apply to re-enable all six.

## 3. Documentation and checks

- [x] 3.1 Update README: the Schedule section (list shape, the six runs, UTC and season-end notes, the extra operator IAM actions). Verify: the README commands match the script's `--help` and the fields match `deploy/schedule.json`.
- [x] 3.2 Run `pipenv run python -m unittest discover tests` and `openspec validate add-lambda-schedule-trigger`. Verify: both pass.
