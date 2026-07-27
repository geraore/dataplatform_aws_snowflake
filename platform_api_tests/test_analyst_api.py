"""Tests for the Cortex Analyst API (POST /ask).

The Lambda proxies the question to Snowflake Cortex Analyst and returns:
    { "interpretation": "<plain-English>", "sql": "<SQL statement>", "results": [...] }

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


_W = 60  # section header width


def _section(label: str) -> str:
    dashes = "─" * max(0, _W - len(label) - 1)
    return f"\n    \033[2m── {label} {dashes}\033[0m"


def _table(rows: list[dict]) -> str:
    if not rows:
        return "    (no rows)"
    headers = list(rows[0].keys())
    widths = {h: max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in headers}

    def fmt(vals: list) -> str:
        return "    " + "  ".join(str(v).ljust(widths[h]) for h, v in zip(headers, vals))

    sep = "    " + "  ".join("─" * widths[h] for h in headers)
    lines = [fmt(headers), sep, *[fmt([r.get(h, "") for h in headers]) for r in rows]]
    return "\n".join(lines)


def _print_cortex_response(body: dict) -> None:
    print(_section("Interpretation"))
    print(f"    {body.get('interpretation', '(none)')}")

    sql = body.get("sql")
    if sql:
        print(_section("SQL"))
        for line in sql.splitlines():
            print(f"    {line}")

    rows = body.get("results")
    if rows is not None:
        count = len(rows)
        print(_section(f"Results  {count} row{'s' if count != 1 else ''}"))
        print(_table(rows))
    print()


def test_basic_question(verbose: bool):
    @run("POST valid question returns 200 with interpretation + sql + results", verbose)
    def _():
        r = _post({"question": "How many orders were placed in total?", "user_id": 1})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "interpretation" in body, f"missing 'interpretation' key: {body}"
        assert "sql" in body, f"missing 'sql' key: {body}"
        assert body["interpretation"], "interpretation is empty"
        assert body["sql"], "sql is empty"
        _print_cortex_response(body)
        assert "results" in body, f"missing 'results' key: {body}"
        assert isinstance(body["results"], list), f"'results' is not a list: {body['results']}"


def test_revenue_question(verbose: bool):
    @run("POST revenue question returns valid SQL", verbose)
    def _():
        r = _post({"question": "What is the total revenue by product category?", "user_id": 1})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        sql = body.get("sql", "")
        assert "SELECT" in sql.upper(), f"response SQL does not contain SELECT: {sql}"
        _print_cortex_response(body)


def test_top_customers_question(verbose: bool):
    @run("POST top-customers question returns valid SQL", verbose)
    def _():
        r = _post({"question": "Who are the top 5 customers by number of orders?", "user_id": 1})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "sql" in body, f"missing 'sql' key: {body}"
        _print_cortex_response(body)


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


def test_null_question(verbose: bool):
    @run("POST with null question returns 400", verbose)
    def _():
        r = _post({"question": None})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_empty_body(verbose: bool):
    @run("POST with empty body {} returns 400", verbose)
    def _():
        r = _post({})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_get_method(verbose: bool):
    # API Gateway runs the token authorizer before method validation, so an
    # unauthenticated GET returns 403 (authorizer fires first) rather than 405.
    @run("GET method returns 403", verbose)
    def _():
        r = requests.get(ANALYST_API_URL, timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


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
    @run("POST responds within 90 seconds (Cortex + query execution budget)", verbose)
    def _():
        start = time.monotonic()
        r = _post({"question": "How many orders exist?", "user_id": 1})
        elapsed = time.monotonic() - start
        assert r.status_code == 200, f"unexpected status {r.status_code}"
        assert elapsed < 90.0, f"response took {elapsed:.2f}s (threshold: 90s)"
        print(f"\n         elapsed: {elapsed:.3f}s")
        _print_cortex_response(r.json())


# ---------------------------------------------------------------------------
# User-context tests
#
# Each Cortex Analyst request must include a `user_id` that maps to a row in
# GOVERNANCE.SECURITY.ENTITLEMENTS.  The Lambda validates it and echoes it
# back in the response; the SQL executor must then SET APP_USER_ID = <user_id>
# before running the returned SQL so that the masking and row-access policies
# in GOVERNANCE.SECURITY apply correctly.
#
# Users from V1.1.12__entitlements_v2.sql:
#   1 – data steward   : access_level 2 on all resources
#   2 – ops analyst    : stores, products, orders, order_items (no customer / payment)
#   3 – CRM analyst    : customer (PII visible), orders, order_items
#   4 – store manager  : store 5 only, products, orders, order_items
#   5 – finance analyst: payments (PII visible), orders
# ---------------------------------------------------------------------------

def test_user_context_user1_data_steward(verbose: bool):
    @run("user 1 (data steward): cross-resource question returns SQL + results", verbose)
    def _():
        r = _post({"question": "What is total revenue per customer?", "user_id": 1})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "sql" in body and body["sql"], f"missing or empty 'sql': {body}"
        _print_cortex_response(body)
        assert "results" in body and isinstance(body["results"], list), f"missing or invalid 'results': {body}"


def test_user_context_user2_ops_analyst(verbose: bool):
    @run("user 2 (ops analyst): order and product question returns SQL + results", verbose)
    def _():
        r = _post({"question": "What are the top 10 stores by total number of orders?", "user_id": 2})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "sql" in body and body["sql"], f"missing or empty 'sql': {body}"
        _print_cortex_response(body)
        assert "results" in body and isinstance(body["results"], list), f"missing or invalid 'results': {body}"


def test_user_context_user3_crm_analyst(verbose: bool):
    @run("user 3 (CRM analyst): customer and order question returns SQL + results", verbose)
    def _():
        r = _post({"question": "How many orders has each customer placed?", "user_id": 3})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "sql" in body and body["sql"], f"missing or empty 'sql': {body}"
        _print_cortex_response(body)
        assert "results" in body and isinstance(body["results"], list), f"missing or invalid 'results': {body}"


def test_user_context_user4_store_manager(verbose: bool):
    @run("user 4 (store manager, store 5): store-scoped question returns SQL + results", verbose)
    def _():
        r = _post({"question": "What are the total sales for store 5?", "user_id": 4})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "sql" in body and body["sql"], f"missing or empty 'sql': {body}"
        _print_cortex_response(body)
        assert "results" in body and isinstance(body["results"], list), f"missing or invalid 'results': {body}"


def test_user_context_user5_finance_analyst(verbose: bool):
    @run("user 5 (finance analyst): payment question returns SQL + results", verbose)
    def _():
        r = _post({"question": "What is the total payment amount processed this month?", "user_id": 5})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "sql" in body and body["sql"], f"missing or empty 'sql': {body}"
        _print_cortex_response(body)
        assert "results" in body and isinstance(body["results"], list), f"missing or invalid 'results': {body}"


def test_missing_user_id(verbose: bool):
    @run("POST valid question without user_id returns 400", verbose)
    def _():
        r = _post({"question": "How many orders exist?"})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        body = r.json()
        assert "error" in body, f"expected 'error' in body: {body}"


def test_invalid_user_id_string(verbose: bool):
    @run("POST with non-integer user_id returns 400", verbose)
    def _():
        r = _post({"question": "How many orders exist?", "user_id": "ops_analyst"})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        body = r.json()
        assert "error" in body, f"expected 'error' in body: {body}"


def test_invalid_user_id_zero(verbose: bool):
    @run("POST with user_id=0 returns 400", verbose)
    def _():
        r = _post({"question": "How many orders exist?", "user_id": 0})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_invalid_user_id_negative(verbose: bool):
    @run("POST with negative user_id returns 400", verbose)
    def _():
        r = _post({"question": "How many orders exist?", "user_id": -1})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


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
        test_null_question,
        test_empty_body,
        test_get_method,
        test_basic_question,
        test_revenue_question,
        test_top_customers_question,
        test_response_time,
        test_user_context_user1_data_steward,
        test_user_context_user2_ops_analyst,
        test_user_context_user3_crm_analyst,
        test_user_context_user4_store_manager,
        test_user_context_user5_finance_analyst,
        test_missing_user_id,
        test_invalid_user_id_string,
        test_invalid_user_id_zero,
        test_invalid_user_id_negative,
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
