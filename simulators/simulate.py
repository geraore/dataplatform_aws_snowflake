#!/usr/bin/env python3
"""
General event simulator for the data platform.

Reads event templates from simulators/events/*.yml and posts
CloudEvents 1.0 structured-mode events to the ingestion API.

Usage:
    python simulate.py                           # cycle through all event types
    python simulate.py -e customer               # only customer events
    python simulate.py -e customer order         # multiple types
    python simulate.py -r 2.0                    # 2 events/second (default: 1.0)
    python simulate.py -n 50                     # stop after 50 events total
    python simulate.py --dry-run                 # print events, do not POST

Environment variables:
    EVENTS_API_URL   Override the default API endpoint
    DEMO_TOKEN       Override the default bearer token

Field generator types (defined per field in the template YAML):
    type: sequence   Auto-incrementing integer.  start: <int> (default 1).
                     IDs are added to the shared pool so other templates can
                     reference them via `type: reference`.
    type: int        Random integer.  min: <int>, max: <int>.
    type: float      Random float.   min: <float>, max: <float>, decimals: <int>.
    type: choice     Random pick.    values: [a, b, c].
    type: faker      Faker method.   method: first_name  (any Faker attribute).
    type: reference  Pick from a shared pool populated by sequence generators.
                     from: <pool_key>  min/max fallback if pool is empty.
    type: uuid       Random UUID string.
"""

import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

try:
    from faker import Faker

    _faker = Faker()
except ImportError:
    _faker = None

TEMPLATES_DIR = Path(__file__).parent / "events"

API_URL = os.environ.get(
    "EVENTS_API_URL",
    "https://c0ossmw0xc.execute-api.us-east-2.amazonaws.com/prod/events",
)
DEMO_TOKEN = os.environ.get("DEMO_TOKEN", "demo-allow-token")

_HEADERS = {
    "Authorization": f"Bearer {DEMO_TOKEN}",
    "Content-Type": "application/cloudevents+json",
}

# Shared state across all generators in a session.
_pools: dict[str, list] = {}
_sequences: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Value generators
# ---------------------------------------------------------------------------

def _generate(field: str, spec: dict):
    kind = spec.get("type", "uuid")

    if kind == "sequence":
        if field not in _sequences:
            _sequences[field] = spec.get("start", 1)
        val = _sequences[field]
        _sequences[field] += 1
        _pools.setdefault(field, []).append(val)
        return val

    if kind == "int":
        return random.randint(spec.get("min", 1), spec.get("max", 1000))

    if kind == "float":
        val = random.uniform(spec.get("min", 0.0), spec.get("max", 100.0))
        return round(val, spec.get("decimals", 2))

    if kind == "choice":
        return random.choice(spec["values"])

    if kind == "faker":
        if _faker is None:
            raise RuntimeError("faker is not installed — run: uv add faker")
        method = spec.get("method", "word")
        fn = getattr(_faker, method, None)
        if fn is None:
            raise ValueError(f"Unknown Faker method: {method!r}")
        return fn()

    if kind == "reference":
        pool_key = spec.get("from", field)
        pool = _pools.get(pool_key)
        if pool:
            return random.choice(pool)
        return random.randint(spec.get("min", 1), spec.get("max", 1000))

    if kind == "uuid":
        return str(uuid.uuid4())

    raise ValueError(f"Unknown generator type: {kind!r}")


def _generate_data(template: dict) -> dict:
    return {
        field: _generate(field, spec)
        for field, spec in template.get("data", {}).items()
    }


# ---------------------------------------------------------------------------
# CloudEvent construction and delivery
# ---------------------------------------------------------------------------

def _build_event(template: dict, data: dict) -> dict:
    event: dict = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": template.get("source", "//dataplatform/simulator"),
        "type": template["event_type"],
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": data,
    }
    return event


def _post(event: dict) -> int:
    try:
        r = requests.post(
            API_URL,
            data=json.dumps(event, default=str),
            headers=_HEADERS,
            timeout=10,
        )
        return r.status_code
    except requests.RequestException as exc:
        print(f"  [ERROR] {exc}", file=sys.stderr)
        return 0


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def _load(name: str) -> dict:
    path = TEMPLATES_DIR / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    with path.open() as f:
        return yaml.safe_load(f)


# Root entities must appear before dependents so their sequence pools are
# populated before any reference generator runs on the first cycle.
_TEMPLATE_ORDER = ["customer", "store", "product", "order", "order_item", "payment"]


def _all_template_names() -> list[str]:
    present = {p.stem for p in TEMPLATES_DIR.glob("*.yml")}
    ordered = [name for name in _TEMPLATE_ORDER if name in present]
    ordered += sorted(present - set(ordered))
    return ordered


# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------

def run(templates: list[dict], rate: float, count: int | None, dry_run: bool) -> None:
    n = len(templates)
    interval = 1.0 / rate if rate > 0 else 0
    sent = 0

    target = f"(dry-run)" if dry_run else API_URL
    print(f"Simulating {n} event type(s) at {rate} evt/s → {target}")
    print("Press Ctrl+C to stop.\n")

    try:
        while count is None or sent < count:
            template = templates[sent % n]
            data = _generate_data(template)
            event = _build_event(template, data)

            if dry_run:
                print(json.dumps(event, indent=2, default=str))
            else:
                status = _post(event)
                mark = "✓" if status == 202 else f"✗ {status}"
                short_id = event["id"][:8]
                print(f"  {mark}  {event['type']}  id={short_id}…")

            sent += 1
            if interval > 0:
                time.sleep(interval)

    except KeyboardInterrupt:
        pass

    print(f"\nSent {sent} event(s).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Data platform event simulator (CloudEvents 1.0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-e", "--event",
        nargs="+",
        metavar="NAME",
        help="Template name(s) to simulate (filename without .yml). "
             "Defaults to all templates in simulators/events/.",
    )
    parser.add_argument(
        "-r", "--rate",
        type=float,
        default=1.0,
        metavar="FLOAT",
        help="Events per second (default: 1.0). Use 0 for no throttling.",
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=None,
        metavar="INT",
        help="Total events to send then stop. Omit for continuous simulation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print events to stdout instead of posting to the API.",
    )
    args = parser.parse_args()

    names = args.event or _all_template_names()
    if not names:
        print(f"No templates found in {TEMPLATES_DIR}.", file=sys.stderr)
        sys.exit(1)

    templates = []
    for name in names:
        try:
            templates.append(_load(name))
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    run(templates, args.rate, args.count, args.dry_run)


if __name__ == "__main__":
    main()
