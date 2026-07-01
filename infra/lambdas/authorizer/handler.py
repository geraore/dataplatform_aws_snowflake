"""Token Lambda authorizer.

Demo behaviour: allow the request only when the ``Authorization`` header equals
the configured dummy token. Real deployments would validate a JWT / look up an
API key here.
"""

import os

DEMO_TOKEN = os.environ.get("DEMO_TOKEN", "demo-allow-token")


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
