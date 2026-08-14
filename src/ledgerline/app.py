"""Ledgerline — governed cross-system sync agent.

Implements the Forge spec pipeline (Intent -> BRD -> PRD -> Architecture -> UI Design)
at the scope the arc plan allows: the governance spine, end to end.

Governance invariants (plan 0001 items 9, 10, 13; Intent "Constraints"):

  1. No write to a downstream system without an authorised work order.
     Enforced structurally, not by convention: ERP and Accounting write endpoints
     require a single-use write token that is minted only inside `approve()`.
  2. Agent-derived integration code never runs in this process.
     It runs in a Daytona sandbox created for the order and destroyed after it.
  3. The audit trail is append-only.
     Enforced by SQLite triggers that raise on UPDATE and DELETE, plus a
     SHA-256 hash chain so any tampering is detectable.

Deviation from Architecture_Options.md, recorded deliberately: that document
selects Node/TypeScript/Fastify, PostgreSQL 16, NATS JetStream, Redis and
Docker+gVisor against a five-week Phase 1 premise. This build is a one-day
hackathon slice on the mandated platforms, so it keeps the architecture's
*domain decomposition and governance properties* and substitutes
Python/FastAPI, SQLite, in-process dispatch and Daytona sandboxes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import secrets
import sqlite3
import textwrap
import uuid
from contextlib import closing
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "ledgerline.db"
UI_DIR = ROOT / "ui"

SYSTEMS = ("crm", "erp", "accounting")
SOURCE_OF_TRUTH = "crm"
TARGETS = ("erp", "accounting")


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def _load_env() -> dict[str, str]:
    """Read .env without a dependency. Real values stay out of git (.gitignore)."""
    env: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    env.update({k: v for k, v in os.environ.items() if k in env or k.startswith(("DAYTONA_", "WEBHOOK_"))})
    return env


ENV = _load_env()
DAYTONA_API_KEY = ENV.get("DAYTONA_API_KEY", "")
DAYTONA_API_URL = ENV.get("DAYTONA_API_URL", "https://app.daytona.io/api")
WEBHOOK_SECRET = ENV.get("WEBHOOK_SECRET", "ledgerline-dev-secret")


# --------------------------------------------------------------------------
# Shared record schema — the one record type in scope (Intent: "one record type")
# --------------------------------------------------------------------------

# field -> per-target mapping. A field absent from a target's map is not propagated.
RECORD_SCHEMA: dict[str, dict[str, str]] = {
    "name":           {"erp": "business_partner_name", "accounting": "account_name"},
    "email":          {"erp": "contact_email",         "accounting": "billing_email"},
    "billing_address":{"erp": "ship_to_address",       "accounting": "billing_address"},
    "vat_id":         {"erp": "tax_number",            "accounting": "tax_registration"},
    "credit_limit":   {"erp": "credit_limit_eur"},  # not carried by Accounting
}

RATIONALE = {
    "erp": "ERP holds the fulfilment view of this customer; the field is mapped "
           "from the CRM master record via the shared Customer schema.",
    "accounting": "Accounting holds the billing view of this customer; the field is "
                  "mapped from the CRM master record via the shared Customer schema.",
}


# --------------------------------------------------------------------------
# Storage — app tables plus an append-only audit ledger
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    system     TEXT NOT NULL,
    record_id  TEXT NOT NULL,
    data       TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (system, record_id)
);

CREATE TABLE IF NOT EXISTS work_orders (
    id            TEXT PRIMARY KEY,
    record_id     TEXT NOT NULL,
    source_system TEXT NOT NULL,
    target_system TEXT NOT NULL,
    diff          TEXT NOT NULL,
    payload       TEXT NOT NULL,
    rationale     TEXT NOT NULL,
    code          TEXT NOT NULL,
    status        TEXT NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL,
    decided_at    TEXT,
    decided_by    TEXT,
    decision_note TEXT,
    write_token   TEXT,
    token_used    INTEGER NOT NULL DEFAULT 0,
    sandbox_id    TEXT,
    sandbox_log   TEXT
);

CREATE TABLE IF NOT EXISTS audit (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    event         TEXT NOT NULL,
    work_order_id TEXT,
    actor         TEXT NOT NULL,
    detail        TEXT NOT NULL,
    prev_hash     TEXT NOT NULL,
    hash          TEXT NOT NULL
);

-- The audit trail is append-only by construction, including on rejection.
CREATE TRIGGER IF NOT EXISTS audit_no_update
BEFORE UPDATE ON audit
BEGIN SELECT RAISE(ABORT, 'audit trail is append-only: UPDATE denied'); END;

CREATE TRIGGER IF NOT EXISTS audit_no_delete
BEFORE DELETE ON audit
BEGIN SELECT RAISE(ABORT, 'audit trail is append-only: DELETE denied'); END;
"""

