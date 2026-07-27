"""Interactive CLI chat for the Snowflake Cortex Analyst API.

Usage:
    uv run python analyst_chat.py
"""

import sys

import requests

from config import ANALYST_API_URL, ANALYST_HEADERS

# ── ANSI helpers ──────────────────────────────────────────────────────────────

BOLD  = "\033[1m"
DIM   = "\033[2m"
CYAN  = "\033[36m"
GREEN = "\033[32m"
RED   = "\033[31m"
RESET = "\033[0m"

_W = 60  # section header width


def _section(label: str) -> str:
    dashes = "─" * max(0, _W - len(label) - 1)
    return f"\n  {DIM}── {label} {dashes}{RESET}"


def _table(rows: list[dict]) -> str:
    if not rows:
        return f"  {DIM}(no rows){RESET}"
    headers = list(rows[0].keys())
    widths = {h: max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in headers}

    def fmt(vals: list) -> str:
        return "  " + "  ".join(str(v).ljust(widths[h]) for h, v in zip(headers, vals))

    sep = "  " + "  ".join("─" * widths[h] for h in headers)
    lines = [fmt(headers), sep, *[fmt([r.get(h, "") for h in headers]) for r in rows]]
    return "\n".join(lines)


def _print_response(body: dict, show_sql: bool) -> None:
    print(_section("Interpretation"))
    print(f"  {body.get('interpretation', '(none)')}")

    if show_sql:
        sql = body.get("sql")
        if sql:
            print(_section("SQL"))
            for line in sql.splitlines():
                print(f"  {line}")

    rows = body.get("results")
    if rows is not None:
        count = len(rows)
        print(_section(f"Results  {count} row{'s' if count != 1 else ''}"))
        print(_table(rows))
    print()


# ── API call ──────────────────────────────────────────────────────────────────

def _ask(question: str, user_id: int) -> dict:
    resp = requests.post(
        ANALYST_API_URL,
        json={"question": question, "user_id": user_id},
        headers=ANALYST_HEADERS,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


# ── Prompts ───────────────────────────────────────────────────────────────────

def _prompt_user_id() -> int:
    while True:
        raw = input(f"  {BOLD}User ID:{RESET} ").strip()
        try:
            uid = int(raw)
            if uid > 0:
                return uid
        except ValueError:
            pass
        print(f"  {RED}Enter a positive integer.{RESET}")


def _prompt_show_sql() -> bool:
    raw = input(f"  {BOLD}Show generated SQL?{RESET} [y/N] ").strip().lower()
    return raw in ("y", "yes")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n  {BOLD}{CYAN}Snowflake Cortex Analyst{RESET}")
    print(f"  {DIM}{ANALYST_API_URL}{RESET}\n")

    user_id  = _prompt_user_id()
    show_sql = _prompt_show_sql()

    print(f"\n  {DIM}Type a question, or 'exit' to quit.{RESET}\n")

    while True:
        try:
            question = input(f"{CYAN}[user {user_id}]{RESET} {BOLD}>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {DIM}Goodbye.{RESET}\n")
            sys.exit(0)

        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            print(f"\n  {DIM}Goodbye.{RESET}\n")
            sys.exit(0)

        try:
            body = _ask(question, user_id)
        except requests.HTTPError as e:
            print(f"\n  {RED}API error {e.response.status_code}:{RESET} {e.response.text}\n")
            continue
        except requests.RequestException as e:
            print(f"\n  {RED}Request failed:{RESET} {e}\n")
            continue

        _print_response(body, show_sql)


if __name__ == "__main__":
    main()
