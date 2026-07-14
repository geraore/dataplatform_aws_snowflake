"""Ingestion pipeline.

    POST /events  -> API Gateway
                     |  (Lambda authorizer validates a dummy bearer token)
                     v
                  Router Lambda  -> EventBridge event bus
                                        |  (two rules, same pattern)
                                        |
                                        +---> Firehose (DirectPut) --> Snowflake
                                        |
                                        +---> Firehose (DirectPut) --> S3 (raw event store)
                                                  prefix: events/<event_type>/<yyyy>/<MM>/<dd>/

The event bus decouples the ingest API from delivery targets: the router just
publishes events, and rules forward them. S3 is the raw event store partitioned
by CloudEvents `type`; Snowflake is the queryable layer built on top of it.
Extra consumers can be added as new rules without touching the producer.

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
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kinesisfirehose as firehose
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

# Marker on every event the router publishes; the delivery rule matches on it.
EVENT_SOURCE = "dataplatform.ingest"

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
        snowflake_event_types: list[str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        demo_token = self.node.try_get_context("demo_token") or DEFAULT_DEMO_TOKEN

        # --- EventBridge event bus -----------------------------------------------
        bus = events.EventBus(
            self,
            "EventBus",
            event_bus_name=f"{prefix}-events",
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
            environment={
                "EVENT_BUS_NAME": bus.event_bus_name,
                "EVENT_SOURCE": EVENT_SOURCE,
            },
        )
        bus.grant_put_events_to(router_fn)

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
        events_resource = api.root.add_resource("events")
        events_resource.add_method(
            "POST",
            apigw.LambdaIntegration(router_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM,
        )

        # --- S3 raw event store --------------------------------------------------
        events_bucket = s3.Bucket(
            self,
            "EventsBucket",
            bucket_name=f"{prefix}-events-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # --- Firehose: DirectPut -> Snowflake ------------------------------------
        # AWS CloudFormation requires s3_configuration on Snowflake destinations
        # regardless of backup mode — this bucket captures delivery failures only.
        sf_failures_bucket = s3.Bucket(
            self,
            "SfFailuresBucket",
            bucket_name=f"{prefix}-sf-failures-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

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
        s3_events_log_stream = logs.LogStream(
            self,
            "S3EventsLogStream",
            log_group=firehose_log_group,
            log_stream_name="events-s3-delivery",
        )

        firehose_role = iam.Role(
            self,
            "FirehoseRole",
            role_name=f"{prefix}-firehose-role",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
        )
        events_bucket.grant_read_write(firehose_role)
        sf_failures_bucket.grant_read_write(firehose_role)
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
            "SnowflakeDelivery",
            delivery_stream_name=f"{prefix}-snowflake-delivery",
            delivery_stream_type="DirectPut",
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
                    s3_backup_mode="FailedDataOnly",
                    s3_configuration=(
                        firehose.CfnDeliveryStream.S3DestinationConfigurationProperty(
                            bucket_arn=sf_failures_bucket.bucket_arn,
                            role_arn=firehose_role.role_arn,
                            prefix="delivery-failures/!{timestamp:yyyy}/!{timestamp:MM}/!{timestamp:dd}/",
                            error_output_prefix="delivery-errors/!{firehose:error-output-type}/!{timestamp:yyyy}/!{timestamp:MM}/!{timestamp:dd}/",
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

        # --- Firehose: DirectPut -> S3 raw event store ---------------------------
        # ExtendedS3DestinationConfiguration is required for dynamic partitioning.
        # MetadataExtraction pulls `type` from each CloudEvent (JMESPath) and maps
        # it to `event_type`, which is substituted into the prefix.
        # AWS requires a minimum 64 MB buffer when dynamic partitioning is enabled.
        s3_events_stream = firehose.CfnDeliveryStream(
            self,
            "ToS3Events",
            delivery_stream_name=f"{prefix}-events-s3",
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=(
                firehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                    bucket_arn=events_bucket.bucket_arn,
                    role_arn=firehose_role.role_arn,
                    prefix="events/!{partitionKeyFromQuery:event_type}/!{timestamp:yyyy}/!{timestamp:MM}/!{timestamp:dd}/",
                    error_output_prefix="events/errors/!{firehose:error-output-type}/!{timestamp:yyyy}/!{timestamp:MM}/!{timestamp:dd}/",
                    compression_format="GZIP",
                    buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                        interval_in_seconds=60,
                        size_in_m_bs=64,
                    ),
                    dynamic_partitioning_configuration=(
                        firehose.CfnDeliveryStream.DynamicPartitioningConfigurationProperty(
                            enabled=True,
                            retry_options=firehose.CfnDeliveryStream.RetryOptionsProperty(
                                duration_in_seconds=300,
                            ),
                        )
                    ),
                    processing_configuration=(
                        firehose.CfnDeliveryStream.ProcessingConfigurationProperty(
                            enabled=True,
                            processors=[
                                firehose.CfnDeliveryStream.ProcessorProperty(
                                    type="MetadataExtraction",
                                    parameters=[
                                        firehose.CfnDeliveryStream.ProcessorParameterProperty(
                                            parameter_name="MetadataExtractionQuery",
                                            parameter_value="{event_type: .type}",
                                        ),
                                        firehose.CfnDeliveryStream.ProcessorParameterProperty(
                                            parameter_name="JsonParsingEngine",
                                            parameter_value="JQ-1.6",
                                        ),
                                    ],
                                )
                            ],
                        )
                    ),
                    cloud_watch_logging_options=(
                        firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
                            enabled=True,
                            log_group_name=firehose_log_group.log_group_name,
                            log_stream_name=s3_events_log_stream.log_stream_name,
                        )
                    ),
                )
            ),
        )
        s3_events_stream.node.add_dependency(firehose_role)

        # --- Rules: event bus -> Firehose ----------------------------------------
        # The router sets DetailType = CloudEvents `type`, so we can route on it.
        # snowflake_event_types (from routing.yaml) go to Snowflake; everything
        # else goes to S3 only.
        delivery_rule = events.Rule(
            self,
            "ToFirehoseRule",
            rule_name=f"{prefix}-to-firehose",
            event_bus=bus,
            event_pattern=events.EventPattern(
                source=[EVENT_SOURCE],
                detail={"type": snowflake_event_types},
            ),
        )
        delivery_rule.add_target(
            targets.KinesisFirehoseStream(
                delivery_stream,
                message=events.RuleTargetInput.from_event_path("$.detail"),
            )
        )

        s3_events_rule = events.Rule(
            self,
            "ToS3EventsRule",
            rule_name=f"{prefix}-to-s3-events",
            event_bus=bus,
            event_pattern=events.EventPattern(
                source=[EVENT_SOURCE],
                detail={"type": [{"anything-but": snowflake_event_types}]},
            ),
        )
        s3_events_rule.add_target(
            targets.KinesisFirehoseStream(
                s3_events_stream,
                message=events.RuleTargetInput.from_event_path("$.detail"),
            )
        )

        # Expose the invoke URL for the verification curl.
        self.api_url = api.url
        CfnOutput(self, "EventsEndpoint", value=f"{api.url}events")
        CfnOutput(self, "EventBusName", value=bus.event_bus_name)
        CfnOutput(self, "EventsBucketName", value=events_bucket.bucket_name)
