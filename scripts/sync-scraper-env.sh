#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${RER_SESSION_AUTH_API_URL:?Set RER_SESSION_AUTH_API_URL in .env}"
: "${RER_SESSION_AUTH_API_KEY_VALUE:?Set RER_SESSION_AUTH_API_KEY_VALUE in .env}"
: "${SMARTSUITE_API_TOKEN:?Set SMARTSUITE_API_TOKEN in .env}"
: "${SMARTSUITE_ACCOUNT_ID:?Set SMARTSUITE_ACCOUNT_ID in .env}"

environment_file="$(mktemp --suffix=.json)"
trap 'rm -f "$environment_file"' EXIT

python - "$environment_file" <<'PY'
import json
import os
import sys

environment = {
    "Variables": {
        "RER_SESSION_AUTH_API_URL": os.environ["RER_SESSION_AUTH_API_URL"],
        "RER_SESSION_AUTH_API_KEY_VALUE": os.environ["RER_SESSION_AUTH_API_KEY_VALUE"],
        "SMARTSUITE_API_URL": os.environ.get("SMARTSUITE_API_URL", "https://app.smartsuite.com/api/v1"),
        "SMARTSUITE_API_TOKEN": os.environ["SMARTSUITE_API_TOKEN"],
        "SMARTSUITE_ACCOUNT_ID": os.environ["SMARTSUITE_ACCOUNT_ID"],
        "SMARTSUITE_TIMEOUT_SECONDS": os.environ.get("SMARTSUITE_TIMEOUT_SECONDS", "30"),
    }
}

with open(sys.argv[1], "w", encoding="utf-8") as file:
    json.dump(environment, file)
PY

region="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-2}}"
function_name="$(aws cloudformation describe-stack-resource \
  --stack-name rer-api-wrapper \
  --logical-resource-id RERScraperFunction \
  --region "$region" \
  --query 'StackResourceDetail.PhysicalResourceId' \
  --output text)"

aws lambda update-function-configuration \
  --function-name "$function_name" \
  --environment "file://$environment_file" \
  --region "$region" \
  --no-cli-pager >/dev/null

aws lambda wait function-updated --function-name "$function_name" --region "$region"
printf 'RER scraper Lambda environment updated.\n'