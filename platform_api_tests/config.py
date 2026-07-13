"""Shared configuration for API test scripts."""

EVENTS_API_URL = "https://c0ossmw0xc.execute-api.us-east-2.amazonaws.com/prod/events"
ANALYST_API_URL = "https://fm7ytstqt0.execute-api.us-east-2.amazonaws.com/prod/ask"

# Demo bearer token configured in both Lambda authorizers.
# Override via env var DEMO_TOKEN if a custom token was deployed.
import os
DEMO_TOKEN = os.environ.get("DEMO_TOKEN", "demo-allow-token")

AUTH_HEADERS = {
    "Authorization": f"Bearer {DEMO_TOKEN}",
    "Content-Type": "application/json",
}
