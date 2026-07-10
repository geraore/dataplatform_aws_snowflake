"""Router Lambda.

Receives the API Gateway proxy event and publishes the request body to the
EventBridge event bus. A rule on the bus forwards matching events to Firehose,
which delivers them to Snowflake (+ S3 backup). The payload is placed in the
event `detail` so downstream targets can consume the original JSON directly.
"""

import json
import os

import boto3

EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]
EVENT_SOURCE = os.environ["EVENT_SOURCE"]
_events = boto3.client("events")


def handler(event, context):
    raw_body = event.get("body") or "{}"
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            payload = {"value": payload}
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON body"})}

    result = _events.put_events(
        Entries=[
            {
                "EventBusName": EVENT_BUS_NAME,
                "Source": EVENT_SOURCE,
                "DetailType": "event",
                "Detail": json.dumps(payload),
            }
        ]
    )

    if result.get("FailedEntryCount"):
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "failed to publish event"}),
        }

    return {
        "statusCode": 202,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "accepted"}),
    }
