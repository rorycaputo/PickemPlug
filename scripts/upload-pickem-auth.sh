#!/usr/bin/env bash
# Upload the saved Pickem session (resources/pickem_auth.json) to the SSM SecureString
# /pickemplug/pickem-auth that the Lambda reads. Local, operator-run only.
#
#   bash scripts/upload-pickem-auth.sh           upload (creates the parameter on first run)
#   bash scripts/upload-pickem-auth.sh --check   verify AWS CLI, credentials and SSM; write nothing
set -euo pipefail

# Git Bash would otherwise rewrite /pickemplug/... into a Windows path.
export MSYS_NO_PATHCONV=1

cd "$(dirname "${BASH_SOURCE[0]}")/.."

AUTH_FILE='resources/pickem_auth.json'
PARAM_NAME='/pickemplug/pickem-auth'
REGEN_CMD='python src --no-fetch-draftkings --no-fetch-espnbet --no-fetch-oddshark'

die() { echo "Error: $*" >&2; exit 1; }

# Read only the AWS settings from .env (never source it: it holds the CBS password).
# Values already in the environment win.
load_env_var() {
  local name=$1 value
  [ -n "${!name:-}" ] && return 0
  [ -f .env ] || return 0
  value=$(grep -E "^[[:space:]]*(export[[:space:]]+)?${name}=" .env | tail -n 1 \
    | sed -E "s/^[^=]*=//; s/\r$//; s/^[\"']//; s/[\"']$//") || true
  [ -n "$value" ] && export "$name=$value"
  return 0
}

preflight() {
  command -v aws >/dev/null 2>&1 || die "AWS CLI not found. Install AWS CLI v2 and re-run."

  local identity
  identity=$(aws sts get-caller-identity --query Account --output text 2>&1) \
    || die "AWS credentials check failed (sts get-caller-identity):
$identity"
  ACCOUNT=$identity

  local ssm_out
  ssm_out=$(aws ssm describe-parameters --max-results 1 2>&1) \
    || die "SSM access check failed (ssm describe-parameters):
$ssm_out"

  REGION=${AWS_DEFAULT_REGION:-$(aws configure get region 2>/dev/null || true)}
  REGION=${REGION:-unknown}
}

require_tty() {
  [ -t 0 ] || die "$1
Generate it with:  $REGEN_CMD
then re-run this script."
}

wait_for_regenerate() {
  echo "Run this in another terminal to generate a fresh session:"
  echo "  $REGEN_CMD"
  read -r -p "Press Enter once it has finished (Ctrl-C to cancel)... " _
}

# Seconds-since-epoch of the saved session's expires_at; empty when unreadable.
session_expiry_epoch() {
  local expires
  expires=$(sed -n 's/.*"expires_at"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$AUTH_FILE" | head -n 1)
  [ -n "$expires" ] || return 0
  date -d "$expires" +%s 2>/dev/null || true
}

# Loop until there is a usable auth file; returns when the user is ready to upload it.
ensure_session_file() {
  local expiry choice
  while true; do
    if [ ! -f "$AUTH_FILE" ]; then
      require_tty "$AUTH_FILE does not exist."
      echo "$AUTH_FILE does not exist."
      wait_for_regenerate
      [ -f "$AUTH_FILE" ] || die "$AUTH_FILE still does not exist."
      continue
    fi

    expiry=$(session_expiry_epoch)
    if [ -z "$expiry" ]; then
      date -d "2000-01-01" +%s >/dev/null 2>&1 \
        || echo "Note: 'date -d' unavailable; skipping the session expiry check."
      return 0
    fi
    [ "$expiry" -gt "$(date +%s)" ] && return 0

    require_tty "The saved Pickem session has expired."
    echo "Warning: the saved Pickem session has expired."
    read -r -p "[r]egenerate, [u]pload anyway, or [a]bort? [a] " choice
    case "${choice:-a}" in
      r|R) wait_for_regenerate ;;
      u|U) return 0 ;;
      *) echo "Aborted; nothing was uploaded."; exit 1 ;;
    esac
  done
}

CHECK_ONLY=0
case "${1:-}" in
  --check) CHECK_ONLY=1 ;;
  '') ;;
  *) die "Unknown argument: $1 (only --check is supported)" ;;
esac

load_env_var AWS_DEFAULT_REGION
load_env_var AWS_PROFILE

preflight

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "AWS access OK: account $ACCOUNT, region $REGION."
  exit 0
fi

ensure_session_file

# --value file://... keeps the credential out of the process list and shell history.
version=$(aws ssm put-parameter --name "$PARAM_NAME" --type SecureString --overwrite \
  --value "file://$AUTH_FILE" --query Version --output text)

echo "Uploaded $PARAM_NAME (region $REGION, version $version)."
