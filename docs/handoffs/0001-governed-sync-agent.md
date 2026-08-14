# Handoff 0001 — Governed cross-system sync agent

**Plan:** [`docs/plans/0001-governed-sync-agent.md`](../plans/0001-governed-sync-agent.md)
**Read that plan's §4 table first — it is the only list of open work.** This handoff tells
you how to pick it up; it deliberately does not duplicate the table.

> **The event is 2026-08-14 — today.** Same-day arc. Phase 0 access gates block everything.

---

## What shipped (this session — research and framing only, no build yet)

| Artifact | Contents |
|---|---|
| `docs/estate-correlation.md` | Ingest digest of all five inputs; PDF §4 mapped stage-by-stage against the estate; PDF §5 mapped criterion-by-criterion with weights; provenance caveats |
| `docs/problem-shortlist.md` | Five candidates ranked by ROI incl. the 30% platform-fit weight; evidence with URLs and source-type labels; a "what changed" table vs. a superseded draft |
| `docs/plans/0001-governed-sync-agent.md` | This arc: goal, source map, design, the 17-row remaining-work table, decide-by-default table, phases, watch-outs |
| `docs/handoffs/0001-governed-sync-agent.md` | This file |

**Nothing has been built.** No code, no Forge project, no Daytona sandbox. The arc is at
Phase 0.

---

## What's next, in order

1. **Clear Phase 0** — plan items 1–4. Owner-gated, blocking. Item 4 (does Forge actually
   expose Work Orders to users?) determines whether decision **D1** fires.
2. **Phase A** — plan items 5–14, in sequence. Item 5 first: the PDF is explicit that the
   Daytona environment must exist *before* you build in Forge, so the first generated build
   has somewhere to run.
3. **Phase B** — one owner sitting: confirm D1, approve spend, review the audit trail the way
   a judge would.
4. **Phase C** — plan items 15–17: deploy, demo, submit.

---

## The loop

For each item in the plan's table:

1. Read its **done-when** before starting. That is the acceptance test.
2. Build the thinnest slice that satisfies it.
3. Prove it **in the sandbox**, not locally — Daytona usage must be real and spread across
   the day, not clustered at the end.
4. Strike the row in the same change that ships it. A row still reading "open" after the work
   landed is a doc bug.
5. Under time pressure, apply **D5**: cut items 11 and 12 first; never cut 9, 10, or 13.

---

## Owner gates — what a human must do

| Gate | Why it can't be automated |
|---|---|
| Forge account + platform access | Registration at `hackathon.softwareforge.ai` |
| Daytona account + API key | Key issued from `app.daytona.io/dashboard/keys` |
| Team registration (≤4) | Event administration |
| Verify Work Orders in-product | Login-gated; drives D1 |
| Demo recording + submission | PDF §6 requires a human walkthrough |

---

## Commands

```bash
# Daytona — verified surface
pip install daytona                    # or: npm install @daytona/sdk
export DAYTONA_API_KEY=...             # from app.daytona.io/dashboard/keys
```

```python
from daytona import Daytona, DaytonaConfig
daytona = Daytona(DaytonaConfig(api_key="YOUR_API_KEY"))
sandbox = daytona.create()
print(sandbox.process.code_run('print("Hello World")').result)
```

Snapshots, filesystem, and git operations are on the same `sandbox` object. REST equivalents:
Platform API (lifecycle), Toolbox API (in-sandbox), Analytics API. OpenAPI specs published.

**Forge:** no CLI or API confirmed — see watch-outs.

---

## Watch-outs (the ones that will bite)

- **The estate is out of scope** (owner decision, 2026-08-14). Do not read, copy, import, or
  depend on `polyforge-orchestrator` or `qte77/qte77`. This project stands alone on
  Forge + Daytona; importing prior work into a sandbox is precisely the "one-off import"
  judges are told to look for. `docs/estate-correlation.md` is retained as analysis only.
- **Forge's primitives are marketing-sourced, not product-verified.** `app.softwareforge.ai/docs/introduction`
  is a JS SPA returning only the string `"Forge"` to any non-browser fetch; `/llms.txt` too.
  Living Specs, Work Orders and ForgeScore all come from `softwareforge.ai` plus press
  coverage. **Verify before depending on them.** D1 is the fallback.
- **No public Forge API found.** Searches surfaced only unrelated products (Atlassian Forge,
  getforge.com, SourceForge). Even if one exists, consuming Forge as a service undercuts the
  30% — Forge must be where development happens.
- **Reddit is inaccessible**, confirmed twice independently: fetches hard-blocked, zero
  indexed hits across 20+ queries. All evidence is HN, Capterra/G2/TrustRadius, and industry
  surveys. Tell judges "review-site and HN sourced" — do not imply forum breadth.
- **Two stats are safe to cite** (both re-fetched at source, both vendor-commissioned so
  present as directional): Parseur/QuestionPro — >9 hrs/week, $28,500/employee/yr; IFOL — 66%
  still hand-keying invoices, 63% of AP teams >10 hrs/week. **Opsera's own 66%/83%/"zero
  drift" figures are marketing — do not repeat them.**
- **Specific Bash commands are denied**, not Bash as a whole: `ls`, `find`, `cat`, `grep`,
  `head`, `tail`, `awk`, `curl`, `wget`, `source`, `touch`. Avoid pipes through them — a
  single `| head` fails the whole command. `git`, `make`, `jq`, `tree` and `uv` work.
- **An invalid `GH_TOKEN` env var shadows the valid stored gh credential**, so pushes fail
  with "Invalid username or token." Prefix git commands with
  `env -u GH_TOKEN -u GITHUB_TOKEN` until the bad var is fixed at source.
- **Repo:** `github.com/qte77/2026-08-14-SF-AWS_EnterpriseHack`, remote `origin`, branch
  `main`. Local path is `__2026-08-14-SF-AWS_EnterpriseHack` (underscore-prefixed); the empty
  non-underscore twin has been deleted.
- **`.venv/` exists** with the Daytona SDK installed (`daytona==0.204.0`), created via
  `uv venv`. There is no `pip` on PATH — use `uv`.

---

## Unresolved

| Question | Default being applied |
|---|---|
| Are Work Orders user-exposed in Forge? | D1 — build the governance layer in our own app if not |
| Does Forge expose an API? | Assume no; develop *on* Forge regardless |
| Is ForgeScore real and usable? | D4 — do not depend on it |
| Which systems to mock? | D2 — three lightweight in-repo services, no real SaaS credentials |
