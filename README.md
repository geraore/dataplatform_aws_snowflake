# dataplatform_aws_snowflake

A presentation demo of a **modern data architecture** on AWS + Snowflake, wired end-to-end:

```
client ──POST /events──▶ API Gateway ──(Lambda authorizer: dummy token)
                              │
                              ▼
                        Router Lambda ──▶ Kinesis Data Stream ──▶ Firehose
                                                                     │
                                              ┌──────────────────────┴───────────────────┐
                                              ▼                                            ▼
                                   Snowflake (Snowpipe Streaming)              S3 backup bucket (AllData)
                                   BRONZE.RAW.EVENTS

         Local Airflow ── orchestrates ──▶ dbt (jaffle shop) ──▶ BRONZE / SILVER / GOLD
                                                                  + native Snowflake semantic views

         schemachange ── version-controls ──▶ databases, roles, dbt user, ABAC governance
```

## Monorepo layout

| Path | What |
|------|------|
| [infra/](infra/) | AWS infrastructure as code — **CDK (Python, managed with `uv`)**. API Gateway, Lambda authorizer + router, Kinesis, Firehose→Snowflake, secrets. |
| [snowflake/](snowflake/) | **schemachange** — version-controlled Snowflake DDL: medallion databases, database roles, dbt user, security schema + ABAC policies. |
| [dbt/](dbt/) | The **jaffle shop** dbt project targeting Snowflake, plus native semantic views. |
| [airflow/](airflow/) | DAGs + `requirements.txt` mounted by the local Airflow stack. |
| [scripts/](scripts/) | `run_airflow_local.sh` + docker-compose for a local Airflow that connects to the project. |
| [.github/workflows/](.github/workflows/) | CI: `ruff` + `sqlfluff` + `dbt parse` on every PR. |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python tooling), Python 3.11+
- Node.js + [AWS CDK](https://docs.aws.amazon.com/cdk/) v2 (`npm i -g aws-cdk`)
- An AWS account with credentials configured, and a Snowflake account
- Docker (for local Airflow)

## Quickstart

```bash
# 1. Snowflake foundations (run bootstrap once as ACCOUNTADMIN, then schemachange)
cd snowflake && cat bootstrap/00_bootstrap.sql   # review, run as ACCOUNTADMIN
schemachange deploy --config-folder .

# 2. Infrastructure
cd ../infra && uv sync
uv run cdk bootstrap          # first time per account/region
uv run cdk deploy --all

# 3. dbt
cd ../dbt/jaffle_shop && dbt deps && dbt seed && dbt build
dbt run-operation create_semantic_views

# 4. Local Airflow (orchestration)
cd ../.. && ./scripts/run_airflow_local.sh
```

> **Cost note:** Orchestration runs on local Airflow (Docker), so there is no managed MWAA cost — and with MWAA gone, the VPC/NAT stack was dropped too. The only standing AWS spend is Kinesis + Firehose. Tear it down after the demo with `uv run cdk destroy --all` in `infra/`.

See each subdirectory's `README.md` for details.
