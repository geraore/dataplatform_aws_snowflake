"""Smoke test for the ecommerce_clicks streaming pipeline.

Sends a burst of click events to the ingestion API and verifies each is
accepted (HTTP 202).  This validates the path from API → Lambda authorizer →
Router Lambda → EventBridge → Firehose Snowflake delivery stream.

After a successful run, verify Snowflake delivery by running these queries
(allow ~1-2 minutes for Firehose buffering and the dynamic table refresh):

    -- Landing table (raw streaming events)
    SELECT COUNT(*), MAX(ingested_at)
    FROM BRONZE.RAW.EVENTS
    WHERE record_content:type::VARCHAR = 'ecommerce_clicks';

    -- Staging dynamic table (refreshes every minute automatically)
    SELECT COUNT(*), MAX(ce_time)
    FROM SILVER.STAGING.ECOMMERCE_CLICKS;

Usage:
    cd platform_api_tests
    uv run python test_streaming_pipeline.py
    uv run python test_streaming_pipeline.py -n 50 -v
"""

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

from config import CE_HEADERS, EVENTS_API_URL

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def _post(payload: dict) -> requests.Response:
    return requests.post(
        EVENTS_API_URL,
        data=json.dumps(payload),
        headers=CE_HEADERS,
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


def _click_event() -> dict:
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "//dataplatform/web-tracker",
        "type": "ecommerce_clicks",
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": {
            "click_id": str(uuid.uuid4()),
            "session_id": random.randint(1, 200),
            "customer_id": random.randint(1, 1000),
            "product_id": random.randint(1, 50),
            "page_type": random.choice(["home", "product", "cart", "checkout", "search", "category"]),
            "action": random.choice(["view", "click", "add_to_cart", "remove_from_cart", "checkout", "purchase"]),
            "device_type": random.choice(["mobile", "desktop", "tablet"]),
            "referrer": random.choice(["organic", "direct", "paid_search", "email", "social", "affiliate"]),
        },
    }


def test_single_click_accepted(verbose: bool):
    @run("Single ecommerce_clicks event → 202", verbose)
    def _():
        evt = _click_event()
        r = _post(evt)
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"
        assert r.json().get("status") == "accepted", f"unexpected body: {r.text}"
        if verbose:
            print(f"         event id: {evt['id']}")


def test_burst(n: int, verbose: bool):
    @run(f"Burst of {n} click events — all accepted (202)", verbose)
    def _():
        failed = []
        start = time.monotonic()
        for _ in range(n):
            r = _post(_click_event())
            if r.status_code != 202:
                failed.append(r.status_code)
        elapsed = time.monotonic() - start
        if verbose:
            print(f"         sent {n} events in {elapsed:.2f}s ({n / elapsed:.1f} evt/s)")
        assert not failed, f"{len(failed)}/{n} events rejected: {set(failed)}"


def test_routing_only_clicks(verbose: bool):
    """Sanity check: a non-click event type is still accepted (it goes to S3 only)."""
    @run("Non-click event type also accepted → 202", verbose)
    def _():
        evt = {
            "specversion": "1.0",
            "id": str(uuid.uuid4()),
            "source": "//dataplatform/tests",
            "type": "com.dataplatform.test.routing_check",
            "time": datetime.now(timezone.utc).isoformat(),
        }
        r = _post(evt)
        assert r.status_code == 202, f"expected 202, got {r.status_code}: {r.text}"


def main():
    parser = argparse.ArgumentParser(
        description="Streaming pipeline smoke test — ecommerce_clicks",
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=20,
        metavar="INT",
        help="Number of events in the burst test (default: 20)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    print(f"\nStreaming pipeline  →  {EVENTS_API_URL}")
    print("Event type: ecommerce_clicks\n")

    test_single_click_accepted(args.verbose)
    test_burst(args.count, args.verbose)
    test_routing_only_clicks(args.verbose)

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print(
            "\nSnowflake verification (run 1-2 min after this test completes):\n\n"
            "  -- Firehose landing (raw)\n"
            "  SELECT COUNT(*), MAX(ingested_at)\n"
            "  FROM BRONZE.RAW.EVENTS\n"
            "  WHERE record_content:type::VARCHAR = 'ecommerce_clicks';\n\n"
            "  -- Staging dynamic table (auto-refreshes every minute)\n"
            "  SELECT COUNT(*), MAX(ce_time)\n"
            "  FROM SILVER.STAGING.ECOMMERCE_CLICKS;"
        )
    elif not args.verbose:
        print("Re-run with -v to see failure details.")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
