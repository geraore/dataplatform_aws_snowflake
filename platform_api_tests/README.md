# Platform API Tests

Smoke tests for the two data platform APIs: the **Events ingestion API** and the **Cortex Analyst API**.

## APIs under test

| API | URL | Auth |
|-----|-----|------|
| Events (ingest) | `https://c0ossmw0xc.execute-api.us-east-2.amazonaws.com/prod/events` | `Authorization: Bearer demo-allow-token` |
| Analyst (Cortex) | `https://fm7ytstqt0.execute-api.us-east-2.amazonaws.com/prod/ask` | `Authorization: Bearer demo-allow-token` |

## CloudEvents 1.0 — Events API

The Events API enforces the [CloudEvents 1.0.2 specification](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md) in **structured mode**.

### Required request headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/cloudevents+json` |
| `Authorization` | `Bearer <token>` |

### Required CloudEvents attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `specversion` | String | Must be `"1.0"` |
| `id` | String | Unique non-empty identifier per `source` |
| `source` | URI-reference | Origin of the event (e.g. `//dataplatform/order-service`) |
| `type` | String | Reverse-DNS event type (e.g. `com.dataplatform.commerce.order_placed`) |

### Optional attributes (forwarded as-is)

`time`, `subject`, `datacontenttype`, `dataschema`, `data`, plus any extension attributes.

### Example payload

```json
{
  "specversion": "1.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "//dataplatform/order-service",
  "type": "com.dataplatform.commerce.order_placed",
  "time": "2026-07-13T12:00:00+00:00",
  "datacontenttype": "application/json",
  "data": {
    "order_id": "ord-9981",
    "customer_id": "u-002",
    "total_usd": 59.99
  }
}
```

The `make_event()` helper in `config.py` builds valid events and auto-generates `id` and `time`.

### Error responses from the router Lambda

| Status | Cause |
|--------|-------|
| `400` | Malformed JSON, missing required CloudEvents attribute, or wrong `specversion` |
| `401` | Missing `Authorization` header |
| `403` | Invalid bearer token |
| `415` | `Content-Type` is not `application/cloudevents+json` |
| `502` | EventBridge publish failure |

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

# verbose — shows SQL, interpretation, event IDs, and latency
uv run python test_events_api.py -v
uv run python test_analyst_api.py -v
```

## Token override

If a custom token was deployed via CDK context (`demo_token`):

```bash
DEMO_TOKEN=my-custom-token uv run python test_events_api.py
```
