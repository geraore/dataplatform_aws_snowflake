import datetime
import decimal

import snowflake.connector
from cryptography.hazmat.primitives import serialization

MAX_ROWS = 500


def connect(account: str, user: str, private_key) -> snowflake.connector.SnowflakeConnection:
    der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return snowflake.connector.connect(account=account, user=user, private_key=der)


def execute_as_user(
    conn: snowflake.connector.SnowflakeConnection, user_id: int, sql: str
) -> list[dict]:
    """SET APP_USER_ID for this request and execute sql on an existing connection."""
    with conn.cursor(snowflake.connector.DictCursor) as cur:
        cur.execute(f"SET APP_USER_ID = {user_id}")
        cur.execute(sql)
        rows = cur.fetchmany(MAX_ROWS)
    return [_coerce(row) for row in rows]


def _coerce(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, decimal.Decimal):
            out[k] = float(v)
        elif isinstance(v, (datetime.date, datetime.datetime)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
