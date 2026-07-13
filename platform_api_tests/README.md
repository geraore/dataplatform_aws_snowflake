# Platform API Tests

Smoke tests for the two data platform APIs: the **Events ingestion API** and the **Cortex Analyst API**.

## APIs under test

| API | URL | Auth |
|-----|-----|------|
| Events (ingest) | `https://c0ossmw0xc.execute-api.us-east-2.amazonaws.com/prod/events` | `Authorization: Bearer demo-allow-token` |
| Analyst (Cortex) | `https://fm7ytstqt0.execute-api.us-east-2.amazonaws.com/prod/ask` | `Authorization: Bearer demo-allow-token` |

## Setup

The environment is managed by [uv](https://docs.astral.sh/uv/). From inside `platform_api_tests/`:

```bash
uv sync
```

## Run

```bash
# from inside platform_api_tests/
uv run python test_events_api.py
uv run python test_analyst_api.py

# verbose — shows SQL, interpretation, and latency
uv run python test_events_api.py -v
uv run python test_analyst_api.py -v
```

## Token override

If a custom token was deployed via CDK context (`demo_token`):

```bash
DEMO_TOKEN=my-custom-token uv run python test_events_api.py
```
