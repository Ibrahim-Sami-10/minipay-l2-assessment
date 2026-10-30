#!/usr/bin/env python3
"""MiniPay L2 Support Automation Tool.

Examples:
  python python/support_tool.py --transaction TXN000123
  python python/support_tool.py --transaction TXN00000123 --json
  python python/support_tool.py --stuck --older-than 15 --limit 10
  python python/support_tool.py --health
"""
import argparse
import json
import logging
import os
import sys

from diagnostics import diagnose, normalize_reference
from minipay_client import ApiUnavailable, AuthError, MiniPayClient, NotFound

EXIT_OK, EXIT_ANOMALY, EXIT_NOT_FOUND, EXIT_UNAVAILABLE, EXIT_CONFIG = 0, 1, 2, 3, 4
log = logging.getLogger("support_tool")


def load_config(path=None, environ=None):
    environ = os.environ if environ is None else environ
    values = {}
    path = path or environ.get("MINIPAY_CONFIG")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    for key in ("MINIPAY_API_URL", "MINIPAY_API_KEY", "MINIPAY_TIMEOUT"):
        if key in environ:
            values[key] = environ[key]
    return {
        "url": values.get("MINIPAY_API_URL", "http://localhost:8080"),
        "key": values.get("MINIPAY_API_KEY"),
        "timeout": float(values.get("MINIPAY_TIMEOUT", "10")),
    }


def render_report(payment, result):
    lines = [
        f"MiniPay Support Report - {payment['transaction_ref']}",
        "=" * 55,
        "Transaction Overview",
        f"  Reference : {payment['transaction_ref']} (ID: {payment['id']})",
        f"  Customer  : {payment['customer_id']}",
        f"  Amount    : {payment['amount']}",
        f"  Status    : {payment['status']}",
    ]
    if payment.get("failure_code"):
        lines.append(f"  Failure   : {payment['failure_code']}")
    took = result["processing_seconds"]
    lines += [
        "Timestamps",
        f"  Created   : {payment['created_at']}",
        f"  Completed : {payment.get('completed_at') or '-'}"
        + (f" ({took:.0f}s)" if took is not None else ""),
    ]
    cbs = payment.get("callbacks") or []
    lines.append(f"Callbacks ({len(cbs)} attempt{'s' if len(cbs) != 1 else ''})")
    for c in cbs:
        attempt_no = c.get("attempt_no", "-")
        attempted_at = c.get("attempted_at") or "-"
        http_status = c.get("http_status", "-")
        callback_status = c.get("callback_status", "-")
        lines.append(f"  #{attempt_no}  {attempted_at}  HTTP {http_status}  {callback_status}")
    if not cbs:
        lines.append("  None recorded")

    lines.append("Findings")
    if result["anomalies"]:
        for a in result["anomalies"]:
            lines.append(f"  [{a['severity'].upper():6}] {a['code']}: {a['message']}")
    else:
        lines.append("  [OK] No anomalies detected")

    lines += [
        f"Likely Cause       : {result['likely_cause']}",
        f"Recommended Action : {result['recommended_action']}",
        "=" * 55,
    ]
    return "\n".join(lines)


def cmd_transaction(client, ref, as_json):
    ident = normalize_reference(ref)
    try:
        payment = client.get_payment(ident)
    except NotFound:
        msg = f"Transaction {ident} not found" + (f" (searched for '{ref}')" if ident != ref else "")
        print(json.dumps({"error": "not_found", "message": msg}) if as_json else msg)
        return EXIT_NOT_FOUND

    result = diagnose(payment)
    if as_json:
        print(json.dumps({"transaction": payment, "diagnosis": result}, indent=2, default=str))
    else:
        print(render_report(payment, result))
    return EXIT_ANOMALY if result["anomalies"] else EXIT_OK


def cmd_stuck(client, older_than, limit, as_json):
    data = client.list_payments(status="PROCESSING", older_than_minutes=older_than, limit=limit)
    items = data.get("payments", [])
    if as_json:
        print(json.dumps({"count": data["count"], "older_than_minutes": older_than, "payments": items}, indent=2))
    else:
        print(f"{data['count']} transaction(s) in PROCESSING for > {older_than} min (showing up to {limit}):")
        for p in items:
            print(f"  {p['transaction_ref']}  Customer: {p['customer_id']:>4}  Amount: {p['amount']:>10}  Created: {p['created_at']}")
    return EXIT_ANOMALY if items else EXIT_OK


def cmd_health(client, as_json):
    status, body = client.health()
    healthy = status == 200 and body.get("database") == "up"
    if as_json:
        print(json.dumps({"api": "up", "http_status": status, "body": body, "healthy": healthy}))
    else:
        print(f"API: up (HTTP {status})   Database: {body.get('database', 'unknown')}")
        print("STATUS: HEALTHY" if healthy else "STATUS: UNHEALTHY")
    return EXIT_OK if healthy else EXIT_UNAVAILABLE


def build_parser():
    p = argparse.ArgumentParser(description="MiniPay L2 Support Automation Utility")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--transaction", "-t", metavar="REF", help="Transaction reference or numeric ID")
    g.add_argument("--stuck", action="store_true", help="List stuck PROCESSING transactions")
    g.add_argument("--health", action="store_true", help="Check API and database health")
    p.add_argument("--older-than", type=int, default=15, help="Age in minutes for stuck sweep (default 15)")
    p.add_argument("--limit", type=int, default=20, help="Max records for stuck sweep (default 20)")
    p.add_argument("--json", action="store_true", help="Output in machine-readable JSON format")
    p.add_argument("--config", help="Path to config file")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s", stream=sys.stderr)
    try:
        cfg = load_config(args.config)
    except OSError as exc:
        print(f"Cannot read config file: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    if not cfg["key"]:
        print("Error: MINIPAY_API_KEY is not set (export MINIPAY_API_KEY=... or use --config)", file=sys.stderr)
        return EXIT_CONFIG

    client = MiniPayClient(cfg["url"], cfg["key"], cfg["timeout"])
    try:
        if args.transaction:
            return cmd_transaction(client, args.transaction, args.json)
        if args.stuck:
            return cmd_stuck(client, args.older_than, args.limit, args.json)
        return cmd_health(client, args.json)
    except AuthError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except ApiUnavailable as exc:
        log.error("%s", exc)
        print(f"API unavailable: {exc}", file=sys.stderr)
        return EXIT_UNAVAILABLE


if __name__ == "__main__":
    sys.exit(main())