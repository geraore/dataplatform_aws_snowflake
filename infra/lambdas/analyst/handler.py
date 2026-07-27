import json
import os

import cortex
import snowflake_auth
import snowflake_execute
import snowflake_secrets

CORTEX_SOURCE = os.environ["CORTEX_SOURCE"]  # e.g. "GOLD.MARTS.SEM_JAFFLE"

# Cached across warm invocations — loaded once per Lambda container lifetime.
_s = None
_private_key = None
_conn = None


def _get_conn():
    global _s, _private_key, _conn
    if _s is None:
        _s = snowflake_secrets.get()
        _private_key = snowflake_auth.load_private_key(
            _s["private_key"], _s.get("key_passphrase") or None
        )
    if _conn is None or _conn.is_closed():
        _conn = snowflake_execute.connect(_s["account_identifier"], _s["user"], _private_key)
    return _s, _private_key, _conn


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

    user_id_raw = body.get("user_id")
    if user_id_raw is None:
        return _resp(400, {"error": "'user_id' field is required"})
    try:
        user_id = int(user_id_raw)
        if user_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return _resp(400, {"error": "'user_id' must be a positive integer"})

    s, private_key, conn = _get_conn()

    fingerprint = snowflake_auth.public_key_fingerprint(private_key)
    token = snowflake_auth.make_jwt(s["account_identifier"], s["user"], private_key, fingerprint)

    try:
        result = cortex.ask(s["account_url"], token, CORTEX_SOURCE, question)
    except cortex.CortexError as e:
        return _resp(e.status_code, {"error": e.body})

    sql = result.get("sql")
    if not sql:
        return _resp(200, result)

    try:
        result["results"] = snowflake_execute.execute_as_user(conn, user_id, sql)
    except Exception as e:
        return _resp(500, {"error": str(e)})

    return _resp(200, result)
