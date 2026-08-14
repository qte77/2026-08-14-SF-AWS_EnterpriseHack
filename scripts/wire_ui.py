"""Wire the eight Forge screens into one navigable app.

Forge generates each screen as a standalone HTML file whose links are `href="#"`
stubs, so nothing reaches anything else. This injects a shared nav strip into
every screen and repoints the dead breadcrumb links at real files.

Idempotent — it looks for its own marker and re-writes rather than stacking. Run
it after `extract_ui.py` re-copies a pristine mockup.

    uv run python scripts/wire_ui.py
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

MARK_OPEN = "<!-- ledgerline:nav -->"
MARK_CLOSE = "<!-- /ledgerline:nav -->"

# Order is the reviewer's path through the product, not alphabetical.
NAV = [
    ("dashboard.html", "Dashboard", False),
    ("work-orders-list.html", "Work Orders", False),
    ("work-order-detail.html", "Review", False),
    ("audit-trail.html", "Audit Trail", True),
    ("sandbox-execution-log.html", "Sandbox Log", False),
    ("design-system.html", "Design System", False),
    ("login.html", "Login", False),
]

# Dead breadcrumb/CTA targets in the mockups -> where they should actually go.
BREADCRUMBS = {
    ">Dashboard<": "dashboard.html",
    ">Work Orders<": "work-orders-list.html",
    ">Audit Trail<": "audit-trail.html",
}

CSS = """
<style>
.ll-nav{position:sticky;top:0;z-index:9998;display:flex;align-items:center;gap:2px;
flex-wrap:wrap;padding:8px 12px;background:var(--color-surface-raised,#fff);
border-bottom:1px solid var(--color-border,#e0e0e0);
font-family:var(--font-family,system-ui);font-size:13px}
.ll-nav .ll-brand{font-weight:700;margin-right:10px;color:var(--color-text-primary,#161616);
text-decoration:none;letter-spacing:-.01em}
.ll-nav a{padding:5px 10px;border-radius:4px;text-decoration:none;
color:var(--color-text-secondary,#525252)}
.ll-nav a:hover{background:var(--color-surface-hover,#e8e8e8)}
.ll-nav a.on{background:var(--color-primary,#0f62fe);color:#fff}
.ll-nav .ll-tag{font-size:10px;padding:1px 6px;border-radius:99px;margin-left:4px;
background:var(--color-surface,#f4f4f4);color:var(--color-text-muted,#8d8d8d)}
.ll-nav a.on .ll-tag{background:rgba(255,255,255,.25);color:#fff}
.ll-nav .ll-live{background:var(--color-success-bg,#defbe6);color:var(--color-success,#198038)}
.ll-nav .ll-right{margin-left:auto;display:flex;gap:8px;align-items:center}
.ll-nav .ll-right a{font-size:12px}
@media(max-width:640px){.ll-nav .ll-right{display:none}}
</style>
"""


def nav_html(current: str) -> str:
    links = []
    for file, label, live in NAV:
        on = " on" if file == current else ""
        tag = '<span class="ll-tag ll-live">live</span>' if live else \
              '<span class="ll-tag">design</span>'
        links.append(f'<a class="ll-item{on}" href="{file}">{label}{tag}</a>')
    return (
        f'{MARK_OPEN}{CSS}<nav class="ll-nav" aria-label="Ledgerline screens">'
        f'<a class="ll-brand" href="dashboard.html">Ledgerline</a>'
        + "".join(links)
        + '<span class="ll-right">'
        '<a href="https://github.com/qte77/2026-08-14-SF-AWS_EnterpriseHack">Source</a>'
        '</span></nav>'
        f'{MARK_CLOSE}'
    )


def wire(path: pathlib.Path) -> str:
    html = path.read_text()

    # Drop a previously injected strip so re-runs replace rather than stack.
    html = re.sub(re.escape(MARK_OPEN) + ".*?" + re.escape(MARK_CLOSE), "", html,
                  flags=re.DOTALL)

    strip = nav_html(path.name)
    if "<body" in html:
        html = re.sub(r"(<body[^>]*>)", r"\1" + strip.replace("\\", "\\\\"), html, count=1)
    else:
        html = strip + html

    # The mockups' breadcrumbs are href="#"; point them at the real screens.
    for needle, target in BREADCRUMBS.items():
        html = html.replace(f'<a href="#"{needle}', f'<a href="{target}"{needle}')
        html = html.replace(f'href="#"{needle}', f'href="{target}"{needle}')
    return html


def main() -> None:
    changed = 0
    for file, _label, _live in NAV:
        path = UI / file
        if not path.exists():
            print(f"  skip (absent) {file}")
            continue
        new = wire(path)
        if new != path.read_text():
            path.write_text(new)
            changed += 1
        print(f"  wired {file}")
    # Not in the nav — it is a modal overlay, not a destination.
    print(f"\n{changed} file(s) updated; session-timeout-warning.html left standalone")


if __name__ == "__main__":
    main()
