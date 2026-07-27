"""Cortex Analyst stack.

    POST /ask  ->  API Gateway
                       |  (same demo token authorizer pattern as IngestStack)
                       v
                   analyst Lambda
                       |  1. reads CORTEX_USER key-pair from Secrets Manager
                       |  2. mints a Snowflake JWT (key-pair auth)
                       |  3. POST /api/v2/cortex/analyst/message
                       |     -> Snowflake Cortex Analyst (GOLD.MARTS.SEM_JAFFLE_SECURED)
                       v
                   { interpretation, sql }

The Lambda bundles PyJWT + cryptography + requests via Docker during
`cdk synth / cdk deploy` -- Docker must be running on the build machine.

One post-deploy manual step (run once as ACCOUNTADMIN in Snowflake):
    GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE CORTEX_ROLE;

CDK context keys (cdk.json or -c):
  cortex_source  - fully-qualified semantic view (default: GOLD.MARTS.SEM_JAFFLE_SECURED)
  demo_token     - shared demo bearer token (default: demo-allow-token)
"""

import json

import aws_cdk as cdk
from aws_cdk import CfnOutput, Duration, RemovalPolicy, SecretValue, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

DEFAULT_CORTEX_SOURCE = "GOLD.MARTS.SEM_JAFFLE_SECURED"
DEFAULT_DEMO_TOKEN = "demo-allow-token"  # noqa: S105


class AnalystStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        prefix: str,
        snowflake_account: str,
        cortex_private_key: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        demo_token = self.node.try_get_context("demo_token") or DEFAULT_DEMO_TOKEN
        cortex_source = self.node.try_get_context("cortex_source") or DEFAULT_CORTEX_SOURCE

        # --- Secrets Manager: CORTEX_USER credentials ----------------------------
        # Private key is read from .secrets/cortex_key.p8 at synth time (see app.py).
        # account_identifier and account_url are derived from SNOWFLAKE_ACCOUNT in .env.
        cortex_secret = secretsmanager.Secret(
            self,
            "CortexSecret",
            secret_name=f"{prefix}/snowflake/cortex-connection",
            description="Snowflake key-pair credentials for the Cortex Analyst Lambda.",
            secret_string_value=SecretValue.unsafe_plain_text(
                json.dumps(
                    {
                        "user": "CORTEX_USER",
                        "private_key": cortex_private_key,
                        "key_passphrase": "",
                        "account_identifier": snowflake_account.upper(),
                        "account_url": f"https://{snowflake_account}.snowflakecomputing.com",
                    }
                )
            ),
        )

        # --- Lambda authorizer (same demo token pattern as IngestStack) ----------
        authorizer_fn = lambda_.Function(
            self,
            "AuthorizerFn",
            function_name=f"{prefix}-analyst-authorizer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/authorizer"),
            timeout=Duration.seconds(10),
            environment={"DEMO_TOKEN": demo_token},
        )

        # --- Analyst Lambda (bundled: PyJWT + cryptography + requests) -----------
        # Requires Docker on the build machine; CDK bundles deps into the zip.
        analyst_log_group = logs.LogGroup(
            self,
            "AnalystFnLogGroup",
            log_group_name=f"/aws/lambda/{prefix}-analyst",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        analyst_fn = lambda_.Function(
            self,
            "AnalystFn",
            function_name=f"{prefix}-analyst",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                "lambdas/analyst",
                bundling=cdk.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    platform="linux/amd64",
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output --quiet"
                        " && cp handler.py cortex.py snowflake_execute.py"
                        " snowflake_secrets.py snowflake_auth.py /asset-output",
                    ],
                ),
            ),
            timeout=Duration.seconds(120),
            memory_size=512,
            environment={
                "SNOWFLAKE_SECRET_ARN": cortex_secret.secret_arn,
                "CORTEX_SOURCE": cortex_source,
            },
            log_group=analyst_log_group,
        )
        cortex_secret.grant_read(analyst_fn)

        # --- API Gateway ---------------------------------------------------------
        authorizer = apigw.TokenAuthorizer(
            self,
            "TokenAuthorizer",
            handler=authorizer_fn,
            authorizer_name=f"{prefix}-analyst-authorizer",
            identity_source=apigw.IdentitySource.header("Authorization"),
            results_cache_ttl=Duration.seconds(0),
        )

        api = apigw.RestApi(
            self,
            "AnalystApi",
            rest_api_name=f"{prefix}-analyst-api",
            description="Text-to-SQL API backed by Snowflake Cortex Analyst.",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=20,
                throttling_burst_limit=10,
            ),
        )

        ask_resource = api.root.add_resource("ask")
        ask_resource.add_method(
            "POST",
            apigw.LambdaIntegration(analyst_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM,
        )

        # --- Outputs -------------------------------------------------------------
        CfnOutput(self, "AskEndpoint", value=f"{api.url}ask")
        CfnOutput(self, "CortexSecretArn", value=cortex_secret.secret_arn)
        CfnOutput(self, "CortexSource", value=cortex_source)
