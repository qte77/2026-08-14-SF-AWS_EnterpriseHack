"""Extract the Forge UI mockups from UI_Design.md.

`UI_Design.md` is a JSON export, not prose: one object per screen carrying a
self-contained `html_preview`. This writes each one out so the design is a file
you can open, diff and serve.

  ui/forge/*.html   pristine, exactly as Forge generated them — never edited
  ui/*.html         the app's screens; these start as copies and get wired up

Re-running is safe: it only ever overwrites ui/forge/, so wiring is never lost.

    uv run python scripts/extract_ui.py
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/SoftwareForge.ai-EnterpriseHack-SF/2026-08-14-EnterpriseHack-SF/UI_Design.md"
UI = ROOT / "ui"
PRISTINE = UI / "forge"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> None:
    PRISTINE.mkdir(parents=True, exist_ok=True)
    spec = json.loads(SRC.read_text())

    index = []
    for page in spec["pages"]:
        name = slug(page["name"])
        (PRISTINE / f"{name}.html").write_text(page["html_preview"])
        (PRISTINE / f"{name}.hierarchy.txt").write_text(page.get("component_hierarchy", ""))
        live = UI / f"{name}.html"
        if not live.exists():
            shutil.copyfile(PRISTINE / f"{name}.html", live)
            status = "copied"
        elif live.read_text() == page["html_preview"]:
            status = "static mockup"
        else:
            status = "wired to the API"
        index.append({"name": page["name"], "file": live.name,
                      "description": page["description"], "status": status})
        print(f"  {live.name:34s} {len(page['html_preview']):>7d} B  {status}")

    (UI / "design-tokens.json").write_text(json.dumps(spec["design_tokens"], indent=2))
    (UI / "pages.json").write_text(json.dumps(index, indent=2))
    print(f"\n{len(index)} screens · pristine originals in {PRISTINE.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
