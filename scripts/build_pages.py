"""Build the GitHub Pages site.

A Daytona preview URL dies with its sandbox; a Pages URL does not. So the
screens are published to Pages and pointed at whichever deploy is current, via
the `?api=` parameter the audit screen reads. Redeploy, rebuild, same link.

    uv run python scripts/build_pages.py    # -> _site/
"""

from __future__ import annotations

import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI = ROOT / "ui"
SITE = ROOT / "_site"
LATEST = ROOT / "daytona_results/latest.json"
SHOTS = ROOT / "docs/screenshots"

REPO_URL = "https://github.com/qte77/2026-08-14-SF-AWS_EnterpriseHack"

# Which screens are wired to the API, and which are still the Forge design.
LIVE = {"audit-trail.html"}


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(UI, SITE)
    if SHOTS.exists():
        shutil.copytree(SHOTS, SITE / "screenshots", dirs_exist_ok=True)

    deploy = json.loads(LATEST.read_text()) if LATEST.exists() else {}
    api = deploy.get("hosted_url", "")
    pages = json.loads((UI / "pages.json").read_text())

    def link(file: str) -> str:
        return f"{file}?api={api}" if file in LIVE and api else file

    rows = "\n".join(
        f'<li><a href="{link(p["file"])}">{p["name"]}</a>'
        + (' <span class="live">live</span>' if p["file"] in LIVE
           else ' <span class="static">design</span>')
        + f'<div class="d">{p["description"][:150]}</div></li>'
        for p in pages
    )

    banner = (
        f'<p class="ok">API: <a href="{api}">{api}</a> — the audit screen on this page '
        f'reads from that deploy. If the sandbox has been torn down, run Ledgerline '
        f'locally and open the screens from <code>http://localhost:8000/ui/</code>.</p>'
        if api else
        '<p class="warn">No deploy recorded. Run <code>uv run python scripts/deploy.py</code>.</p>'
    )

    (SITE / "index.html").write_text(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ledgerline — governed cross-system sync</title>
<style>
:root{{--fg:#161616;--bg:#fff;--muted:#525252;--line:#e0e0e0;--blue:#0f62fe;
--okbg:#defbe6;--okfg:#198038;--warnbg:#fdf6dd;--warnfg:#b28600;--surface:#f4f4f4}}
@media(prefers-color-scheme:dark){{:root{{--fg:#f4f4f4;--bg:#161616;--muted:#c6c6c6;
--line:#393939;--blue:#78a9ff;--okbg:#044317;--okfg:#42be65;--warnbg:#3a2f00;
--warnfg:#f1c21b;--surface:#262626}}}}
*{{box-sizing:border-box}}
body{{font:16px/1.6 'IBM Plex Sans',system-ui,sans-serif;color:var(--fg);background:var(--bg);
margin:0;padding:3rem 1.25rem;}}
main{{max-width:52rem;margin:0 auto}}
h1{{font-size:1.9rem;margin:0 0 .4rem}}
.tag{{color:var(--muted);font-size:.9rem;margin-bottom:2rem}}
.lede{{font-size:1.1rem;border-left:4px solid var(--blue);padding-left:1rem;margin:2rem 0}}
.ok,.warn{{padding:.7rem 1rem;border-radius:4px;font-size:.9rem;word-break:break-all}}
.ok{{background:var(--okbg);color:var(--okfg)}}
.warn{{background:var(--warnbg);color:var(--warnfg)}}
a{{color:var(--blue)}}
ul{{list-style:none;padding:0}}
li{{padding:.75rem 0;border-bottom:1px solid var(--line)}}
li a{{font-weight:600;text-decoration:none}}
li a:hover{{text-decoration:underline}}
.d{{color:var(--muted);font-size:.85rem;margin-top:.15rem}}
.live,.static{{font-size:.7rem;padding:1px 7px;border-radius:99px;vertical-align:middle;
margin-left:.4rem}}
.live{{background:var(--okbg);color:var(--okfg)}}
.static{{background:var(--surface);color:var(--muted)}}
code{{background:var(--surface);padding:.1rem .35rem;border-radius:3px;font-size:.85em}}
table{{border-collapse:collapse;width:100%;font-size:.9rem;margin:1rem 0}}
td,th{{text-align:left;padding:.45rem .6rem;border-bottom:1px solid var(--line)}}
img{{max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:.5rem}}
</style></head>
<body><main>
<h1>Ledgerline</h1>
<p class="tag">SF Enterprise Hackathon · 2026-08-14 · Workflow Automation ·
built on <a href="https://softwareforge.ai/">SoftwareForge</a>, runs on
<a href="https://www.daytona.io/">Daytona</a> · <a href="{REPO_URL}">source</a></p>

<p class="lede">Enterprise data gets typed three times. Ledgerline types it once —
and no write happens until a human authorises it.</p>

{banner}

<h2>Screens</h2>
<ul>{rows}</ul>

<h2>The governance spine</h2>
<table>
<tr><th>Property</th><th>How it is enforced</th></tr>
<tr><td>No write without an authorised order</td>
<td>Downstream endpoints require a single-use token minted only at approval; a direct
write returns <code>403</code></td></tr>
<tr><td>Generated code never runs in-process</td>
<td>A Daytona sandbox is created per authorised order and destroyed after it; both
states are read back from Daytona and stored in the trail</td></tr>
<tr><td>Audit trail is append-only</td>
<td>SQLite triggers reject UPDATE and DELETE; a SHA-256 hash chain catches tampering
that bypasses them</td></tr>
</table>

<h2>Run it</h2>
<p><code>uv pip install -e '.[dev]'</code> · <code>bash scripts/restart.sh</code> ·
<code>uv run python scripts/e2e.py</code></p>

<h2>Audit trail, live</h2>
<img src="screenshots/audit-trail-desktop.png" alt="The audit trail screen tracing a
record back through its authorising order to the code that ran">
</main></body></html>
""")

    print(f"  _site/ built · {len(pages)} screens · api={api or '(none)'}")


if __name__ == "__main__":
    main()
