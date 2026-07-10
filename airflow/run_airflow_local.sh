#!/usr/bin/env bash
# Run Airflow locally (docker compose), building the image (Airflow + Cosmos in
# one env, dbt in an isolated venv) and wiring up a Snowflake connection so the
# DAG can connect to the project.
#
# Auth is key-pair (as DBT_USER) end to end: both the dbt build (Cosmos, via
# profiles.yml) and the connectivity pre-check (snowflake_default) use the
# private key at .airflow/secrets/dbt_key.p8 -- no account password anywhere.
#
# Usage:
#   export SNOWFLAKE_ACCOUNT=abc-xy123
#   # connection login is always the dbt identity; override only if renamed:
#   #   export DBT_SNOWFLAKE_USER=DBT_USER   (defaults to DBT_USER)
#   # place DBT_USER's PKCS#8 private key at airflow/.airflow/secrets/dbt_key.p8
#   export DBT_PRIVATE_KEY_PASSPHRASE=...   # only if the key is encrypted
#   export SNOWFLAKE_WAREHOUSE=DBT_WH
#   export SNOWFLAKE_DATABASE=GOLD
#   export SNOWFLAKE_ROLE=DBT_ROLE
#   # optional: point at a different host key dir (default: repo-root .secrets/)
#   export HOST_SECRETS_DIR=/path/to/keys
#   # optional: fixed UI admin password (default: admin)
#   export AIRFLOW_ADMIN_PASSWORD=my-secret
#   ./airflow/run_airflow_local.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p .airflow/logs

# Cosmos renders the dbt profile from this file (env-var driven, key-pair auth).
# Seed it from the checked-in example if the developer hasn't created one.
DBT_DIR="$SCRIPT_DIR/../dbt/jaffle_shop"
if [[ ! -f "$DBT_DIR/profiles.yml" ]]; then
  cp "$DBT_DIR/profiles.example.yml" "$DBT_DIR/profiles.yml"
  echo "Seeded $DBT_DIR/profiles.yml from profiles.example.yml"
fi

: "${SNOWFLAKE_ACCOUNT:?set SNOWFLAKE_ACCOUNT}"
# This connection is always the dbt identity, so default the login to DBT_USER
# via DBT_SNOWFLAKE_USER (the same var the dbt profile reads). We deliberately
# ignore SNOWFLAKE_USER here -- .env sets it to SCHEMACHANGE_USER for
# schemachange, which would not match the dbt key.
SNOWFLAKE_USER="${DBT_SNOWFLAKE_USER:-DBT_USER}"
SNOWFLAKE_WAREHOUSE="${SNOWFLAKE_WAREHOUSE:-DBT_WH}"
SNOWFLAKE_DATABASE="${SNOWFLAKE_DATABASE:-GOLD}"
SNOWFLAKE_ROLE="${SNOWFLAKE_ROLE:-DBT_ROLE}"

# The private key is mounted read-only into the container from HOST_SECRETS_DIR
# (compose maps it to /opt/project/secrets, and DBT_PRIVATE_KEY_PATH points at
# dbt_key.p8 there). Default to the repo-root .secrets/ where the keys live.
export HOST_SECRETS_DIR="${HOST_SECRETS_DIR:-../.secrets}"
if [[ ! -f "$HOST_SECRETS_DIR/dbt_key.p8" ]]; then
  echo "ERROR: DBT_USER private key not found at $HOST_SECRETS_DIR/dbt_key.p8" >&2
  echo "       (path is relative to airflow/; override with HOST_SECRETS_DIR)" >&2
  exit 1
fi

# Fixed admin login for the standalone UI (compose seeds it into
# standalone_admin_password.txt so it isn't randomized on each start).
export AIRFLOW_ADMIN_PASSWORD="${AIRFLOW_ADMIN_PASSWORD:-admin}"

# Build the JSON env-connection Airflow reads as `snowflake_default`.
# Key-pair auth: the Snowflake provider loads `private_key_file` (path inside
# the container) and uses the `password` field as the key *passphrase* (empty
# for an unencrypted key), not an account password.
export AIRFLOW_CONN_SNOWFLAKE_DEFAULT
AIRFLOW_CONN_SNOWFLAKE_DEFAULT=$(cat <<JSON
{
  "conn_type": "snowflake",
  "login": "${SNOWFLAKE_USER}",
  "password": "${DBT_PRIVATE_KEY_PASSPHRASE:-}",
  "extra": {
    "account": "${SNOWFLAKE_ACCOUNT}",
    "warehouse": "${SNOWFLAKE_WAREHOUSE}",
    "database": "${SNOWFLAKE_DATABASE}",
    "role": "${SNOWFLAKE_ROLE}",
    "private_key_file": "/opt/project/secrets/dbt_key.p8"
  }
}
JSON
)

echo "Starting local Airflow at http://localhost:8080 (login: admin / ${AIRFLOW_ADMIN_PASSWORD})."
echo "DAG: jaffle_pipeline. Snowflake account: ${SNOWFLAKE_ACCOUNT}"

docker compose -f docker-compose.airflow.yml up --build "$@"
