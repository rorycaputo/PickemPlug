#!/usr/bin/env bash
# Apply the pickem Lambda's schedule triggers from deploy/schedule.json. Local, operator-run only.
#
#   bash scripts/deploy-schedule.sh [--check] [--disable]
#
#   --check     validate the config and show the current rules; change nothing
#   --disable   apply the config but leave every rule DISABLED, whatever the file says
#
# Creates or updates one EventBridge rule per schedule in the file, each invoking <function>:live
# with that schedule's event payload, and removes any other target on it. Rules this script
# manages that are no longer in the file are deleted, with their invoke permission. Function
# name and region come from deploy/lambda.json (override the files with LAMBDA_CONFIG and
# SCHEDULE_CONFIG). It does not touch the function's code, configuration, aliases or IAM roles.
set -euo pipefail

export MSYS_NO_PATHCONV=1

cd "$(dirname "${BASH_SOURCE[0]}")/.."

CONFIG=${LAMBDA_CONFIG:-deploy/lambda.json}
SCHEDULE=${SCHEDULE_CONFIG:-deploy/schedule.json}
PYTHON=${PYTHON:-python}
HELPER=scripts/lambda_build.py
ALIAS=live
RULE_PREFIX=pickem-
MANAGED_MARK='managed by scripts/deploy-schedule.sh'

die() { echo "Error: $*" >&2; exit 1; }

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; }

CHECK=0
DISABLE=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    --disable) DISABLE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $arg (see --help)" ;;
  esac
done

# Same reading of .env as the other scripts: only the AWS settings, never sourced.
load_env_var() {
  local name=$1 value
  [ -n "${!name:-}" ] && return 0
  [ -f .env ] || return 0
  value=$(grep -E "^[[:space:]]*(export[[:space:]]+)?${name}=" .env | tail -n 1 \
    | sed -E "s/^[^=]*=//; s/\r$//; s/^[\"']//; s/[\"']$//") || true
  [ -n "$value" ] && export "$name=$value"
  return 0
}

# Fills NAMES, EXPRS, STATES (parallel arrays) and CFG_function_name / CFG_region; validation
# happens here, before any AWS call.
load_config() {
  local out line name expr enabled
  out=$("$PYTHON" "$HELPER" schedule "$SCHEDULE" "$CONFIG") || exit 1
  NAMES=() EXPRS=() STATES=()
  while IFS= read -r line; do
    line=${line%$'\r'}
    case "$line" in
      function_name=*) CFG_function_name=${line#*=} ;;
      region=*) CFG_region=${line#*=} ;;
      *)
        IFS=$'\t' read -r name expr enabled <<< "$line"
        NAMES+=("$name")
        EXPRS+=("$expr")
        if [ "$enabled" = true ] && [ "$DISABLE" -eq 0 ]; then STATES+=(ENABLED); else STATES+=(DISABLED); fi
        ;;
    esac
  done <<< "$out"
}

show_config() {
  local i
  echo "Function: $CFG_function_name:$ALIAS ($CFG_region); EventBridge rules use UTC"
  for i in "${!NAMES[@]}"; do
    printf '  %-24s %-34s %s\n' "${NAMES[$i]}" "${EXPRS[$i]}" "${STATES[$i]}"
  done
}

# The Windows AWS CLI ends text-output lines with CRLF; strip the CR before using values.
strip_cr() { tr -d '\r'; }

lambda() { aws lambda "$@" --region "$CFG_region"; }
events() { aws events "$@" --region "$CFG_region"; }

preflight() {
  command -v aws >/dev/null 2>&1 || die "AWS CLI not found. Install AWS CLI v2 and re-run."

  local out
  out=$(aws sts get-caller-identity --query Account --output text 2>&1) \
    || die "AWS credentials check failed (sts get-caller-identity):
$out"
  echo "AWS account $out"

  ALIAS_ARN=$(lambda get-alias --function-name "$CFG_function_name" --name "$ALIAS" \
    --query AliasArn --output text 2>&1) \
    || die "alias $ALIAS of $CFG_function_name not found; deploy first (bash scripts/deploy-lambda.sh):
$ALIAS_ARN"
  echo "Target $ALIAS_ARN"
}

