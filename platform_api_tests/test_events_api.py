"""Tests for the Events ingestion API (POST /events).

The API enforces CloudEvents 1.0 structured mode:
  https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md

Required CloudEvents attributes validated by the router Lambda:
  - specversion  "1.0"
  - id           non-empty string (unique per source)
  - source       non-empty URI-reference
  - type         non-empty string (reverse-DNS prefix recommended)

Content-Type must be: application/cloudevents+json

Usage:
    uv run python test_events_api.py
    uv run python test_events_api.py -v    # verbose output
"""

import argparse
import json
import sys
import time

import requests

from config import CE_HEADERS, EVENTS_API_URL, make_event

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def _post(payload: dict, headers: dict | None = None) -> requests.Response:
    return requests.post(
        EVENTS_API_URL,
        data=json.dumps(payload),
        headers=CE_HEADERS if headers is None else headers,
        timeout=15,
    )


def _raw_post(body: str, headers: dict | None = None) -> requests.Response:
    return requests.post(
        EVENTS_API_URL,
        data=body,
        headers=CE_HEADERS if headers is None else headers,
        timeout=15,
    )


def run(name: str, verbose: bool):
    def decorator(fn):
        try:
            fn()
            results.append((name, True, ""))
            print(f"  {PASS}  {name}")
        except AssertionError as e:
            results.append((name, False, str(e)))
            print(f"  {FAIL}  {name}")
            if verbose:
                print(f"         {e}")
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Auth tests (authorizer runs before Lambda — content-type does not matter)
# ---------------------------------------------------------------------------

def test_missing_auth(verbose: bool):
    @run("No Authorization header → 401", verbose)
    def _():
        h = {k: v for k, v in CE_HEADERS.items() if k != "Authorization"}
        r = _post(make_event("com.example.test"), headers=h)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


def test_wrong_token(verbose: bool):
    @run("Wrong bearer token → 403", verbose)
    def _():
        h = {**CE_HEADERS, "Authorization": "Bearer wrong-token"}
        r = _post(make_event("com.example.test"), headers=h)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# Content-Type enforcement (CloudEvents structured mode)
# ---------------------------------------------------------------------------

def test_wrong_content_type(verbose: bool):
    @run("Content-Type: application/json (not CloudEvents) → 415", verbose)
    def _():
        h = {**CE_HEADERS, "Content-Type": "application/json"}
        r = _post(make_event("com.example.test"), headers=h)
        assert r.status_code == 415, f"expected 415, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# CloudEvents required-attribute validation
# ---------------------------------------------------------------------------

def test_missing_specversion(verbose: bool):
    @run("Missing 'specversion' → 400", verbose)
    def _():
        evt = make_event("com.example.test")
        del evt["specversion"]
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        assert "specversion" in r.text, f"error should mention 'specversion': {r.text}"


def test_wrong_specversion(verbose: bool):
    @run("specversion '0.3' (unsupported) → 400", verbose)
    def _():
        evt = {**make_event("com.example.test"), "specversion": "0.3"}
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_missing_id(verbose: bool):
    @run("Missing 'id' → 400", verbose)
    def _():
        evt = make_event("com.example.test")
        del evt["id"]
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_missing_source(verbose: bool):
    @run("Missing 'source' → 400", verbose)
    def _():
        evt = make_event("com.example.test")
        del evt["source"]
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_missing_type(verbose: bool):
    @run("Missing 'type' → 400", verbose)
    def _():
        evt = make_event("com.example.test")
        del evt["type"]
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_empty_id(verbose: bool):
    @run("Empty string 'id' → 400", verbose)
    def _():
        evt = {**make_event("com.example.test"), "id": "   "}
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_malformed_json(verbose: bool):
    @run("Malformed JSON body → 400", verbose)
    def _():
        r = _raw_post("not-json{{{{")
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_empty_source(verbose: bool):
    @run("Whitespace-only 'source' → 400", verbose)
    def _():
        evt = {**make_event("com.example.test"), "source": "   "}
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_empty_type(verbose: bool):
    @run("Whitespace-only 'type' → 400", verbose)
    def _():
        evt = {**make_event("com.example.test"), "type": "   "}
        r = _post(evt)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_null_required_fields(verbose: bool):
    @run("Null value in required field → 400", verbose)
    def _():
        for field in ("specversion", "id", "source", "type"):
            evt = {**make_event("com.example.test"), field: None}
            r = _post(evt)
            assert r.status_code == 400, (
                f"expected 400 for null '{field}', got {r.status_code}: {r.text}"
            )


