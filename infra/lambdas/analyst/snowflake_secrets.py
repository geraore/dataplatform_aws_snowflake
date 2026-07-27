import json
import os

import boto3

SECRET_ARN = os.environ["SNOWFLAKE_SECRET_ARN"]

_sm = boto3.client("secretsmanager")
_cache: dict | None = None


def get() -> dict:
    global _cache
    if _cache is None:
        resp = _sm.get_secret_value(SecretId=SECRET_ARN)
        _cache = json.loads(resp["SecretString"])
    return _cache
