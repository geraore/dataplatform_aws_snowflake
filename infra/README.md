# infra/ — AWS CDK (Python + uv)

Infrastructure for the ingestion pipeline.

## Stacks

| Stack | Resources |
|-------|-----------|
| `dataplatform-snowflake-secret` | Secrets Manager secret with the Snowflake key-pair connection for Firehose |
| `dataplatform-ingest` | API Gateway + Lambda authorizer + router Lambda + Kinesis + Firehose→Snowflake (+ S3 backup `AllData`) |

> Orchestration runs on **local Airflow** (`airflow/run_airflow_local.sh`). The
> managed MWAA environment was removed to avoid its standing cost — and with it
> the VPC stack, since none of the remaining managed services (Firehose, Lambda,
> Kinesis) run inside a VPC.

## Setup

```bash
uv sync                      # install aws-cdk-lib, constructs
uv run cdk bootstrap         # once per account/region
uv run cdk synth             # offline validation
uv run cdk deploy --all
```

## Configuration (CDK context)

Override defaults with `-c key=value` or in `cdk.json`'s `context` block:

| Key | Default | Purpose |
|-----|---------|---------|
| `prefix` | `dataplatform` | Name prefix for all resources |
| `demo_token` | `demo-allow-token` | Token the authorizer accepts |
| `snowflake_account_url` | placeholder | Firehose Snowflake destination URL |
| `snowflake_database` / `snowflake_schema` / `snowflake_table` | `BRONZE` / `RAW` / `EVENTS` | Firehose target |

Example:

```bash
uv run cdk deploy --all \
  -c snowflake_account_url=https://abc-xy123.snowflakecomputing.com
```

## After deploy

1. Register the Snowflake public key on `FIREHOSE_USER` (see `snowflake/bootstrap`).
2. Populate the connection secret with real values. The Firehose key pair is
   generated into the repo's gitignored `.secrets/` and staged as
   `.secrets/firehose_conn.json` (fill in `account_url` first):

   ```bash
   aws secretsmanager put-secret-value \
     --secret-id dataplatform/snowflake/firehose-connection \
     --secret-string file://../.secrets/firehose_conn.json
   ```

   (`snowflake_conn.example.json` shows the expected schema for reference.)

3. Smoke-test the API (URL is in the `dataplatform-ingest` stack outputs):

   ```bash
   curl -XPOST "$API_URL/events" \
     -H "Authorization: demo-allow-token" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "u1", "event": "page_view"}'
   # 202 accepted; a missing/wrong token returns 403
   ```

## Teardown

```bash
uv run cdk destroy --all
```
