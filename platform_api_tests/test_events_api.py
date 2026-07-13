"""Tests for the Events ingestion API (POST /events).

Usage:
    python tests/test_events_api.py
    python tests/test_events_api.py -v        # verbose output
"""

import argparse
import json
import sys
import time

import requests

from config import AUTH_HEADERS, EVENTS_API_URL

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def _post(payload: dict | None, headers: dict | None = None) -> requests.Response:
    h = AUTH_HEADERS if headers is None else headers
    body = json.dumps(payload) if payload is not None else payload
    return requests.post(EVENTS_API_URL, data=body, headers=h, timeout=15)


results: list[tuple[str, bool, str]] = []


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


def test_healthy_event(verbose: bool):
    @run("POST valid event returns 202", verbose)
    def _():
        r = _post({"event_type": "page_view", "user_id": "u-001", "url": "/home"})
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("status") == "accepted", f"unexpected body: {body}"


def test_minimal_payload(verbose: bool):
    @run("POST minimal payload (empty object) returns 202", verbose)
    def _():
        r = _post({})
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"


def test_nested_payload(verbose: bool):
    @run("POST deeply nested payload returns 202", verbose)
    def _():
        payload = {
            "event_type": "purchase",
            "user": {"id": "u-002", "tier": "gold"},
            "items": [{"sku": "SKU-1", "qty": 2}, {"sku": "SKU-2", "qty": 1}],
            "total": 59.99,
        }
        r = _post(payload)
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"


def test_invalid_json(verbose: bool):
    @run("POST malformed JSON returns 400", verbose)
    def _():
        r = requests.post(
            EVENTS_API_URL,
            data="not-json{{{{",
            headers=AUTH_HEADERS,
            timeout=15,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_missing_auth(verbose: bool):
    @run("POST without Authorization header returns 401", verbose)
    def _():
        r = requests.post(
            EVENTS_API_URL,
            json={"event_type": "test"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


def test_wrong_token(verbose: bool):
    @run("POST with wrong token returns 403", verbose)
    def _():
        bad_headers = {**AUTH_HEADERS, "Authorization": "Bearer wrong-token"}
        r = _post({"event_type": "test"}, headers=bad_headers)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


def test_response_time(verbose: bool):
    @run("POST responds within 5 seconds", verbose)
    def _():
        start = time.monotonic()
        r = _post({"event_type": "latency_check"})
        elapsed = time.monotonic() - start
        assert r.status_code == 202, f"unexpected status {r.status_code}"
        assert elapsed < 5.0, f"response took {elapsed:.2f}s (threshold: 5s)"
        if verbose:
            print(f"         elapsed: {elapsed:.3f}s")


def main():
    parser = argparse.ArgumentParser(description="Events API smoke tests")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    print(f"\nEvents API  →  {EVENTS_API_URL}\n")

    for fn in [
        test_healthy_event,
        test_minimal_payload,
        test_nested_payload,
        test_invalid_json,
        test_missing_auth,
        test_wrong_token,
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
