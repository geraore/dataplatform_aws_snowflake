#!/usr/bin/env bash
# Run Airflow locally (docker compose) with the same DAG that runs on MWAA, and
# wire up a Snowflake connection so the DAG can connect to the project.
#
# Usage:
#   export SNOWFLAKE_ACCOUNT=abc-xy123
#   export SNOWFLAKE_USER=DBT_USER
#   export SNOWFLAKE_PASSWORD=...        # or use a private key at .airflow/secrets/dbt_key.p8
#   export SNOWFLAKE_WAREHOUSE=DBT_WH
#   export SNOWFLAKE_DATABASE=GOLD
#   export SNOWFLAKE_ROLE=DBT_ROLE
#   ./scripts/run_airflow_local.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p .airflow/logs .airflow/secrets

: "${SNOWFLAKE_ACCOUNT:?set SNOWFLAKE_ACCOUNT}"
SNOWFLAKE_USER="${SNOWFLAKE_USER:-DBT_USER}"
SNOWFLAKE_WAREHOUSE="${SNOWFLAKE_WAREHOUSE:-DBT_WH}"
SNOWFLAKE_DATABASE="${SNOWFLAKE_DATABASE:-GOLD}"
SNOWFLAKE_ROLE="${SNOWFLAKE_ROLE:-DBT_ROLE}"

# Build the JSON env-connection Airflow reads as `snowflake_default`.
export AIRFLOW_CONN_SNOWFLAKE_DEFAULT
AIRFLOW_CONN_SNOWFLAKE_DEFAULT=$(cat <<JSON
{
  "conn_type": "snowflake",
  "login": "${SNOWFLAKE_USER}",
  "password": "${SNOWFLAKE_PASSWORD:-}",
  "extra": {
    "account": "${SNOWFLAKE_ACCOUNT}",
    "warehouse": "${SNOWFLAKE_WAREHOUSE}",
    "database": "${SNOWFLAKE_DATABASE}",
    "role": "${SNOWFLAKE_ROLE}"
  }
}
JSON
)

echo "Starting local Airflow at http://localhost:8080 (user/password printed by 'standalone')."
echo "DAG: jaffle_pipeline. Snowflake account: ${SNOWFLAKE_ACCOUNT}"

docker compose -f docker-compose.airflow.yml up "$@"
