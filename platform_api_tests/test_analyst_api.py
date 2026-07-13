"""Tests for the Cortex Analyst API (POST /ask).

The Lambda proxies the question to Snowflake Cortex Analyst and returns:
    { "interpretation": "<plain-English>", "sql": "<SQL statement>" }

Usage:
    uv run python test_analyst_api.py
    uv run python test_analyst_api.py -v    # verbose: show SQL + interpretation
"""

import argparse
import json
import sys
import time

import requests

from config import ANALYST_API_URL, ANALYST_HEADERS as AUTH_HEADERS

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def _post(payload: dict | None = None, headers: dict | None = None) -> requests.Response:
    h = AUTH_HEADERS if headers is None else headers
    return requests.post(ANALYST_API_URL, json=payload, headers=h, timeout=90)


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


def test_basic_question(verbose: bool):
    @run("POST valid question returns 200 with interpretation + sql", verbose)
    def _():
        r = _post({"question": "How many orders were placed in total?"})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "interpretation" in body, f"missing 'interpretation' key: {body}"
        assert "sql" in body, f"missing 'sql' key: {body}"
        assert body["interpretation"], "interpretation is empty"
        assert body["sql"], "sql is empty"
        if verbose:
            print(f"\n         interpretation: {body['interpretation'][:120]}...")
            print(f"         sql: {body['sql'][:200]}...")


def test_revenue_question(verbose: bool):
    @run("POST revenue question returns valid SQL", verbose)
    def _():
        r = _post({"question": "What is the total revenue by customer segment?"})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        sql = body.get("sql", "")
        assert "SELECT" in sql.upper(), f"response SQL does not contain SELECT: {sql}"
        if verbose:
            print(f"\n         sql: {sql[:300]}")


def test_top_customers_question(verbose: bool):
    @run("POST top-customers question returns valid SQL", verbose)
    def _():
        r = _post({"question": "Who are the top 5 customers by number of orders?"})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "sql" in body, f"missing 'sql' key: {body}"
        if verbose:
            print(f"\n         sql: {body['sql'][:300]}")


def test_missing_question_field(verbose: bool):
    @run("POST without 'question' field returns 400", verbose)
    def _():
        r = _post({"query": "this uses the wrong key"})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        body = r.json()
        assert "error" in body, f"expected 'error' in body: {body}"


def test_empty_question(verbose: bool):
    @run("POST with empty question string returns 400", verbose)
    def _():
        r = _post({"question": "   "})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_invalid_json(verbose: bool):
    @run("POST malformed JSON returns 400", verbose)
    def _():
        r = requests.post(
            ANALYST_API_URL,
            data="not-json{{{{",
            headers=AUTH_HEADERS,
            timeout=15,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_missing_auth(verbose: bool):
    @run("POST without Authorization header returns 401", verbose)
    def _():
        r = requests.post(
            ANALYST_API_URL,
            json={"question": "test"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


def test_wrong_token(verbose: bool):
    @run("POST with wrong token returns 403", verbose)
    def _():
        bad_headers = {**AUTH_HEADERS, "Authorization": "Bearer wrong-token"}
        r = _post({"question": "test"}, headers=bad_headers)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


def test_response_time(verbose: bool):
    @run("POST responds within 60 seconds (Snowflake cold-start budget)", verbose)
    def _():
        start = time.monotonic()
        r = _post({"question": "How many orders exist?"})
        elapsed = time.monotonic() - start
        assert r.status_code == 200, f"unexpected status {r.status_code}"
        assert elapsed < 60.0, f"response took {elapsed:.2f}s (threshold: 60s)"
        if verbose:
            print(f"         elapsed: {elapsed:.3f}s")


def main():
    parser = argparse.ArgumentParser(description="Analyst API smoke tests")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    print(f"\nAnalyst API  →  {ANALYST_API_URL}\n")
    print("  Note: tests that call Snowflake Cortex may take 10-30s each.\n")

    for fn in [
        test_missing_auth,
        test_wrong_token,
        test_missing_question_field,
        test_empty_question,
        test_invalid_json,
        test_basic_question,
        test_revenue_question,
        test_top_customers_question,
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
