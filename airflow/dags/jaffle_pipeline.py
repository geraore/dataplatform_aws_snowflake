"""Demo orchestration DAG.

Runs daily:
  1. sanity-check the Snowflake connection (reads from the secrets backend),
  2. build the dbt jaffle shop models,
  3. (re)create the semantic views.

The Snowflake connection ``snowflake_default`` is resolved from AWS Secrets
Manager on MWAA, and from the local Airflow metadata DB when run via
scripts/run_airflow_local.sh. The same DAG file is used in both places.
"""

from __future__ import annotations

import os
from datetime import datetime

from airflow.operators.bash import BashOperator

from airflow import DAG

try:
    # Provider is present on MWAA and in the local image's requirements.
    from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

    _HAS_SNOWFLAKE = True
except ImportError:  # keep the DAG importable even without the provider
    _HAS_SNOWFLAKE = False

# Where the dbt project lives. On MWAA we ship it under the DAGs bucket; locally
# the compose file mounts the repo's dbt/ folder here.
DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/usr/local/airflow/dbt/jaffle_shop")
DBT_PROFILES_DIR = os.environ.get("DBT_PROFILES_DIR", DBT_PROJECT_DIR)

default_args = {"owner": "data-platform", "retries": 1}

with DAG(
    dag_id="jaffle_pipeline",
    description="Build jaffle shop marts + semantic views on Snowflake",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["demo", "dbt", "snowflake"],
) as dag:
    if _HAS_SNOWFLAKE:
        check_connection = SnowflakeOperator(
            task_id="check_snowflake",
            snowflake_conn_id="snowflake_default",
            sql="SELECT CURRENT_VERSION();",
        )
    else:
        check_connection = BashOperator(
            task_id="check_snowflake",
            bash_command="echo 'snowflake provider not installed; skipping check'",
        )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && dbt build --profiles-dir {DBT_PROFILES_DIR} --target dev"
        ),
    )

    dbt_semantic_views = BashOperator(
        task_id="dbt_semantic_views",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt run-operation create_semantic_views --profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    check_connection >> dbt_build >> dbt_semantic_views
