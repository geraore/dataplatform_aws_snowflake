"""Shared configuration for API test scripts."""

import os
import uuid
from datetime import UTC, datetime

EVENTS_API_URL = os.environ["EVENTS_API_URL"]
ANALYST_API_URL = os.environ["ANALYST_API_URL"]

# Demo bearer token configured in both Lambda authorizers.
# Override via env var DEMO_TOKEN if a custom token was deployed.
DEMO_TOKEN = os.environ.get("DEMO_TOKEN", "demo-allow-token")

# Events API uses CloudEvents 1.0 structured mode — content-type is required by spec.
CE_HEADERS = {
    "Authorization": f"Bearer {DEMO_TOKEN}",
    "Content-Type": "application/cloudevents+json",
}

# Analyst API uses plain JSON.
ANALYST_HEADERS = {
    "Authorization": f"Bearer {DEMO_TOKEN}",
    "Content-Type": "application/json",
}


def make_event(
    event_type: str,
    source: str = "//dataplatform/tests",
    data: dict | None = None,
    **extra,
) -> dict:
    """Build a minimal valid CloudEvents 1.0 structured-mode event.

    Spec: https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md

    Required attributes (always present):
      specversion, id, source, type

    Optional attributes added by default:
      time, datacontenttype (when data is provided)
    """
    event: dict = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "time": datetime.now(UTC).isoformat(),
    }
    if data is not None:
        event["datacontenttype"] = "application/json"
        event["data"] = data
    event.update(extra)
    return event
