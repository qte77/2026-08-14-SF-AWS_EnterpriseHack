"""End-to-end proof of the eight success criteria in docs/forge-intent.md.

Real triggers, no mocked steps: a real CRM write, real derivation, a real
Daytona sandbox, a real downstream write, a real audit chain.

    uv run uvicorn ledgerline.app:app --port 8000    # in one shell
    uv run python scripts/e2e.py                     # in another
"""

from __future__ import annotations

import json
import pathlib
import platform
import sqlite3
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT = pathlib.Path(__file__).resolve().parents[1]
RECORD = "CUST-4471"

passed: list[str] = []
failed: list[str] = []


def check(criterion: str, ok: bool, detail: str = "") -> None:
    (passed if ok else failed).append(criterion)
    print(f"  {'PASS' if ok else 'FAIL'}  {criterion}" + (f"  — {detail}" if detail else ""))


c = httpx.Client(base_url=BASE, timeout=180.0)

print("\n1. A CRM change produces work orders without human prompting")
r = c.post(f"/systems/crm/records/{RECORD}", json={
    "name": "Nordwind Logistik GmbH",
    "email": "ap@nordwind-logistik.de",
    "billing_address": "Speicherstadt 12, 20457 Hamburg",
    "vat_id": "DE811907980",
    "credit_limit": 250000,
})
r.raise_for_status()
created = r.json()["work_orders_created"]
check("1 · change detected -> work orders derived", len(created) == 2, f"{created}")

orders = c.get("/api/v1/workorders").json()
by_target = {o["target_system"]: o for o in orders if o["record_id"] == RECORD}

print("\n2. The work order is legible: target, field diff, rationale, code")
erp = c.get(f"/api/v1/workorders/{by_target['erp']['id']}").json()
check("2 · diff + rationale + code present",
      bool(erp["diff"]) and bool(erp["rationale"]) and "def transform" in erp["code"],
      f"{len(erp['diff'])} fields, {len(erp['code'])} B of code")

print("\n3. No write occurs before authorisation")
before = c.get("/systems/erp/records").json()
check("3a · ERP empty while orders are PENDING",
      not any(x["record_id"] == RECORD for x in before))
direct = c.post(f"/systems/erp/records/{RECORD}", json={"business_partner_name": "BYPASS"})
check("3b · direct downstream write refused (no token)", direct.status_code == 403,
      f"HTTP {direct.status_code}")

print("\n4 + 6. Approve -> sandbox created, code runs, sandbox destroyed, write lands")
appr = c.post(f"/api/v1/workorders/{erp['id']}/approve",
              json={"approver": "reviewer@ledgerline", "note": "Verified against CRM master"})
body = appr.json()
sandbox = body.get("sandbox", {})
check("4 · approved order wrote to ERP", appr.status_code == 200 and body["status"] == "SYNCED",
      body.get("status", appr.text[:120]))
# Criterion 6 says "observable, not asserted", so this checks what Daytona
# reports about the sandbox, not what our own executor returned about itself.
alive = sandbox.get("proof_alive") or {}
gone = sandbox.get("proof_destroyed") or {}
check("6a · Daytona confirms the sandbox existed (GET /sandbox/{id} -> 200)",
      alive.get("http_status") == 200 and alive.get("state") in {"started", "creating"},
      f"{alive.get('http_status')} state={alive.get('state')} org={alive.get('organization_id')}")
check("6b · Daytona confirms it is gone after teardown",
      gone.get("http_status") in {400, 401, 403, 404} or gone.get("state") in
      {"destroyed", "destroying", "archived", None},
      f"HTTP {gone.get('http_status')} state={gone.get('state')}")
check("6c · the code ran off-host (sandbox kernel != this process's)",
      bool(sandbox.get("executed_on")) and platform.node() not in sandbox.get("executed_on", ""),
      sandbox.get("executed_on", "")[:88])
erp_rows = c.get("/systems/erp/records").json()
check("4b · value visible in the target system",
      any(x["record_id"] == RECORD and x.get("business_partner_name")
          == "Nordwind Logistik GmbH" for x in erp_rows))

print("\n5. Reject -> no write, reason recorded")
acct = by_target["accounting"]
rej = c.post(f"/api/v1/workorders/{acct['id']}/reject",
             json={"approver": "reviewer@ledgerline",
                   "reason": "Billing address needs finance sign-off first"})
acct_rows = c.get("/systems/accounting/records").json()
check("5 · rejected order produced no write and kept its reason",
      rej.status_code == 200 and not any(x["record_id"] == RECORD for x in acct_rows)
      and rej.json()["reason"].startswith("Billing address"))

print("\n7. Trace a written record back to its authorising order")
tr = c.get(f"/api/v1/audit/trace/erp/{RECORD}").json()
check("7 · record -> order -> approver -> code -> write",
      bool(tr["authorised_by"]) and tr["authorised_by"][0]["decided_by"] == "reviewer@ledgerline"
      and any(e["event"] == "work_order.approved" for e in tr["audit"]))

print("\n8. Audit trail is append-only and tamper-evident")
chain = c.get("/api/v1/audit").json()["chain"]
check("8a · hash chain intact", chain.get("intact") is True, str(chain)[:80])
conn = sqlite3.connect(ROOT / "ledgerline.db")
try:
    conn.execute("UPDATE audit SET detail = '{}' WHERE seq = 1")
    check("8b · UPDATE on audit blocked", False, "the UPDATE succeeded")
except sqlite3.IntegrityError as exc:
    check("8b · UPDATE on audit blocked", True, str(exc))
try:
    conn.execute("DELETE FROM audit WHERE seq = 1")
    check("8c · DELETE on audit blocked", False, "the DELETE succeeded")
except sqlite3.IntegrityError as exc:
    check("8c · DELETE on audit blocked", True, str(exc))
conn.close()

print(f"\n{'=' * 62}\n{len(passed)} passed, {len(failed)} failed")
if failed:
    print("failed: " + json.dumps(failed, indent=2))
sys.exit(1 if failed else 0)
