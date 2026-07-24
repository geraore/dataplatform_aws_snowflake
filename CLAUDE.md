# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Each subdirectory is an independent Python project managed with `uv`. Always `cd` into the relevant subdirectory before running commands; there is no top-level `uv` workspace.

### Infrastructure (CDK)
```bash
cd infra
uv sync
uv run cdk synth          # offline validation — no AWS calls
uv run cdk deploy --all   # deploy all stacks
uv run cdk destroy --all  # teardown
```

### Snowflake DDL (schemachange)
```bash
# Requires env vars: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_PATH
cd snowflake
uv sync
uv run schemachange deploy --config-folder .
```

### dbt
```bash
cd dbt/jaffle_shop
uv sync
dbt deps
dbt build                         # full run: seeds + staging + marts + semantic + secured
dbt run --select staging          # only staging models
dbt run --select secured          # rebuild secured views and reattach policies
dbt run --select <model_name>     # single model
dbt test --select <model_name>    # single model's tests
```

### Local Airflow (orchestration)
```bash
# From repo root — reads env vars from .env
./airflow/run_airflow_local.sh
# UI at http://localhost:8080 (admin / $AIRFLOW_ADMIN_PASSWORD)
```

### Event simulator
```bash
cd simulators
uv run python simulate.py                   # cycle all event types at 1 evt/s
uv run python simulate.py -e customer       # only customer events
uv run python simulate.py --dry-run         # print CloudEvents without POSTing
```

### Linting (matches CI)
```bash
ruff check infra airflow
ruff format --check infra airflow
sqlfluff lint snowflake/
dbt parse --profiles-dir ci      # from dbt/jaffle_shop/
```

### API integration tests
```bash
cd platform_api_tests
uv run pytest
```

## Architecture

### End-to-end data flow

```
Simulator → POST /events (CloudEvents 1.0)
  → API Gateway (Lambda token authorizer, dummy bearer token)
  → Router Lambda (validates CloudEvents envelope, publishes to EventBridge)
  → EventBridge event bus (dataplatform-events)
       ├── rule: event types in routing.yaml[snowflake] → Firehose → BRONZE.RAW.EVENTS
       └── rule: all other types                        → Firehose → S3 (events bucket)

dbt (orchestrated by Airflow/Cosmos, daily):
  pre-hook COPY from S3 → BRONZE.RAW.<entity>  (raw CloudEvent VARIANT rows)
  → SILVER.STAGING.<entity>  (incremental SCD-1, extracts typed columns from VARIANT)
  → GOLD.MARTS.dim_* / fact_*  (curated tables)
  → GOLD.MARTS.sv_dim_* / sv_fact_*  (secured views, policies attached via post-hooks)
  → GOLD.MARTS.SEM_JAFFLE  (Snowflake native semantic view)
```

### Repository layout

| Path | Role |
|------|------|
| `infra/` | AWS CDK (Python). Stacks: `SnowflakeSecretStack`, `IngestStack`, `AnalystStack` |
| `infra/stacks/ingest_stack.py` | Authorizer Lambda, Router Lambda, EventBridge bus + rules, two Firehose streams, S3 storage-integration IAM role |
| `infra/routing.yaml` | Controls which CloudEvent `type` values are routed to Snowflake vs S3-only |
| `infra/lambdas/router/` | Enforces CloudEvents 1.0 structure; publishes to EventBridge |
| `snowflake/scripts/` | Versioned schemachange DDL; files named `V<version>__<description>.sql` |
| `dbt/jaffle_shop/` | dbt project targeting Snowflake; profiles driven by env vars |
| `dbt/jaffle_shop/macros/` | Key macros (see below) |
| `dbt/jaffle_shop/models/staging/` | Incremental SCD-1 models; source = BRONZE.RAW |
| `dbt/jaffle_shop/models/marts/` | dim_* and fact_* tables in GOLD.MARTS |
| `dbt/jaffle_shop/models/secured/` | Secure views (sv_*) over marts, with ABAC post-hooks |
| `dbt/jaffle_shop/models/semantic_models/` | Native Snowflake semantic view via dbt_semantic_view package |
| `simulators/` | YAML-driven CloudEvents generator; templates in `simulators/events/*.yml` |
| `airflow/dags/jaffle_pipeline.py` | Daily DAG: connectivity check → dbt deps → Cosmos DbtTaskGroup |

### Snowflake database layout

| Database | Schema | Contents |
|----------|--------|----------|
| `BRONZE` | `RAW` | Landing zone: `EVENTS` (Firehose Snowpipe Streaming), per-entity raw tables (COPY from S3), external stage |
| `SILVER` | `STAGING` | Typed incremental tables — one per entity |
| `GOLD` | `MARTS` | Curated dims, facts, secured views, semantic view |
| `GOVERNANCE` | `SECURITY` | `ENTITLEMENTS` table, `V_ENTITLEMENTS` view, masking policy (`MASK_PII_STRING`), row access policies |

### Key dbt macros

**`staging_scd1(unique_key, ...)`** — generates all incremental SCD-1 SQL for a staging model. Column names and types are driven by the model's YAML `columns[].data_type`; CloudEvents envelope fields (`ce_id`, `ce_time`, `ce_type`, etc.) are extracted from the top-level VARIANT; `data.*` fields are extracted from `record_content:data:<col>`. Every staging model calls this macro as its body.

**`copy_raw_events(event_type)`** — runs as a staging model pre-hook; issues a `COPY INTO BRONZE.RAW.<model>` from `@BRONZE.RAW.EVENTS_S3_STAGE/<event_type>/`. Snowflake's LOAD_HISTORY deduplicates by file automatically.

**`apply_column_masking(this, model)`** — post-hook on secured views; reads `columns[].config.meta.security.resource` from the model YAML and attaches `GOVERNANCE.SECURITY.MASK_PII_STRING` to PII columns.

### Governance / ABAC

`GOVERNANCE.SECURITY.ENTITLEMENTS` is the single source of truth. Rows have `(user_id, resource, access_level, object_id)` where `object_id = '*'` means all records. Masking and row-access policies query `V_ENTITLEMENTS` at query time (Snowflake policy context).

Secured views (`models/secured/sv_*.sql`) are Snowflake `SECURE VIEW`s that select directly from the corresponding mart and attach policies via dbt post-hooks. Rebuilding secured views requires `dbt run --select secured`.

### CDK configuration

All non-secret configuration passes through CDK context (`cdk.json` or `-c key=value`). The `.env` file at repo root (see `.env.example`) supplies `CDK_DEFAULT_ACCOUNT`, `CDK_DEFAULT_REGION`, `SNOWFLAKE_ACCOUNT`, and AWS credentials profile. The CDK app reads it via `python-dotenv` at synth time — it is **not** sourced into the shell for CDK.

### S3 storage integration bootstrap (two-step)

The IAM role Snowflake assumes to COPY from S3 requires a chicken-and-egg setup:
1. Deploy CDK → copy the `SnowflakeS3RoleArn` output.
2. Run schemachange `V1.1.9` with that ARN → `DESC INTEGRATION EVENTS_S3_INT` to get `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID`.
3. Add those two values as CDK context keys (`snowflake_iam_user_arn`, `snowflake_external_id`) and redeploy to lock the trust policy.

### Event routing

`infra/routing.yaml` lists the CloudEvent `type` values that fan out to both Firehose streams (Snowflake + S3). Types not on the list go to S3 only. Adding a new type to Snowflake requires updating `routing.yaml` and redeploying the ingest stack.
