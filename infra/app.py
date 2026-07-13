#!/usr/bin/env python3
"""CDK entry point for the AWS + Snowflake data platform demo.

Stacks:
  * SnowflakeSecretStack  - Secrets Manager secret with the Snowflake key-pair
                            connection consumed by Firehose.
  * IngestStack           - API Gateway, Lambda authorizer, router Lambda,
                            EventBridge event bus, Firehose -> Snowflake
                            (+ S3 backup).

Orchestration runs on local Airflow (see airflow/run_airflow_local.sh); the
managed MWAA environment was dropped to avoid its standing cost. The VPC stack
went with it -- the remaining managed services (Firehose, Lambda, EventBridge)
do not run inside the VPC, so nothing here needs one.

Configuration is read from CDK context (cdk.json / -c flags) with sensible
demo defaults. Nothing secret is hard-coded here.
"""

from pathlib import Path

import aws_cdk as cdk
from dotenv import dotenv_values
from stacks.analyst_stack import AnalystStack
from stacks.ingest_stack import IngestStack
from stacks.snowflake_secret_stack import SnowflakeSecretStack

# Configuration is loaded from the repo-root .env via python-dotenv (no defaults
# baked into code, no direct os.environ access). See .env.example for the keys.
config = dotenv_values(Path(__file__).resolve().parents[1] / ".env")

repo_root = Path(__file__).resolve().parents[1]

app = cdk.App()

# A short prefix so all resource names are recognisable in the console.
prefix = app.node.try_get_context("prefix") or "dataplatform"

env = cdk.Environment(
    account=config["CDK_DEFAULT_ACCOUNT"],
    region=config["CDK_DEFAULT_REGION"],
)

snowflake_secret = SnowflakeSecretStack(app, f"{prefix}-snowflake-secret", prefix=prefix, env=env)

ingest = IngestStack(
    app,
    f"{prefix}-ingest",
    prefix=prefix,
    snowflake_secret=snowflake_secret.secret,
    env=env,
)

# Read the CORTEX_USER private key generated at .secrets/cortex_key.p8.
# The matching public key is registered on CORTEX_USER by the schemachange
# migration V1.1.8__cortex_analyst_setup.sql.
cortex_private_key = (repo_root / ".secrets" / "cortex_key.p8").read_text()

analyst = AnalystStack(
    app,
    f"{prefix}-analyst",
    prefix=prefix,
    snowflake_account=config["SNOWFLAKE_ACCOUNT"],
    cortex_private_key=cortex_private_key,
    env=env,
)

cdk.Tags.of(app).add("project", prefix)
cdk.Tags.of(app).add("managed-by", "cdk")

app.synth()
