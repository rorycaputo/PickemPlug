# Proposal

## Why

The `pickem` function and its `live` alias deploy from the repo, but nothing invokes it. The schedule has to be set by hand in the console, so it can drift and isn't recorded anywhere. The triggers should be defined in a checked-in file and applied by a script, like the function configuration already is. The pickem needs several runs a week at different times (Thursday morning, Thursday evening, Sunday morning), and the runs should stop after the regular NFL season.

## What Changes

- Add `deploy/schedule.json`: a list of schedules, each with a name, a schedule expression, an enabled flag and the event payload sent to the function (the `fetch_*` booleans).
- Add `scripts/deploy-schedule.sh`: creates or updates one EventBridge rule per listed schedule, each invoking `pickem:live`, and deletes managed rules that are no longer listed. It validates the config, shows what it will set, and applies it. It supports `--disable` and `--check` (validate and show the current state, no changes).
- Each rule's expression uses explicit dates for the end of the season, because EventBridge rules have no end date: day-of-week crons through December plus exact-date crons for the January dates, so the schedules stop on their own after the regular season (final games Sun Jan 10, 2027).
- Allow the Lambda resource policy to let EventBridge invoke the `live` alias (the script adds one statement per rule, and removes it when it removes the rule).
- Document the trigger inputs and the script in the README.
- No change to the function code, `deploy/lambda.json` or its environment variables. The existing `PICKEM_STORAGE`, `PICKEM_BUCKET` and `DISPLAY_TZ` are already applied by the deploy pipeline and are not trigger inputs.
- Scheduling next season is out of scope.

## Capabilities

### New Capabilities
- `lambda-schedule-trigger`: a checked-in list of schedules and a script that applies each as an EventBridge rule targeting `pickem:live`.

### Modified Capabilities
<!-- None: the deploy pipeline's requirements are unchanged; the trigger is a separate script. -->

## Impact

- New files: `deploy/schedule.json`, `scripts/deploy-schedule.sh`, a validation subcommand in `scripts/lambda_build.py`.
- AWS: six EventBridge rules (one target each) and six Lambda resource-policy statements. The earlier single `pickem-schedule` rule created while testing is removed. No IAM roles created.
- Operator IAM needs `events:PutRule`, `PutTargets`, `RemoveTargets`, `DescribeRule`, `ListRules`, `ListTargetsByRule`, `DeleteRule`, and `lambda:AddPermission`, `RemovePermission`, `GetPolicy`.
- README.
