"""Render-check the wired screens in a real browser.

Rendering and wiring cannot be unit-tested meaningfully — the browser is the
test. This drives the audit-trail screen the way a judge would: load it, read
the chain banner, trace a record, filter, export, and fail on any console error.

    uv run python scripts/ui_e2e.py [base_url]
"""

from __future__ import annotations

import pathlib
import sys

from patchright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
SHOTS = pathlib.Path(__file__).resolve().parents[1] / "docs/screenshots"
RECORD = "CUST-4471"

VIEWPORTS = [("desktop", 1440, 900), ("mobile", 390, 844)]

passed: list[str] = []
failed: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (passed if ok else failed).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    console: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, width, height in VIEWPORTS:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()
            page.on("console", lambda m: console.append(f"{m.type}: {m.text}")
                    if m.type == "error" else None)
            page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
            failed_requests: list[str] = []
            page.on("requestfailed",
                    lambda r, sink=failed_requests: sink.append(f"{r.method} {r.url}"))

            print(f"\n[{label} {width}x{height}]")
            page.goto(f"{BASE}/ui/audit-trail.html", wait_until="networkidle")

            # The chain banner must resolve to a real verdict, not stay "checking…".
            page.wait_for_function(
                "document.getElementById('chainBadge').textContent.indexOf('checking') === -1",
                timeout=15000)
            badge = page.inner_text("#chainBadge")
            head = page.inner_text("#chainHead")
            check(f"{label} · chain banner verified", "verified" in badge, f"{badge} {head[:40]}")

            rows = page.locator(".audit-entry").count()
            check(f"{label} · live entries rendered", rows > 0, f"{rows} entries")

            count_text = page.inner_text("#resultCount")
            check(f"{label} · no mock data left", "248" not in count_text, count_text[:60])

            # Expand the first entry — the payload must carry a real hash.
            page.locator(".audit-entry-header").first.click()
            body = page.locator(".audit-entry .payload-block").first.inner_text()
            check(f"{label} · entry expands with hash chain",
                  '"hash"' in body and '"prev_hash"' in body, body[:50].replace("\n", " "))

            # Trace a written record end to end (criterion 7, on screen).
            page.select_option("#traceSystem", "erp")
            page.fill("#traceRecord", RECORD)
            page.click("#traceBtn")
            page.wait_for_selector("#traceResult.visible .trace-step", timeout=15000)
            steps = page.locator("#traceResult .trace-step .v").all_inner_texts()
            check(f"{label} · trace walks record -> order -> approver -> sandbox",
                  len(steps) >= 5 and RECORD in steps[0], " | ".join(s[:18] for s in steps))
            check(f"{label} · trace shows the code that ran",
                  "def transform" in page.locator("#traceResult .payload-block").last.inner_text())

            # Filtering must actually reduce the set.
            before = page.locator(".audit-entry").count()
            page.select_option("#fEvent", "work_order.approved")
            page.wait_for_timeout(300)
            after = page.locator(".audit-entry").count()
            check(f"{label} · event filter narrows the list", after < before,
                  f"{before} -> {after}")
            page.click("#clearBtn")

            page.screenshot(path=str(SHOTS / f"audit-trail-{label}.png"), full_page=True)
            print(f"        screenshot -> docs/screenshots/audit-trail-{label}.png")

            check(f"{label} · no failed network requests", not failed_requests,
                  "; ".join(failed_requests[:2]))
            ctx.close()
        browser.close()

    app_errors = [c for c in console if "fonts.googleapis.com" not in c]
    check("no console errors", not app_errors, "; ".join(app_errors[:3]))

    print(f"\n{'=' * 62}\n{len(passed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
