# Ledgerline

**Enterprise data gets typed three times. Ledgerline types it once — and no write happens
until a human authorises it.**

Built for the **[SF Enterprise Hackathon](https://luma.com/ev9ndfke)**, 2026-08-14 ·
Track: **Workflow Automation**
Built on **[SoftwareForge](https://softwareforge.ai/)** · Runs on **[Daytona](https://www.daytona.io/)**

---

## Try it

| | |
|---|---|
| **Screens (permanent)** | <https://qte77.github.io/2026-08-14-SF-AWS_EnterpriseHack/> |
| **Live app on Daytona** | <https://8000-8cff584c-c83c-45cb-a1c8-8b8767705f72.daytonaproxy01.net> |
| **SoftwareForge spec** | artifact `90bd0b04-21ba-4674-86d3-f40a2e3a8a1e` — _`<!-- TODO: owner, paste the shareable Forge project URL -->`_ |
| **Demo video** | _`<!-- TODO: 2–3 min walkthrough, recorded from the Daytona environment -->`_ |
| **Team** | _`<!-- TODO: team name + members -->`_ |

The Pages link is permanent; the Daytona URL lives only as long as its sandbox
(`8cff584c-c83c-45cb-a1c8-8b8767705f72`, snapshot `ledgerline-b312e26-230625`). Redeploy with
`uv run python scripts/deploy.py` — Pages rebuilds against the new URL automatically.

> **Where the full loop runs.** The hosted instance serves the UI, the API and the
> audit trail, but it cannot *execute* work orders: Daytona rejects
> sandbox-to-sandbox toolbox traffic on this account tier — *"Network access is
> restricted and cannot be overridden at the sandbox level"*
> ([network limits](https://www.daytona.io/docs/en/network-limits/#tier-based-network-restrictions)).
> The nested sandbox is created; its `code_run` connection is then reset. Run
> Ledgerline **outside** a sandbox and the whole loop works — `scripts/e2e.py`
> passes 14/14 there against real Daytona sandboxes.

<!-- markdownlint-disable MD033 -->
<details>
<summary><b>Screenshots</b> — the audit trail tracing a written record back to the human who authorised it, the published screens, and the live deploy</summary>

### Audit trail — the governance property, on screen

Chain verified, and one record walked back: **record → authorising order → approver
→ timestamp → sandbox → the code that ran**. Every entry carries its own hash and
its predecessor's.

![Ledgerline audit trail: SHA-256 chain verified, a record traced back through its
authorising order to the sandbox and the code that executed](docs/screenshots/audit-trail-desktop.png)

### Same screen, mobile

![The audit trail at a 390px viewport](docs/screenshots/audit-trail-mobile.png)

### Published screens (GitHub Pages)

![The Ledgerline Pages site listing all eight Forge-designed screens](docs/screenshots/pages-landing.png)

### Pages talking to the live Daytona deploy

The published audit screen reading the API on a different origin — proof the
`?api=` wiring and CORS work end to end.

![The published audit trail rendering live entries fetched cross-origin from the
Daytona deploy](docs/screenshots/pages-audit-trail.png)

### The app served from Daytona

![The Ledgerline index served from the Daytona sandbox](docs/screenshots/daytona-hosted.png)

Screenshots are captured by [`scripts/ui_e2e.py`](scripts/ui_e2e.py) (local, in-repo)
and by [polyfetch-scrape](https://github.com/qte77/polyfetch-scrape) for the hosted
pages.

</details>
<!-- markdownlint-enable MD033 -->

---

## The problem

A single new customer or order is entered by sales into the CRM, re-typed by operations into
the ERP, then exported by finance into a spreadsheet. **The same facts, keyed three times.**

Three costs, in increasing severity:

1. **Time.** Over **nine hours per week per employee** transferring data by hand, ≈ **$28,500
   per employee per year**.
   <sub>Parseur × QuestionPro, Jul 2025, n=500 US professionals — *vendor-commissioned survey,
   verified at source. Directional, not precise.*</sub>
2. **Errors.** Every re-key is a chance for systems to diverge. **66%** of organisations still
   manually enter invoice data into ERP; **63%** of AP teams spend >10 hrs/week on it.
   <sub>IFOL AP Automation Trends 2025 — *vendor-sponsored industry survey, verified at source.*</sub>
3. **Loss of trust in the data.** Once systems disagree, teams stop believing any of them and
   fall back to spreadsheets. That is how the manual work becomes *permanent* rather than
   transitional.

### Why the obvious fix hasn't landed

Point-to-point integrations and RPA both **write autonomously**. Finance, compliance and
operations owners will not grant an autonomous process write access to a system of record
without an answer to *"who approved this, and what exactly did it do?"* So the integration
gets scoped down to read-only, or shelved — and the re-keying survives.

**The blocker is governance, not capability.** That is the gap Ledgerline is built for.

---

## How it works

Every propagation is a **work order**: a discrete, human-readable unit of proposed change —
target system, field-level diff, derivation rationale, and the exact code that will run.
Nothing is written until a human authorises it.

```mermaid
flowchart LR
    A[Record changes<br/>in CRM] --> B[Agent derives<br/>downstream updates]
    B --> C{Work order<br/>raised}
    C -->|human authorises| D[Sandbox created<br/>per order]
    C -->|rejected| E[No write<br/>reason recorded]
    D --> F[Code executes<br/>in isolation]
    F --> G[Write lands<br/>in ERP / Accounting]
    G --> H[(Append-only<br/>audit trail)]
    E --> H
    D -.->|torn down after| I[Sandbox destroyed]
```

**The invariant:** if a code path can write without an authorised order, that is a
top-severity defect — not a convenience trade-off.

---

## Built on Forge & Daytona

Both platforms are **structural**. Remove either and the product stops working as specified.

### Forge — where it's specified and built

- The requirement is authored as a **Living Specification** on-platform; its version history
  is the record of how the design evolved.
- Frontend and backend are generated and iterated **through Forge** — rapid generation, then
  refinement against enterprise constraints.
- Forge's **work-order model** is the same primitive the product exposes to its users, so the
  governance concept runs end-to-end: our spec is authorised the way our writes are.

### Daytona — where generated code is allowed to run

- **A sandbox is created per authorised work order**, executes the agent-generated
  integration code, and is **destroyed afterward**. Agent-written code never runs in the
  application process.
- **Parallel experimentation** — multiple sandboxes trying different sync strategies
  side-by-side; the losers are discarded at zero cleanup cost.
- **Snapshots** make the demo reproducible: what you see is the build that went green.

```python
def execute_authorized_order(order):
    """Only reachable after a human authorises the work order."""
    sandbox = daytona.create(...)
    try:
        return sandbox.process.code_run(order.generated_code)
    finally:
        sandbox.delete()
```

Isolation here is a **security property of the product**, not a deployment detail. That is
what makes Daytona load-bearing rather than a box we happened to run in.

---

## Impact

| | |
|---|---|
| **Baseline** | >9 hrs/week/employee on manual transfer · ≈$28,500/employee/yr |
| **Demonstrated** | **66% fewer re-keying events per record** — three manual entries collapse to one, shown live |
| **Projected** | ~80% at full connector coverage — *projection, not measured* |

Every figure above carries its source type. Vendor-commissioned surveys are labelled as such
rather than presented as neutral fact.

---

## Run it

```bash
uv venv && uv pip install -e .        # Python 3.12+
cp .env.example .env                  # add DAYTONA_API_KEY + DAYTONA_API_URL
bash scripts/restart.sh               # serves on http://127.0.0.1:8000
uv run python scripts/e2e.py          # the eight success criteria, executable
```

`/` lists the eight Forge-designed screens and the live API. The end-to-end run
creates a real Daytona sandbox per authorised work order and destroys it after.

| Endpoint | What |
|---|---|
| `POST /systems/crm/records/{id}` | Edit the source of truth — this is the trigger |
| `GET /api/v1/workorders` | Derived orders with field diffs, rationale, and the code to run |
| `POST /api/v1/workorders/{id}/approve` | Authorise, execute in a sandbox, write downstream |
| `POST /api/v1/workorders/{id}/reject` | Refuse, with a reason, recorded permanently |
| `GET /api/v1/audit` | Append-only trail with SHA-256 chain verification |
| `GET /api/v1/audit/trace/{system}/{id}` | A written record back to its authorising order |

`POST /systems/erp/records/{id}` without a token minted by an approval returns
**403**. That is the product's central invariant, enforced in the write path.

---

## Repo map

| Path | What |
|---|---|
| `docs/forge-intent.md` | The Intent given to Forge — problem, users, scope, constraints, acceptance |
| `docs/problem-shortlist.md` | Five enterprise pain points ranked by ROI, with sourced evidence |
| `docs/estate-correlation.md` | Ingest analysis: hackathon reference architecture and judging criteria |
| `docs/plans/0001-governed-sync-agent.md` | Build plan, remaining-work table, open decisions |
| `docs/handoffs/0001-governed-sync-agent.md` | Session handoff |
| `docs/SoftwareForge.ai-EnterpriseHack-SF/` | Forge pipeline output: Intent, BRD, PRD, Architecture, UI Design |
| `src/ledgerline/app.py` | The agent: detection, derivation, authorisation, sandboxed execution, audit |
| `ui/` | The eight Forge-designed screens, extracted from `UI_Design.md` |
| `scripts/e2e.py` | The eight success criteria as executable checks |
| `daytona_results/` | What was deployed, where, and from which commit |
| `assets/` | Problem statement |

---

## Scope, stated honestly

**In:** change detection · target derivation · work orders with field-level diffs ·
approve/reject/amend · sandboxed execution · append-only audit trail · three systems
(CRM, ERP, Accounting).

**Out:** real SaaS tenancy or production credentials (the three systems are lightweight
services sharing one record schema) · bidirectional conflict resolution · RBAC beyond a
single approver role · historical backfill.

**Deliberately absent:** there is **no auto-approve mode**. Human authorisation is the
feature, not a limitation to be removed later.

---

## Licence

See [LICENSE](LICENSE) if present; otherwise all rights reserved by the team pending
selection.
