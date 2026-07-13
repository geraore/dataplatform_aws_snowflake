"""Analyst Lambda.

Receives { "question": "..." } from API Gateway, authenticates to Snowflake
using key-pair JWT auth, and proxies the question to Cortex Analyst.

The Cortex Analyst REST endpoint accepts either:
  - a YAML file in a Snowflake stage:  "@DB.SCHEMA.STAGE/file.yaml"
  - a Snowflake Semantic View:         "DB.SCHEMA.SEM_VIEW_NAME"

Both are set via the CORTEX_SOURCE environment variable. This Lambda uses the
existing GOLD.MARTS.SEM_JAFFLE semantic view so no YAML file is needed.

Response shape returned to the caller:
  {
    "interpretation": "<plain-English explanation from Cortex>",
    "sql":            "<generated SQL statement>"
  }
"""

import base64
import datetime
import hashlib
import json
import os

import boto3
import jwt
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: F401 (type reference)

SECRET_ARN = os.environ["SNOWFLAKE_SECRET_ARN"]
CORTEX_SOURCE = os.environ["CORTEX_SOURCE"]  # e.g. "GOLD.MARTS.SEM_JAFFLE"

_sm = boto3.client("secretsmanager")
_secret_cache: dict | None = None


def _secret() -> dict:
    global _secret_cache
    if _secret_cache is None:
        resp = _sm.get_secret_value(SecretId=SECRET_ARN)
        _secret_cache = json.loads(resp["SecretString"])
    return _secret_cache


def _load_private_key(pem: str, passphrase: str | None):
    pw = passphrase.encode() if passphrase else None
    return serialization.load_pem_private_key(pem.encode(), password=pw)


def _public_key_fingerprint(private_key) -> str:
    """SHA-256 fingerprint of the DER-encoded public key (Snowflake JWT format)."""
    der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return "SHA256:" + base64.b64encode(hashlib.sha256(der).digest()).decode()


def _make_jwt(account: str, user: str, private_key, fingerprint: str) -> str:
    """Mint a Snowflake key-pair JWT valid for 1 hour.

    account: account identifier exactly as returned by SELECT CURRENT_ACCOUNT(),
             uppercased (e.g. "ORGNAME-ACCOUNTNAME" or legacy locator "XY12345").
    """
    account = account.upper()
    user = user.upper()
    qualified = f"{account}.{user}"
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    payload = {
        "iss": f"{qualified}.{fingerprint}",
        "sub": qualified,
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def handler(event, _context):
    body_raw = event.get("body") or "{}"
    try:
        body = json.loads(body_raw)
    except json.JSONDecodeError:
        return _resp(400, {"error": "request body must be JSON"})

    question = (body.get("question") or "").strip()
    if not question:
        return _resp(400, {"error": "'question' field is required"})

    s = _secret()
    private_key = _load_private_key(s["private_key"], s.get("key_passphrase") or None)
    fingerprint = _public_key_fingerprint(private_key)
    token = _make_jwt(s["account_identifier"], s["user"], private_key, fingerprint)

    account_url = s["account_url"].rstrip("/")
    sf_resp = requests.post(
        f"{account_url}/api/v2/cortex/analyst/message",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question}]}
            ],
            "semantic_model_file": CORTEX_SOURCE,
        },
        timeout=60,
    )

    if not sf_resp.ok:
        return _resp(sf_resp.status_code, {"error": sf_resp.text})

    contents = sf_resp.json().get("message", {}).get("content", [])
    result: dict = {}
    for item in contents:
        if item.get("type") == "text":
            result["interpretation"] = item["text"]
        elif item.get("type") == "sql":
            result["sql"] = item["statement"]

    return _resp(200, result)


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
