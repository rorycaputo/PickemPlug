# Design

## Context

See proposal.md (Why). Constraints:

- `deploy/lambda.json` already holds `function_name` and `region`; `scripts/lambda_build.py` already loads and validates it, and the deploy scripts set the style (`set -euo pipefail`, `MSYS_NO_PATHCONV=1`, run from repo root, AWS settings only from `.env`, `--check`). Git Bash on Windows, no `jq`.
- The function reads only `fetch_*` booleans from the event and ignores other keys; a non-boolean fails the run (`RunConfig.from_event`). All default to true, so an empty payload means a full live fetch. A full live run from Lambda has been run successfully (about 6 s).
- The `live` alias is created by the deploy pipeline after a passing smoke invoke.
- The existing environment variables (`PICKEM_STORAGE`, `PICKEM_BUCKET`, `DISPLAY_TZ`) are function configuration, already enforced by the deploy; they are not trigger inputs.
- EventBridge rules take exactly one schedule expression, use UTC only, and have no end date.

## Goals / Non-Goals

**Goals:**
- One command applies all schedules from a local file; re-running is safe.
- The triggers can only ever run a verified version.
- The runs stop by themselves after the regular season.

**Non-Goals:**
- No IAM role creation, no CloudFormation/SAM, no changes to `deploy-lambda.sh` or the function.
- No failure alerting.
- No scheduling for next season.

## Decisions

### EventBridge rules, not EventBridge Scheduler
A rule with a Lambda target needs only a resource-based permission on the function, so no IAM role is created, which matches the pipeline's "role untouched" stance. Scheduler would need a new invocation role, but has a native end date and timezone. Trade-offs of rules: UTC only (not an issue here, see below) and no end date (see "Ending the season").

### A list of schedules, one rule each
A rule holds one expression, so each entry in the config becomes its own rule, named by the entry's `name`. The script identifies the rules it manages by name prefix `pickem-` plus a description that starts with `Runs <function>:live (managed by scripts/deploy-schedule.sh`, and deletes managed rules that are no longer listed (and their permission statements). Rules it didn't create are never touched.

### Files

| Path | Role |
|------|------|
| `deploy/schedule.json` | Checked-in trigger config |
| `scripts/deploy-schedule.sh` | Applies it; `--check`, `--disable` |
| `scripts/lambda_build.py` | Gains `schedule` and `event-json` subcommands that validate the file and print values (reusing `load_config` for function name and region) |

### Config shape

```json
{
  "schedules": [
    {
      "name": "pickem-thu-8am-novdec",
      "note": "Thursday 8 am Central",
      "schedule": "cron(0 14 ? NOV,DEC THU 2026)",
      "enabled": true,
      "event": {"fetch_pickem": true, "fetch_draftkings": true, "fetch_espnbet": true, "fetch_oddshark": true}
    }
  ]
}
```

`event` is sent as the target's constant input. Validation lives in the helper and runs before any AWS call: `schedules` is a non-empty list; each `name` matches `pickem-[A-Za-z0-9._-]{1,57}` and is unique; `schedule` is `cron(...)` or `rate(...)`; `enabled` is boolean; `note`, if present, is a string; `event` keys are limited to the four options with boolean values; the deploy config's secret-key deny list is applied to every event key.

### Times and the season end (UTC, no daylight saving)
From Nov 1, 2026 to March 2027 Central is on standard time (UTC-6), so every run's UTC time is fixed:

| Run | UTC | Cron days |
|-----|-----|-----------|
| Thu 8 am Central | 14:00 Thu | Thursdays |
| Thu 6 pm Central | 00:00 the next day | Fridays (including Fri Jan 1, 2027 for Thu Dec 31) |
| Sun 8 am Central | 14:00 Sun | Sundays |

### Ending the season
Rules can't expire, so each run is split into two rules: a day-of-week cron for November and December 2026, and an exact-date cron for January 2027, which is where the runs stop:

| Name | Expression | Last firing |
|------|------------|-------------|
| `pickem-thu-8am-novdec` | `cron(0 14 ? NOV,DEC THU 2026)` | Thu Dec 31 |
| `pickem-thu-8am-jan` | `cron(0 14 7 JAN ? 2027)` | Thu Jan 7 |
| `pickem-thu-6pm-novdec` | `cron(0 0 ? NOV,DEC FRI 2026)` | Thu Dec 24 evening (Fri Dec 25 00:00Z) |
| `pickem-thu-6pm-jan` | `cron(0 0 1,8 JAN ? 2027)` | Thu Jan 7 evening (Fri Jan 8 00:00Z) |
| `pickem-sun-8am-novdec` | `cron(0 14 ? NOV,DEC SUN 2026)` | Sun Dec 27 |
| `pickem-sun-8am-jan` | `cron(0 14 3,10 JAN ? 2027)` | Sun Jan 10 |

The regular season's final games are Sat Jan 9 and Sun Jan 10, 2027, so Week 18's last useful runs are Thu Jan 7 and Sun Jan 10. The Thursday Dec 31 evening run is Jan 1, 00:00Z, so it sits in the January rule. Cron can't combine a day-of-month with a day-of-week, which is why January uses dates.

Alternatives considered: the handler skipping runs after an end date (needs an app change and redeploy; rules keep firing), and the script disabling expired rules (relies on someone re-running it). Chosen because the stop is in the schedules themselves and needs no code.

### Apply steps
1. Load and validate both configs; region and function name come from `deploy/lambda.json`.
2. Check `live` exists (`lambda get-alias`); otherwise fail with "deploy first".
3. For each schedule: `events put-rule` (an idempotent upsert); add the invoke permission on qualifier `live` (statement id `pickem-schedule-<name>`, principal `events.amazonaws.com`, source ARN the rule's ARN) unless `lambda get-policy --qualifier live` already lists it; `events put-targets` with one target (id `live`, the alias ARN, the event JSON as input); then remove any other target on the rule.
4. List managed rules (`events list-rules --name-prefix pickem-`, filtered by description); for each one not in the config, remove its targets, delete the rule and remove its permission statement.
5. Print each rule's state, schedule and payload.

`--disable` sets every rule to DISABLED regardless of the file's `enabled`. `--check` runs steps 1 and 2, then describes the rules and their targets (including managed rules that would be removed) without writing.

Alternative considered: folding this into `deploy-lambda.sh`. Rejected: the triggers change on a different cadence than the code, and a code deploy shouldn't silently re-enable a paused schedule.

## Risks / Trade-offs

- [The Pickem session in SSM expires and live runs fail] → Out of scope; the run errors visibly in CloudWatch logs. Refresh it with `scripts/upload-pickem-auth.sh`.
- [A paused trigger is forgotten] → `--check` shows each state; the next normal run re-enables per the file.
- [Explicit dates are easy to get wrong] → The table above is the reference, and the `--check` output shows each expression; the first firing is Thursday Nov 12.
- [Six rules and six policy statements] → Well within limits; all are removed by deleting them from the file.
- [Operator IAM lacks events permissions] → The script surfaces the failing AWS call; the README lists the needed actions.

## Migration Plan

1. Edit `deploy/schedule.json`.
2. Make sure a deploy has created `live`.
3. Run `bash scripts/deploy-schedule.sh --check`, then `bash scripts/deploy-schedule.sh`. The earlier single `pickem-schedule` rule is removed by the same run, because it is managed and no longer listed.
4. Rollback: `bash scripts/deploy-schedule.sh --disable`.

## Open Questions

None.
