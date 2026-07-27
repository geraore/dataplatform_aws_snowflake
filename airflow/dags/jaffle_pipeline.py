"""Demo orchestration DAG.

Runs daily:
  1. sanity-check the Snowflake connection (reads from the secrets backend),
  2. build the dbt jaffle shop project via **Cosmos** (a task per seed/model/test),
     including the native Snowflake semantic view.

The dbt build is orchestrated with astronomer-cosmos, which parses the dbt
project and renders each resource as its own Airflow task (so seeds, staging
models, marts, the semantic view and tests show up individually in the graph)
instead of a single opaque ``dbt build`` shell call.

The semantic view is a first-class dbt model (materialized via the
Snowflake-Labs/dbt_semantic_view package), so Cosmos schedules it after its
``ref()`` dependencies (the gold marts) with no extra orchestration step.

Cosmos resolves the dbt profile from the project's ``profiles.yml`` (env-var
driven, key-pair auth). The Snowflake connection ``snowflake_default`` is used
only by the connectivity pre-check and is resolved from AWS Secrets Manager on
MWAA, or from the local Airflow metadata DB when run via
airflow/run_airflow_local.sh.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from airflow.operators.bash import BashOperator
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import InvocationMode

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

# Cosmos configuration. Reuse the project's own profiles.yml as the single
# source of truth for how dbt connects to Snowflake (key-pair auth via env vars).
profile_config = ProfileConfig(
    profile_name="jaffle_shop",
    target_name="dev",
    profiles_yml_filepath=Path(DBT_PROFILES_DIR) / "profiles.yml",
)

project_config = ProjectConfig(dbt_project_path=DBT_PROJECT_DIR)

# LOCAL execution via subprocess against the dbt binary in its isolated venv
# (dbt is deliberately not importable in the Airflow env — see the Dockerfile).
execution_config = ExecutionConfig(
    dbt_executable_path=os.environ.get("DBT_EXECUTABLE_PATH", "dbt"),
    invocation_mode=InvocationMode.SUBPROCESS,
)

default_args = {"owner": "data-platform", "retries": 1}

with DAG(
    dag_id="jaffle_pipeline",
    description="Build jaffle shop marts + semantic views on Snowflake (Cosmos)",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["demo", "dbt", "snowflake", "cosmos"],
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

    # Install dbt package dependencies declared in packages.yml.
    # Must run at task time (not image build time) because the dbt project is
    # mounted as a volume and is not available during `docker build`.
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && $DBT_EXECUTABLE_PATH deps --profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    # Cosmos renders one task per dbt resource (seeds -> BRONZE, staging ->
    # SILVER, marts + semantic view -> GOLD, plus tests). Equivalent coverage to
    # `dbt build`; the semantic view builds after the marts it ref()s.
    dbt_build = DbtTaskGroup(
        group_id="dbt_build",
        project_config=project_config,
        profile_config=profile_config,
        execution_config=execution_config,
        render_config=RenderConfig(),
        default_args={"retries": 1},
    )

    check_connection >> dbt_deps >> dbt_build
