"""The governance invariants, provable without a Daytona sandbox.

`scripts/e2e.py` proves the whole loop but needs live Daytona credentials.
These are the properties that must hold regardless, so they can gate CI:

  1. Derivation maps only the fields the shared schema carries.
  2. A downstream write with no token, a stale token, or a reused token is refused.
  3. The audit trail rejects UPDATE and DELETE and detects tampering.

    uv run python scripts/test_governance.py
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

passed: list[str] = []
failed: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (passed if ok else failed).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def main() -> None:
    tmp = pathlib.Path(tempfile.mkdtemp()) / "test.db"
    from ledgerline import app

    app.DB_PATH = tmp
    app.init_db()

    print("\nDerivation")
    with sqlite3.connect(tmp) as raw:
        raw.row_factory = sqlite3.Row
        before = {"name": "Acme", "credit_limit": 100}
        after = {"name": "Acme GmbH", "credit_limit": 250, "nickname": "unmapped"}
        ids = app.derive_work_orders(raw, "CUST-1", before, after)
        raw.commit()
        orders = {r["target_system"]: r for r in
                  raw.execute("SELECT * FROM work_orders").fetchall()}

    check("one work order per affected target", len(ids) == 2, f"{sorted(orders)}")
    import json
    erp_diff = json.loads(orders["erp"]["diff"])
    acct_diff = json.loads(orders["accounting"]["diff"])
    check("ERP receives credit_limit (mapped for ERP only)",
          "credit_limit_eur" in erp_diff, ", ".join(sorted(erp_diff)))
    check("Accounting does not receive credit_limit",
          "credit_limit_eur" not in acct_diff, ", ".join(sorted(acct_diff)))
    check("unmapped fields are not silently propagated",
          not any("nickname" in d for d in (erp_diff, acct_diff)))
    check("unmapped fields are named in the rationale",
          "nickname" in orders["erp"]["rationale"])
    check("the diff carries before and after for every field",
          all({"before", "after"} <= set(v) for v in erp_diff.values()))
    check("generated code is present and runnable Python",
          compile(orders["erp"]["code"], "<generated>", "exec") is not None)

    print("\nWrite authorisation")
    from fastapi.testclient import TestClient

    client = TestClient(app.app)
    wo = orders["erp"]["id"]

    r = client.post("/systems/erp/records/CUST-1", json={"business_partner_name": "X"})
    check("write with no token refused", r.status_code == 403, f"HTTP {r.status_code}")

    r = client.post("/systems/erp/records/CUST-1", json={"business_partner_name": "X"},
                    headers={"X-Write-Token": "not-a-real-token"})
    check("write with a forged token refused", r.status_code == 403, f"HTTP {r.status_code}")

    # Mint a token the way approve() does, without running a sandbox.
    with sqlite3.connect(tmp) as raw:
        raw.row_factory = sqlite3.Row
        raw.execute("UPDATE work_orders SET status='APPROVED' WHERE id=?", (wo,))
        token = app.mint_write_token(raw, wo)
        raw.commit()

    r = client.post("/systems/erp/records/CUST-1", json={"business_partner_name": "X"},
                    headers={"X-Write-Token": token})
    check("write with an authorised token accepted", r.status_code == 200, f"HTTP {r.status_code}")

    r = client.post("/systems/erp/records/CUST-1", json={"business_partner_name": "Y"},
                    headers={"X-Write-Token": token})
    check("the same token cannot be replayed", r.status_code == 403, f"HTTP {r.status_code}")

    r = client.post("/systems/accounting/records/CUST-1", json={"account_name": "Z"},
                    headers={"X-Write-Token": token})
    check("a token for one target cannot write to another", r.status_code == 403,
          f"HTTP {r.status_code}")

    print("\nAudit trail")
    conn = sqlite3.connect(tmp)
    try:
        conn.execute("UPDATE audit SET actor='forged' WHERE seq=1")
        check("UPDATE blocked", False, "the UPDATE succeeded")
    except sqlite3.IntegrityError:
        check("UPDATE blocked", True)
    try:
        conn.execute("DELETE FROM audit WHERE seq=1")
        check("DELETE blocked", False, "the DELETE succeeded")
    except sqlite3.IntegrityError:
        check("DELETE blocked", True)

    conn.row_factory = sqlite3.Row
    check("chain verifies clean", app.verify_chain(conn)["intact"] is True)

    # Tamper past the triggers to prove the chain, not just the triggers, catches it.
    conn.execute("DROP TRIGGER audit_no_update")
    conn.execute("UPDATE audit SET detail='{\"tampered\":true}' WHERE seq=1")
    conn.commit()
    result = app.verify_chain(conn)
    check("chain detects tampering that bypasses the triggers",
          result["intact"] is False and result["broken_at_seq"] == 1, str(result))
    conn.close()

    print(f"\n{'=' * 62}\n{len(passed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