def test_get_method(verbose: bool):
    @run("GET method → 405", verbose)
    def _():
        r = requests.get(EVENTS_API_URL, headers=CE_HEADERS, timeout=15)
        assert r.status_code == 405, f"expected 405, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# Happy-path: valid CloudEvents
# ---------------------------------------------------------------------------

def test_minimal_event(verbose: bool):
    @run("Minimal CloudEvent (required attrs only) → 202", verbose)
    def _():
        evt = {
            "specversion": "1.0",
            "id": "test-minimal-001",
            "source": "//dataplatform/tests",
            "type": "com.dataplatform.test.minimal",
        }
        r = _post(evt)
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"
        assert r.json().get("status") == "accepted", f"unexpected body: {r.text}"


def test_page_view_event(verbose: bool):
    @run("CloudEvent: page_view with data → 202", verbose)
    def _():
        evt = make_event(
            "com.dataplatform.web.page_view",
            source="//dataplatform/web-tracker",
            data={"user_id": "u-001", "url": "/home", "session_id": "s-abc123"},
        )
        r = _post(evt)
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"
        if verbose:
            print(f"\n         event id: {evt['id']}")


def test_purchase_event(verbose: bool):
    @run("CloudEvent: purchase with nested data → 202", verbose)
    def _():
        evt = make_event(
            "com.dataplatform.commerce.order_placed",
            source="//dataplatform/order-service",
            data={
                "order_id": "ord-9981",
                "customer": {"id": "u-002", "tier": "gold"},
                "items": [{"sku": "SKU-1", "qty": 2}, {"sku": "SKU-2", "qty": 1}],
                "total_usd": 59.99,
            },
        )
        r = _post(evt)
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"


def test_event_with_subject(verbose: bool):
    @run("CloudEvent with optional 'subject' attribute → 202", verbose)
    def _():
        evt = make_event(
            "com.dataplatform.user.signup",
            source="//dataplatform/auth-service",
            data={"plan": "pro"},
            subject="user/u-003",
        )
        r = _post(evt)
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------

def test_response_time(verbose: bool):
    @run("Responds within 5 seconds", verbose)
    def _():
        evt = make_event("com.dataplatform.test.latency")
        start = time.monotonic()
        r = _post(evt)
        elapsed = time.monotonic() - start
        assert r.status_code == 202, f"unexpected status {r.status_code}"
        assert elapsed < 5.0, f"response took {elapsed:.2f}s (threshold: 5s)"
        if verbose:
            print(f"         elapsed: {elapsed:.3f}s")


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Events API smoke tests (CloudEvents 1.0)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    print(f"\nEvents API  →  {EVENTS_API_URL}")
    print(f"CloudEvents spec: https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md\n")

    for fn in [
        # Auth
        test_missing_auth,
        test_wrong_token,
        # Content-Type
        test_wrong_content_type,
        # Required-attribute validation
        test_missing_specversion,
        test_wrong_specversion,
        test_missing_id,
        test_missing_source,
        test_missing_type,
        test_empty_id,
        test_malformed_json,
        test_empty_source,
        test_empty_type,
        test_null_required_fields,
        test_get_method,
        # Happy path
        test_minimal_event,
        test_page_view_event,
        test_purchase_event,
        test_event_with_subject,
        # Latency
        test_response_time,
    ]:
        fn(args.verbose)

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")

    if passed < total and not args.verbose:
        print("Re-run with -v to see failure details.")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
