"""Router Lambda.

Receives the API Gateway proxy event and forwards the request body to the
Kinesis Data Stream. The partition key is taken from the payload when present
so related events stay ordered, otherwise a random key spreads load.
"""

import json
import os
import uuid

import boto3

STREAM_NAME = os.environ["STREAM_NAME"]
_kinesis = boto3.client("kinesis")


def _partition_key(payload: dict) -> str:
    for key in ("partition_key", "user_id", "id"):
        if payload.get(key):
            return str(payload[key])
    return uuid.uuid4().hex


def handler(event, context):
    raw_body = event.get("body") or "{}"
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            payload = {"value": payload}
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON body"})}

    _kinesis.put_record(
        StreamName=STREAM_NAME,
        Data=(json.dumps(payload) + "\n").encode("utf-8"),
        PartitionKey=_partition_key(payload),
    )

    return {
        "statusCode": 202,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "accepted"}),
    }
