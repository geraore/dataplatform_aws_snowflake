"""Ingestion pipeline.

    POST /events  -> API Gateway
                     |  (Lambda authorizer validates a dummy bearer token)
                     v
                  Router Lambda  -> Kinesis Data Stream
                                        |
                                        v
                                    Firehose  --> Snowflake (Snowpipe Streaming)
                                              \\-> S3 backup bucket (AllData)

The Snowflake account URL / database / schema / table come from CDK context
(with demo defaults); the user + private key are read at runtime by Firehose
from the Secrets Manager secret created in SnowflakeSecretStack.
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kinesis as kinesis
from aws_cdk import aws_kinesisfirehose as firehose
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

# In a real deployment store this in SSM/Secrets Manager. It is a demo "accept
# anything that matches" token, surfaced via context so it is not committed.
DEFAULT_DEMO_TOKEN = "demo-allow-token"  # noqa: S105


class IngestStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        prefix: str,
        snowflake_secret: secretsmanager.ISecret,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        demo_token = self.node.try_get_context("demo_token") or DEFAULT_DEMO_TOKEN

        # --- Kinesis Data Stream -------------------------------------------------
        stream = kinesis.Stream(
            self,
            "EventStream",
            stream_name=f"{prefix}-events",
            stream_mode=kinesis.StreamMode.ON_DEMAND,
        )

        # --- Lambdas -------------------------------------------------------------
        authorizer_fn = lambda_.Function(
            self,
            "AuthorizerFn",
            function_name=f"{prefix}-authorizer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/authorizer"),
            timeout=Duration.seconds(10),
            environment={"DEMO_TOKEN": demo_token},
        )

        router_fn = lambda_.Function(
            self,
            "RouterFn",
            function_name=f"{prefix}-router",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/router"),
            timeout=Duration.seconds(15),
            environment={"STREAM_NAME": stream.stream_name},
        )
        stream.grant_write(router_fn)

        # --- API Gateway ---------------------------------------------------------
        authorizer = apigw.TokenAuthorizer(
            self,
            "TokenAuthorizer",
            handler=authorizer_fn,
            authorizer_name=f"{prefix}-authorizer",
            # Header carrying the token; matches the router/authorizer contract.
            identity_source=apigw.IdentitySource.header("Authorization"),
            results_cache_ttl=Duration.seconds(0),  # demo: don't cache allow/deny
        )

        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"{prefix}-api",
            description="Ingestion API for the data platform demo.",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=50,
                throttling_burst_limit=20,
            ),
        )
        events = api.root.add_resource("events")
        events.add_method(
            "POST",
            apigw.LambdaIntegration(router_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM,
        )

        # --- S3 backup bucket (every event archived) -----------------------------
        backup_bucket = s3.Bucket(
            self,
            "EventBackupBucket",
            bucket_name=f"{prefix}-events-backup-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # demo: clean up on destroy
            auto_delete_objects=True,
        )

        # --- Firehose: Kinesis -> Snowflake (+ S3 backup) ------------------------
        firehose_log_group = logs.LogGroup(
            self,
            "FirehoseLogs",
            log_group_name=f"/aws/kinesisfirehose/{prefix}-to-snowflake",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )
        firehose_log_stream = logs.LogStream(
            self,
            "FirehoseLogStream",
            log_group=firehose_log_group,
            log_stream_name="snowflake-delivery",
        )

        firehose_role = iam.Role(
            self,
            "FirehoseRole",
            role_name=f"{prefix}-firehose-role",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
        )
        stream.grant_read(firehose_role)
        backup_bucket.grant_read_write(firehose_role)
        snowflake_secret.grant_read(firehose_role)
        firehose_log_group.grant_write(firehose_role)

        # Snowflake target coordinates (auth comes from Secrets Manager).
        sf_account_url = (
            self.node.try_get_context("snowflake_account_url")
            or "https://REPLACE_ME.snowflakecomputing.com"
        )
        sf_database = self.node.try_get_context("snowflake_database") or "BRONZE"
        sf_schema = self.node.try_get_context("snowflake_schema") or "RAW"
        sf_table = self.node.try_get_context("snowflake_table") or "EVENTS"

        cw_logging = firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
            enabled=True,
            log_group_name=firehose_log_group.log_group_name,
            log_stream_name=firehose_log_stream.log_stream_name,
        )

        delivery_stream = firehose.CfnDeliveryStream(
            self,
            "ToSnowflake",
            delivery_stream_name=f"{prefix}-to-snowflake",
            delivery_stream_type="KinesisStreamAsSource",
            kinesis_stream_source_configuration=(
                firehose.CfnDeliveryStream.KinesisStreamSourceConfigurationProperty(
                    kinesis_stream_arn=stream.stream_arn,
                    role_arn=firehose_role.role_arn,
                )
            ),
            snowflake_destination_configuration=(
                firehose.CfnDeliveryStream.SnowflakeDestinationConfigurationProperty(
                    account_url=sf_account_url,
                    database=sf_database,
                    schema=sf_schema,
                    table=sf_table,
                    role_arn=firehose_role.role_arn,
                    # Auth (user + private key) is read from Secrets Manager.
                    secrets_manager_configuration=(
                        firehose.CfnDeliveryStream.SecretsManagerConfigurationProperty(
                            enabled=True,
                            secret_arn=snowflake_secret.secret_arn,
                            role_arn=firehose_role.role_arn,
                        )
                    ),
                    # Land the whole event into one VARIANT column + metadata,
                    # matching BRONZE.RAW.EVENTS (snowflake/V1.1.6).
                    data_loading_option="VARIANT_CONTENT_AND_METADATA_MAPPING",
                    content_column_name="record_content",
                    meta_data_column_name="record_metadata",
                    s3_backup_mode="AllData",
                    s3_configuration=(
                        firehose.CfnDeliveryStream.S3DestinationConfigurationProperty(
                            bucket_arn=backup_bucket.bucket_arn,
                            role_arn=firehose_role.role_arn,
                            prefix="events/",
                            error_output_prefix="errors/",
                            compression_format="GZIP",
                            buffering_hints=(
                                firehose.CfnDeliveryStream.BufferingHintsProperty(
                                    interval_in_seconds=60,
                                    size_in_m_bs=5,
                                )
                            ),
                        )
                    ),
                    cloud_watch_logging_options=cw_logging,
                )
            ),
        )
        delivery_stream.node.add_dependency(firehose_role)

        # Expose the invoke URL for the verification curl.
        self.api_url = api.url
        CfnOutput(self, "EventsEndpoint", value=f"{api.url}events")
        CfnOutput(self, "EventBackupBucketName", value=backup_bucket.bucket_name)
        CfnOutput(self, "EventStreamName", value=stream.stream_name)
