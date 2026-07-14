import json
import os

import cortex
import sf_secrets
import snowflake_auth

CORTEX_SOURCE = os.environ["CORTEX_SOURCE"]  # e.g. "GOLD.MARTS.SEM_JAFFLE"


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, _context):
    body_raw = event.get("body") or "{}"
    try:
        body = json.loads(body_raw)
    except json.JSONDecodeError:
        return _resp(400, {"error": "request body must be JSON"})

    question = (body.get("question") or "").strip()
    if not question:
        return _resp(400, {"error": "'question' field is required"})

    s = sf_secrets.get()
    private_key = snowflake_auth.load_private_key(s["private_key"], s.get("key_passphrase") or None)
    fingerprint = snowflake_auth.public_key_fingerprint(private_key)
    token = snowflake_auth.make_jwt(s["account_identifier"], s["user"], private_key, fingerprint)

    try:
        result = cortex.ask(s["account_url"], token, CORTEX_SOURCE, question)
    except cortex.CortexError as e:
        return _resp(e.status_code, {"error": e.body})

    return _resp(200, result)