# Names of the rules this script manages: our prefix, and our mark in the description.
managed_rules() {
  events list-rules --name-prefix "$RULE_PREFIX" \
    --query "Rules[?contains(Description, '$MANAGED_MARK')].Name" --output text | tr '\t' '\n' | strip_cr
}

in_config() {
  local name
  for name in "${NAMES[@]}"; do [ "$name" = "$1" ] && return 0; done
  return 1
}

show_current() {
  local name out note
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    out=$(events describe-rule --name "$name" --query '[ScheduleExpression,State]' --output text | strip_cr)
    note=''
    in_config "$name" || note='  (not in config: would be removed)'
    printf '  %-24s %s%s\n' "$name" "${out//$'\t'/  }" "$note"
    events list-targets-by-rule --rule "$name" --query 'Targets[].[Id,Input]' --output text | sed 's/^/      target: /'
  done < <(managed_rules)
}

apply_one() {
  local name=$1 expr=$2 state=$3 rule_arn sid targets_file extra event

  rule_arn=$(events put-rule --name "$name" --schedule-expression "$expr" --state "$state" \
    --description "Runs $CFG_function_name:$ALIAS ($MANAGED_MARK)" --query RuleArn --output text)

  sid="pickem-schedule-$name"
  if ! lambda get-policy --function-name "$CFG_function_name" --qualifier "$ALIAS" \
      --query Policy --output text 2>/dev/null | grep -q "\"$sid\""; then
    lambda add-permission --function-name "$CFG_function_name" --qualifier "$ALIAS" \
      --statement-id "$sid" --action lambda:InvokeFunction --principal events.amazonaws.com \
      --source-arn "$rule_arn" --query Statement --output text >/dev/null
  fi

  event=$("$PYTHON" "$HELPER" event-json "$SCHEDULE" "$name")
  # A repo-relative path: the Windows AWS CLI can't read Git Bash's /tmp.
  mkdir -p build
  targets_file=build/schedule-targets.json
  "$PYTHON" - "$ALIAS_ARN" "$event" > "$targets_file" <<'PY'
import json, sys
print(json.dumps([{'Id': 'live', 'Arn': sys.argv[1], 'Input': sys.argv[2]}]))
PY
  events put-targets --rule "$name" --targets "file://$targets_file" \
    --query FailedEntryCount --output text | grep -qx 0 || die "put-targets failed for $name"
  rm -f "$targets_file"

  extra=$(events list-targets-by-rule --rule "$name" \
    --query "Targets[?Id!='live'].Id" --output text | tr '\t' ' ' | strip_cr)
  if [ -n "$extra" ]; then
    # shellcheck disable=SC2086
    events remove-targets --rule "$name" --ids $extra >/dev/null
    echo "  $name: removed other targets: $extra"
  fi
  echo "  $name: $state"
}

remove_stale() {
  local name ids
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    in_config "$name" && continue
    ids=$(events list-targets-by-rule --rule "$name" --query 'Targets[].Id' --output text | tr '\t' ' ' | strip_cr)
    # shellcheck disable=SC2086
    [ -z "$ids" ] || events remove-targets --rule "$name" --ids $ids >/dev/null
    events delete-rule --name "$name"
    lambda remove-permission --function-name "$CFG_function_name" --qualifier "$ALIAS" \
      --statement-id "pickem-schedule-$name" 2>/dev/null || true
    echo "  $name: removed (not in config)"
  done < <(managed_rules)
}

load_env_var AWS_PROFILE
load_config
show_config
preflight
echo
if [ "$CHECK" -eq 1 ]; then
  echo "Current rules:"
  show_current
  echo "--check: nothing changed"
  exit 0
fi
echo "Applying:"
for i in "${!NAMES[@]}"; do
  apply_one "${NAMES[$i]}" "${EXPRS[$i]}" "${STATES[$i]}"
done
remove_stale
echo
echo "Current rules:"
show_current
