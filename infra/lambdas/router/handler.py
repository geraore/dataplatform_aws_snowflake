import json
import os

from pydantic import ValidationError

import eventbridge
from models import CloudEvent

EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]
EVENT_SOURCE = os.environ["EVENT_SOURCE"]

_CE_CONTENT_TYPE = "application/cloudevents+json"


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
            {"error": f"Content-Type must be '{_CE_CONTENT_TYPE}' for CloudEvents structured mode"},
        )

    raw_body = event.get("body") or "{}"
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            return _resp(400, {"error": "request body must be a JSON object"})
    except json.JSONDecodeError:
        return _resp(400, {"error": "invalid JSON body"})

    try:
        ce = CloudEvent.model_validate(payload)
    except ValidationError as exc:
        errors = [
            {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return _resp(400, {"error": "invalid CloudEvent", "details": errors})

    if not eventbridge.publish(EVENT_BUS_NAME, EVENT_SOURCE, ce.type, json.dumps(payload)):
        return _resp(502, {"error": "failed to publish event"})

    return _resp(202, {"status": "accepted"})
