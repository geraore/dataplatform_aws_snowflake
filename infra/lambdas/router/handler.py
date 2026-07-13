"""Router Lambda.

Receives the API Gateway proxy event, validates it as a CloudEvents 1.0
structured-mode event (https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md),
and publishes the full envelope to the EventBridge event bus. A rule on the bus
forwards matching events to Firehose (DirectPut), which delivers them to
Snowflake (+ S3 backup). The payload is placed in the event `detail` so
downstream targets can consume the original CloudEvent directly.

CloudEvents structured mode requirements enforced here:
  - Content-Type: application/cloudevents+json  (MUST per spec §3)
  - specversion: "1.0"                          (REQUIRED)
  - id:          non-empty string               (REQUIRED)
  - source:      non-empty URI-reference        (REQUIRED)
  - type:        non-empty string               (REQUIRED)

Optional attributes (datacontenttype, dataschema, subject, time, data, etc.)
are forwarded as-is without modification.
"""

import json
import os

import boto3

EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]
EVENT_SOURCE = os.environ["EVENT_SOURCE"]
_events = boto3.client("events")

_CE_CONTENT_TYPE = "application/cloudevents+json"
_REQUIRED_CE_ATTRS = {"specversion", "id", "source", "type"}


def _validate_cloudevent(payload: dict) -> str | None:
    """Return an error message if payload is not a valid CloudEvents 1.0 event."""
    missing = _REQUIRED_CE_ATTRS - payload.keys()
    if missing:
        return f"missing required CloudEvents attributes: {sorted(missing)}"
    if payload["specversion"] != "1.0":
        return f"unsupported specversion: {payload['specversion']!r} — expected '1.0'"
    for attr in ("id", "source", "type"):
        if not isinstance(payload[attr], str) or not payload[attr].strip():
            return f"'{attr}' must be a non-empty string"
    return None


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    content_type = (event.get("headers") or {}).get("Content-Type", "")
    if not content_type.startswith(_CE_CONTENT_TYPE):
        return _resp(
            415,
            {
                "error": f"Content-Type must be '{_CE_CONTENT_TYPE}' for CloudEvents structured mode"
            },
        )

    raw_body = event.get("body") or "{}"
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            return _resp(400, {"error": "request body must be a JSON object"})
    except json.JSONDecodeError:
        return _resp(400, {"error": "invalid JSON body"})

    error = _validate_cloudevent(payload)
    if error:
        return _resp(400, {"error": error})

    result = _events.put_events(
        Entries=[
            {
                "EventBusName": EVENT_BUS_NAME,
                "Source": EVENT_SOURCE,
                # Use the CloudEvents type as the DetailType for EventBridge rule matching.
                "DetailType": payload["type"],
                "Detail": json.dumps(payload),
            }
        ]
    )

    if result.get("FailedEntryCount"):
        return _resp(502, {"error": "failed to publish event"})

    return _resp(202, {"status": "accepted"})
