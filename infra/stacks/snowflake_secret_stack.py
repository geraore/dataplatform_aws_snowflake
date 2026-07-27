"""Secrets Manager secret holding the Snowflake key-pair connection.

Firehose's Snowflake destination authenticates with key-pair auth. This secret
stores the connection details and private key. The template here ships with
PLACEHOLDER values only; populate the real values after deploy with, e.g.:

    aws secretsmanager put-secret-value \\
        --secret-id <secret-arn> \\
        --secret-string file://snowflake_conn.json

The matching public key must be registered on the Snowflake user
(see snowflake/bootstrap/00_bootstrap.sql).
"""

import json

from aws_cdk import SecretValue, Stack
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class SnowflakeSecretStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        placeholder = json.dumps(
            {
                # Firehose reads `user`, `private_key` and (optional) `key_passphrase`.
                "user": "FIREHOSE_USER",
                "private_key": "REPLACE_ME_WITH_PKCS8_PRIVATE_KEY",
                "key_passphrase": "",
                # Reference only — account/db/schema/table are set on the delivery stream.
                "account_url": "https://REPLACE_ME.snowflakecomputing.com",
                "role": "FIREHOSE_ROLE",
                "database": "BRONZE",
                "schema": "RAW",
                "table": "EVENTS",
            }
        )

        self.secret = secretsmanager.Secret(
            self,
            "SnowflakeConnection",
            secret_name=f"{prefix}/snowflake/firehose-connection",
            description="Snowflake key-pair connection consumed by Firehose (Snowpipe Streaming).",
            secret_string_value=SecretValue.unsafe_plain_text(placeholder),
        )