GENESIS = "0" * 64


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with closing(db()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def audit(conn: sqlite3.Connection, event: str, actor: str, detail: dict[str, Any],
          work_order_id: str | None = None) -> str:
    """Append one tamper-evident entry. Each hash covers the previous hash."""
    row = conn.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
    prev = row["hash"] if row else GENESIS
    ts = now()
    body = json.dumps(detail, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(
        f"{prev}|{ts}|{event}|{work_order_id or ''}|{actor}|{body}".encode()
    ).hexdigest()
    conn.execute(
        "INSERT INTO audit (ts, event, work_order_id, actor, detail, prev_hash, hash)"
        " VALUES (?,?,?,?,?,?,?)",
        (ts, event, work_order_id, actor, body, prev, digest),
    )
    return digest


def verify_chain(conn: sqlite3.Connection) -> dict[str, Any]:
    """Recompute the whole chain. Any edit or gap shows up here."""
    prev = GENESIS
    for row in conn.execute("SELECT * FROM audit ORDER BY seq ASC"):
        expect = hashlib.sha256(
            f"{prev}|{row['ts']}|{row['event']}|{row['work_order_id'] or ''}"
            f"|{row['actor']}|{row['detail']}".encode()
        ).hexdigest()
        if expect != row["hash"] or row["prev_hash"] != prev:
            return {"intact": False, "broken_at_seq": row["seq"]}
        prev = row["hash"]
    return {"intact": True, "head": prev}


# --------------------------------------------------------------------------
# Derivation — change event to work orders
# --------------------------------------------------------------------------

def derive_work_orders(conn: sqlite3.Connection, record_id: str,
                       before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """One work order per target system that has at least one mapped, changed field."""
    created: list[str] = []
    changed = {k: v for k, v in after.items() if before.get(k) != v}

    for target in TARGETS:
        diff = {
            RECORD_SCHEMA[field][target]: {"before": before.get(field), "after": value}
            for field, value in changed.items()
            if field in RECORD_SCHEMA and target in RECORD_SCHEMA[field]
        }
        if not diff:
            continue

        payload = {name: change["after"] for name, change in diff.items()}
        unmapped = sorted(f for f in changed if f not in RECORD_SCHEMA or target not in RECORD_SCHEMA.get(f, {}))
        rationale = RATIONALE[target]
        if unmapped:
            rationale += f" Not carried by this system, left unchanged: {', '.join(unmapped)}."

        wo_id = f"WO-{uuid.uuid4().hex[:8].upper()}"
        code = generated_code(wo_id, target, record_id, payload)
        conn.execute(
            "INSERT INTO work_orders (id, record_id, source_system, target_system, diff,"
            " payload, rationale, code, status, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,'PENDING',?)",
            (wo_id, record_id, SOURCE_OF_TRUTH, target, json.dumps(diff),
             json.dumps(payload), rationale, code, now()),
        )
        audit(conn, "work_order.derived", "agent",
              {"target": target, "record_id": record_id, "diff": diff,
               "rationale": rationale}, wo_id)
        created.append(wo_id)
    return created


def generated_code(wo_id: str, target: str, record_id: str, payload: dict[str, Any]) -> str:
    """The integration code the agent proposes. Shown verbatim in the work order.

    This is what executes inside the Daytona sandbox — never in this process.
    """
    fields = "\n".join(f"    {name!r}: {value!r}," for name, value in payload.items())
    return (
        "# Ledgerline generated integration code\n"
        f"# work order : {wo_id}\n"
        f"# target     : {target}\n"
        f"# record     : {record_id}\n"
        "#\n"
        "# Runs inside a disposable Daytona sandbox created for this order.\n"
        "# It transforms the authorised payload and emits it; it holds no\n"
        "# credential and opens no connection of its own.\n"
        "import json\n"
        "\n"
        f"RECORD_ID = {record_id!r}\n"
        "PAYLOAD = {\n"
        f"{fields}\n"
        "}\n"
        "\n"
        "def transform(payload):\n"
        "    out = {}\n"
        "    for field, value in payload.items():\n"
        "        out[field] = value.strip() if isinstance(value, str) else value\n"
        "    return out\n"
        "\n"
        'result = {"record_id": RECORD_ID, "fields": transform(PAYLOAD)}\n'
        'print("LEDGERLINE_RESULT " + json.dumps(result))\n'
    )


# --------------------------------------------------------------------------
# Sandboxed execution — Daytona, one sandbox per authorised order
# --------------------------------------------------------------------------

def _daytona_probe(sandbox_id: str) -> dict[str, Any]:
    """Ask Daytona itself about a sandbox.

    Criterion 6 requires the sandbox lifecycle to be *observable, not asserted*.
    Trusting our own return value is self-referential, so both the live and the
    torn-down state are read back from the Daytona API and stored in the audit
    trail, where an auditor can check them against the vendor independently.

    Note: this key is scoped to create/get/delete. `GET /sandbox` (list) and
    `/users/me` return 401, so a *list* view will look empty even while a
    sandbox is running. `GET /sandbox/{id}` is the authoritative check.
    """
    import httpx

    url = f"{DAYTONA_API_URL.rstrip('/')}/sandbox/{sandbox_id}"
    try:
        r = httpx.get(url, headers={"Authorization": f"Bearer {DAYTONA_API_KEY}"},
                      timeout=20)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return {
            "endpoint": f"GET /sandbox/{sandbox_id}",
            "http_status": r.status_code,
            "state": body.get("state"),
            "organization_id": body.get("organizationId"),
            "target": body.get("target"),
            "snapshot": body.get("snapshot"),
        }
    except Exception as exc:  # noqa: BLE001 - the probe must never break execution
        return {"endpoint": f"GET /sandbox/{sandbox_id}", "error": f"{type(exc).__name__}: {exc}"}


def run_in_sandbox(code: str, hold_seconds: int = 0) -> dict[str, Any]:
    """Create a sandbox, run the authorised code, destroy the sandbox.

    Only reachable after a human authorises the work order.

    `hold_seconds` keeps the sandbox alive after the run so it can be watched in
    the Daytona dashboard during a demo. It changes nothing about the isolation
    guarantee — the sandbox is still destroyed, just later.
    """
    import time

    from daytona import Daytona, DaytonaConfig

    config = DaytonaConfig(api_key=DAYTONA_API_KEY, api_url=DAYTONA_API_URL)
    daytona = Daytona(config)

    sandbox = daytona.create()
    sandbox_id = getattr(sandbox, "id", None) or str(sandbox)
    created_at = now()
    alive_proof = _daytona_probe(sandbox_id)

    run: dict[str, Any] = {"sandbox_id": sandbox_id, "created_at": created_at,
                           "proof_alive": alive_proof}
    try:
        response = sandbox.process.code_run(code)
        exit_code = getattr(response, "exit_code", 0)
        output = getattr(response, "result", "") or ""
        # Independent evidence the code ran off-host: the sandbox reports its own
        # kernel and hostname, which differ from this process's.
        host = sandbox.process.code_run(
            "import platform, os; print(platform.node(), '|', platform.platform(), '|', os.getcwd())"
        )
        run["executed_on"] = (getattr(host, "result", "") or "").strip()
        if exit_code != 0:
            run.update({"ok": False, "error": f"exit {exit_code}: {output}", "stdout": output})
            return run
        result = None
        for line in output.splitlines():
            if line.startswith("LEDGERLINE_RESULT "):
                result = json.loads(line[len("LEDGERLINE_RESULT "):])
        run.update({"ok": True, "result": result, "stdout": output})
        return run
    finally:
        if hold_seconds:
            time.sleep(hold_seconds)
        try:
            sandbox.delete()
            run["proof_destroyed"] = _daytona_probe(sandbox_id)
        except Exception as exc:  # noqa: BLE001 - teardown must not mask the run result
            run["teardown_error"] = f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

app = FastAPI(title="Ledgerline", version="0.1.0")
init_db()


def mint_write_token(conn: sqlite3.Connection, wo_id: str) -> str:
    """A downstream write is only possible with a token minted at approval."""
    token = hmac.new(WEBHOOK_SECRET.encode(),
                     f"{wo_id}|{secrets.token_hex(16)}".encode(),
                     hashlib.sha256).hexdigest()
    conn.execute("UPDATE work_orders SET write_token = ?, token_used = 0 WHERE id = ?",
                 (token, wo_id))
    return token


def _row(conn: sqlite3.Connection, wo_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (wo_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"unknown work order {wo_id}")
    return row


@app.post("/systems/{system}/records/{record_id}")
async def write_record(system: str, record_id: str, request: Request,
                       x_write_token: str | None = Header(default=None)):
    """Write into a system of record.

    CRM is the source of truth and is written by people. ERP and Accounting are
    downstream: they refuse any write that does not carry a single-use token
    minted by an approval. This is invariant 1, enforced in the write path.
    """
    if system not in SYSTEMS:
        raise HTTPException(404, f"unknown system {system}")
    data = await request.json()

    with closing(db()) as conn:
        if system in TARGETS:
            row = conn.execute(
                "SELECT * FROM work_orders WHERE write_token = ? AND target_system = ?"
                " AND record_id = ? AND status = 'APPROVED' AND token_used = 0",
                (x_write_token or "", system, record_id),
            ).fetchone()
            if row is None:
                audit(conn, "write.denied", "system",
                      {"system": system, "record_id": record_id,
                       "reason": "no valid authorised work order token"})
                conn.commit()
                raise HTTPException(
                    403,
                    "refused: downstream writes require a single-use token from an "
                    "authorised work order",
                )
            conn.execute("UPDATE work_orders SET token_used = 1 WHERE id = ?", (row["id"],))

        prev = conn.execute("SELECT data FROM records WHERE system = ? AND record_id = ?",
                            (system, record_id)).fetchone()
        before = json.loads(prev["data"]) if prev else {}
        after = {**before, **data}
        conn.execute(
            "INSERT INTO records (system, record_id, data, updated_at) VALUES (?,?,?,?)"
            " ON CONFLICT(system, record_id) DO UPDATE SET data = excluded.data,"
            " updated_at = excluded.updated_at",
            (system, record_id, json.dumps(after), now()),
        )

        created: list[str] = []
        if system == SOURCE_OF_TRUTH:
            # Change detection: a CRM edit is the trigger for derivation.
            audit(conn, "change.detected", "crm",
                  {"record_id": record_id,
                   "changed": sorted(k for k in after if before.get(k) != after.get(k))})
            created = derive_work_orders(conn, record_id, before, after)
        else:
            audit(conn, "write.executed", "sandbox",
                  {"system": system, "record_id": record_id, "fields": data},
                  work_order_id=row["id"])
        conn.commit()

    return {"system": system, "record_id": record_id, "record": after,
            "work_orders_created": created}


@app.get("/systems/{system}/records")
def list_records(system: str):
    with closing(db()) as conn:
        rows = conn.execute("SELECT * FROM records WHERE system = ? ORDER BY record_id",
                            (system,)).fetchall()
    return [{"record_id": r["record_id"], "updated_at": r["updated_at"],
             **json.loads(r["data"])} for r in rows]


@app.get("/api/v1/workorders")
def list_work_orders(status: str | None = None):
    query = "SELECT * FROM work_orders"
    params: tuple[Any, ...] = ()
    if status:
        query += " WHERE status = ?"
        params = (status.upper(),)
    query += " ORDER BY created_at DESC"
    with closing(db()) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_public(r) for r in rows]


@app.get("/api/v1/workorders/{wo_id}")
def get_work_order(wo_id: str):
    with closing(db()) as conn:
        return _public(_row(conn, wo_id), include_code=True)


def _public(row: sqlite3.Row, include_code: bool = False) -> dict[str, Any]:
    out = {
        "id": row["id"],
        "record_id": row["record_id"],
        "source_system": row["source_system"],
        "target_system": row["target_system"],
        "diff": json.loads(row["diff"]),
        "payload": json.loads(row["payload"]),
        "rationale": row["rationale"],
        "status": row["status"],
        "version": row["version"],
        "created_at": row["created_at"],
        "decided_at": row["decided_at"],
        "decided_by": row["decided_by"],
        "decision_note": row["decision_note"],
        "sandbox_id": row["sandbox_id"],
    }
    if include_code:
        out["code"] = row["code"]
        out["sandbox_log"] = json.loads(row["sandbox_log"]) if row["sandbox_log"] else None
    return out


@app.post("/api/v1/workorders/{wo_id}/approve")
async def approve(wo_id: str, request: Request):
    """Authorise the order, then execute its code in a sandbox created for it."""
    body = await request.json() if await request.body() else {}
    approver = body.get("approver", "approver@ledgerline")
    version = body.get("version")
    amendment = body.get("amend")  # optional {field: value} overrides

    with closing(db()) as conn:
        row = _row(conn, wo_id)
        if row["status"] != "PENDING":
            raise HTTPException(409, f"work order is {row['status']}, not PENDING")
        if version is not None and int(version) != row["version"]:
            raise HTTPException(409, "work order changed since it was loaded")

        payload = json.loads(row["payload"])
        code = row["code"]
        if amendment:
            unknown = sorted(set(amendment) - set(payload))
            if unknown:
                raise HTTPException(400, f"amendment touches unmapped fields: {unknown}")
            payload = {**payload, **amendment}
            code = generated_code(wo_id, row["target_system"], row["record_id"], payload)
            conn.execute(
                "UPDATE work_orders SET payload = ?, code = ?, version = version + 1 WHERE id = ?",
                (json.dumps(payload), code, wo_id))
            audit(conn, "work_order.amended", approver,
                  {"amendment": amendment, "payload": payload}, wo_id)

        conn.execute(
            "UPDATE work_orders SET status='APPROVED', decided_at=?, decided_by=?,"
            " decision_note=? WHERE id = ?",
            (now(), approver, body.get("note"), wo_id))
        token = mint_write_token(conn, wo_id)
        audit(conn, "work_order.approved", approver,
              {"target": row["target_system"], "payload": payload,
               "code_sha256": hashlib.sha256(code.encode()).hexdigest()}, wo_id)
        conn.commit()

    # Execution happens outside the app process, in a sandbox for this order only.
    try:
        run = run_in_sandbox(code, hold_seconds=int(body.get("hold_seconds", 0)))
    except Exception as exc:  # noqa: BLE001 - surfaced to the reviewer and the audit trail
        run = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "sandbox_id": None}

    with closing(db()) as conn:
        run["destroyed_at"] = now()
        conn.execute("UPDATE work_orders SET sandbox_id = ?, sandbox_log = ? WHERE id = ?",
                     (run.get("sandbox_id"), json.dumps(run), wo_id))
        audit(conn, "sandbox.created", "agent",
              {"sandbox_id": run.get("sandbox_id"), "at": run.get("created_at"),
               "daytona_says": run.get("proof_alive"),
               "executed_on": run.get("executed_on")}, wo_id)

        if not run.get("ok"):
            conn.execute("UPDATE work_orders SET status='FAILED' WHERE id = ?", (wo_id,))
            audit(conn, "sandbox.destroyed", "agent",
                  {"sandbox_id": run.get("sandbox_id"), "at": run["destroyed_at"]}, wo_id)
            audit(conn, "work_order.failed", "agent", {"error": run.get("error")}, wo_id)
            conn.commit()
            return JSONResponse(status_code=502,
                                content={"work_order": wo_id, "status": "FAILED",
                                         "sandbox": run})
        audit(conn, "sandbox.destroyed", "agent",
              {"sandbox_id": run.get("sandbox_id"), "at": run["destroyed_at"],
               "daytona_says": run.get("proof_destroyed")}, wo_id)
        conn.commit()

    # The sandbox produced the payload; the write is carried out under the token
    # minted at approval, so the downstream system can verify authorisation.
    fields = (run.get("result") or {}).get("fields", payload)
    import httpx

    async with httpx.AsyncClient(base_url=str(request.base_url).rstrip("/")) as client:
        resp = await client.post(
            f"/systems/{row['target_system']}/records/{row['record_id']}",
            json=fields, headers={"X-Write-Token": token})
    if resp.status_code != 200:
        with closing(db()) as conn:
            conn.execute("UPDATE work_orders SET status='FAILED' WHERE id = ?", (wo_id,))
            audit(conn, "work_order.failed", "agent", {"write_error": resp.text}, wo_id)
            conn.commit()
        raise HTTPException(502, f"downstream write refused: {resp.text}")

    with closing(db()) as conn:
        conn.execute("UPDATE work_orders SET status='SYNCED' WHERE id = ?", (wo_id,))
        audit(conn, "work_order.synced", "agent",
              {"target": row["target_system"], "fields": fields}, wo_id)
        conn.commit()

    return {"work_order": wo_id, "status": "SYNCED", "sandbox": run, "written": fields}


@app.post("/api/v1/workorders/{wo_id}/reject")
async def reject(wo_id: str, request: Request):
    body = await request.json() if await request.body() else {}
    reason = body.get("reason")
    if not reason:
        raise HTTPException(400, "a rejection must carry a reason")
    approver = body.get("approver", "approver@ledgerline")

    with closing(db()) as conn:
        row = _row(conn, wo_id)
        if row["status"] != "PENDING":
            raise HTTPException(409, f"work order is {row['status']}, not PENDING")
        conn.execute(
            "UPDATE work_orders SET status='REJECTED', decided_at=?, decided_by=?,"
            " decision_note=? WHERE id = ?", (now(), approver, reason, wo_id))
        # Rejections are recorded, never erased.
        audit(conn, "work_order.rejected", approver, {"reason": reason}, wo_id)
        conn.commit()
    return {"work_order": wo_id, "status": "REJECTED", "reason": reason}


@app.get("/api/v1/audit")
def audit_trail(work_order_id: str | None = None, limit: int = 200):
    query = "SELECT * FROM audit"
    params: tuple[Any, ...] = ()
    if work_order_id:
        query += " WHERE work_order_id = ?"
        params = (work_order_id,)
    query += " ORDER BY seq DESC LIMIT ?"
    with closing(db()) as conn:
        rows = conn.execute(query, (*params, limit)).fetchall()
        chain = verify_chain(conn)
    return {
        "chain": chain,
        "entries": [{"seq": r["seq"], "ts": r["ts"], "event": r["event"],
                     "work_order_id": r["work_order_id"], "actor": r["actor"],
                     "detail": json.loads(r["detail"]), "prev_hash": r["prev_hash"],
                     "hash": r["hash"]} for r in rows],
    }


@app.get("/api/v1/audit/trace/{system}/{record_id}")
def trace(system: str, record_id: str):
    """Criterion 7: any downstream record traces back to its authorising order."""
    with closing(db()) as conn:
        rec = conn.execute("SELECT * FROM records WHERE system=? AND record_id=?",
                           (system, record_id)).fetchone()
        if rec is None:
            raise HTTPException(404, "no such record")
        orders = conn.execute(
            "SELECT * FROM work_orders WHERE target_system=? AND record_id=?"
            " ORDER BY created_at", (system, record_id)).fetchall()
        entries = conn.execute(
            "SELECT * FROM audit WHERE work_order_id IN"
            " (SELECT id FROM work_orders WHERE target_system=? AND record_id=?)"
            " ORDER BY seq", (system, record_id)).fetchall()
    return {
        "record": {"system": system, "record_id": record_id, **json.loads(rec["data"])},
        "authorised_by": [_public(o, include_code=True) for o in orders],
        "audit": [{"seq": e["seq"], "ts": e["ts"], "event": e["event"],
                   "actor": e["actor"], "hash": e["hash"]} for e in entries],
    }


@app.get("/api/v1/dashboard")
def dashboard():
    with closing(db()) as conn:
        counts = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) n FROM work_orders GROUP BY status")}
        chain = verify_chain(conn)
        recent = conn.execute(
            "SELECT * FROM work_orders ORDER BY created_at DESC LIMIT 10").fetchall()
    return {"counts": counts, "audit_chain": chain,
            "recent": [_public(r) for r in recent]}


@app.get("/", response_class=HTMLResponse)
def index():
    pages = json.loads((UI_DIR / "pages.json").read_text()) if (UI_DIR / "pages.json").exists() else []
    links = "\n".join(
        f'<li><a href="/ui/{p["file"]}">{p["name"]}</a> — {p["description"][:110]}</li>'
        for p in pages)
    return f"""<!doctype html><meta charset="utf-8"><title>Ledgerline</title>
<style>body{{font:15px/1.6 system-ui;margin:3rem auto;max-width:52rem;padding:0 1rem}}
code{{background:#f4f4f5;padding:.1rem .3rem;border-radius:3px}}li{{margin:.4rem 0}}</style>
<h1>Ledgerline</h1>
<p>Enterprise data gets typed three times. Ledgerline types it once — and no write
happens until a human authorises it.</p>
<h2>Forge UI (8 screens)</h2><ul>{links}</ul>
<h2>Live API</h2><ul>
<li><a href="/api/v1/dashboard">/api/v1/dashboard</a></li>
<li><a href="/api/v1/workorders">/api/v1/workorders</a></li>
<li><a href="/api/v1/audit">/api/v1/audit</a> — with hash-chain verification</li>
<li><a href="/systems/erp/records">/systems/erp/records</a></li>
<li><a href="/docs">/docs</a> — OpenAPI</li></ul>"""


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")
