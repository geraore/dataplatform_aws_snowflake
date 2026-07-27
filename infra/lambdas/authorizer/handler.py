"""Token Lambda authorizer.

Demo behaviour: allow the request only when the ``Authorization`` header
matches the token stored in Secrets Manager. Real deployments would validate
a JWT or look up an API key here.
"""

import os

import boto3

_sm = boto3.client("secretsmanager")
# Fetched once at cold start; cached for the lifetime of the execution environment.
DEMO_TOKEN = _sm.get_secret_value(SecretId=os.environ["DEMO_TOKEN_SECRET_ARN"])["SecretString"]


def _policy(principal_id: str, effect: str, resource: str) -> dict:
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource,
                }
            ],
        },
    }


def handler(event, context):
    # API Gateway TOKEN authorizer passes the header value in authorizationToken.
    token = (event.get("authorizationToken") or "").removeprefix("Bearer ").strip()
    method_arn = event.get("methodArn", "*")

    if token == DEMO_TOKEN:
        return _policy("demo-user", "Allow", method_arn)

    # Returning an explicit Deny yields a 403; raising "Unauthorized" yields 401.
    return _policy("anonymous", "Deny", method_arn)
