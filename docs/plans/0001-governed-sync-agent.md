# Plan 0001 — Governed cross-system sync agent (SF Enterprise Hackathon)

**Arc:** 0001 · **Handoff:** [`docs/handoffs/0001-governed-sync-agent.md`](../handoffs/0001-governed-sync-agent.md)
**Event:** 2026-08-14, San Francisco · one-day build sprint · teams ≤4
**Mandated stack:** SoftwareForge.ai (Forge) for development · Daytona for run/test/deploy

### Logistics — from the [Luma listing](https://luma.com/ev9ndfke)

| | |
|---|---|
| **Hours** | **09:30 – 19:00** (PT inferred; the listing does not state a timezone) |
| **Venue** | San Francisco — exact address released to registered guests only |
| **Registration** | **Approval required** — "Request to Join"; ~300 registered |
| **Hosts** | Devnovate (presenter) · AWS Builder Loft · RocketRide · Aviral · Javier Garza · Mansi More |
| **Submission** | **RocketRide Discord `#showcase` channel, with GitHub links** |
| **Judging** | "Live project demos to judges and industry experts" — no per-slot times published |
| **Prizes** | "Exciting prizes and sponsor awards" — unspecified |
| **Support** | RocketRide Discord (credits + support) |

> **No explicit submission deadline is published.** The hard stop is the 19:00 event end, and
> live demos happen before it — so treat late afternoon as the real cut-off and confirm the
> exact time at the mentor table. This drives **D5** (what gets cut).
>
> **The GitHub repo is the submission artifact.** Submission is by GitHub link, so repo
> hygiene — README, working prototype URL, problem overview — is scored surface, not
> housekeeping.

> **The event is TODAY.** This is a same-day arc, not a multi-session one. The usual
> "front-load Phase A, batch owner gates later" shape is **inverted**: the access gates in
> Phase 0 block everything and must clear first. Treat elapsed hours as the scarce resource.

---

## 1. Goal

Ship a working, deployed prototype of **an automation agent whose every action is
spec-derived and Work-Order-authorised, executing its generated integration code in a
disposable Daytona sandbox** — solving duplicate cross-system data re-entry
(CRM → ERP → Accounting).

**Why this problem:** ranked #1 in [`../problem-shortlist.md`](../problem-shortlist.md).
Best evidence triangulation in the corpus, and the only top candidate where *both* mandated
platforms are structurally required rather than decorative.

**Track:** Workflow Automation (PDF §3).

---

## 2. Source map

Read these instead of re-deriving context.

### Local — this repo

| Path | What it holds |
|---|---|
| `assets/2026-08-14 SF Enterprise Hackathon Problem Statement.pdf` | 4pp. §4 Reference Architecture (p3) · §5 Judging Criteria (p3) · §6 Submission (p3–4) · §7 Setup checklist (p4) |
| `docs/estate-correlation.md` | Ingest digest; §4 stage-by-stage mapping; §5 criteria mapping; Forge/Daytona provenance caveats |
| `docs/problem-shortlist.md` | Ranked candidates, evidence with URLs, source-type labels, what changed from the superseded draft |

### Local — estate

**Not used.** `polyforge-orchestrator` and `qte77/qte77` are **out of scope for this build**
(owner decision, 2026-08-14). Do not read, copy, import, or depend on them. This project
stands alone on Forge + Daytona.

`docs/estate-correlation.md` remains as the record of the ingest analysis that was
requested at the outset; it is **analysis, not a build input**.

### External

| Ref | Use |
|---|---|
| `https://hackathon.softwareforge.ai/` | Forge access for the event (PDF §7) |
| `https://softwareforge.ai/` | Living Specifications, Work Orders, ForgeScore — **marketing copy, unconfirmed in-product** |
| `https://www.daytona.io/docs/` | SDKs, REST API, auth, snapshots — **verified** |
| `https://app.daytona.io/dashboard/keys` | API key issuance |

### Daytona API surface — verified 2026-08-14

```python
from daytona import Daytona, DaytonaConfig
config = DaytonaConfig(api_key="YOUR_API_KEY")
daytona = Daytona(config)
sandbox = daytona.create()
response = sandbox.process.code_run('print("Hello World")')
```

- **SDKs:** Python (`pip install daytona`) · TypeScript (`npm install @daytona/sdk`) ·
  Ruby · Go · Java
- **REST:** Platform API (sandbox lifecycle) · Toolbox API (in-sandbox ops) · Analytics API.
  OpenAPI specs published.
- **Auth:** API key, issued from the dashboard.
- **Ops:** create/delete sandbox · `code_run()` · filesystem · git · **snapshots**.
- **CLI:** `daytona`.

---

## 3. Design

### Data flow — maps 1:1 onto PDF §4

1. **Spec** — author the requirement as a **Living Specification in Forge**, acceptance
   criteria as first-class spec content. Version history *is* the 30% evidence.
2. **Build** — generate frontend + backend **through Forge** (Rapid Generation → Iterative
   Refinement → Full-Stack Execution). Refinement rounds visible on-platform.
3. **Run/test** — Daytona sandbox via Process Execution API. Snapshot the moment it first
   goes green; that snapshot becomes the demo base.
4. **Integrate** — connect the mock CRM/ERP/Accounting surfaces and validate **inside** the
   sandbox. Agent-generated integration code never touches a host.
5. **Deploy/demo** — hosted URL; demo from the snapshot.

### Forge ↔ repo ↔ Daytona wiring

**Forge is connected to `github.com/qte77/2026-08-14-SF-AWS_EnterpriseHack`** (owner,
2026-08-14). That closes the build-time seam: Forge generates → pushes to this repo →
a Daytona sandbox clones it and runs the gates. No Forge API is needed for this.

The *runtime* seam is separate and is where the 30% is earned: the Forge-built app itself
imports the Daytona SDK and creates a sandbox **per authorised work order**, executing the
generated integration code there and tearing it down after.

> **Two writers on `main` from now on** — Forge and this session. Always `fetch` + rebase
> before committing locally. Prefer having Forge push to its own branch so generated code and
> the docs/plan do not tangle; merge deliberately.

### The governance spine (the differentiator)

Every propagation the agent proposes is a **Work Order**: derived from the spec, shown to a
human, authorised, then executed in the sandbox, then recorded. This is qte77's
eval-gate-before-work re-implemented on Forge primitives — *not* pointed at.

### Platform-native patterns (built here, from nothing)

- **Parallel experimentation** — multiple Daytona sandboxes trying different sync strategies
  side-by-side, discarding the losers at zero cleanup cost (PDF §2b).
- **Untrusted-inbound posture** — agent-generated integration code is treated as untrusted:
  it executes only in a sandbox created for its authorised order, never in-process.
- **Gate-before-write** — no propagation occurs until its work order is authorised.

---

## 4. Remaining work

**This is the single source of truth for what is open.** Sections above describe HOW; they
never re-list WHAT. Gate: `agent` (unattended) · `owner` (human) · `data` (needs an input).

| # | Item | Gate | Done when |
|---|---|---|---|
| ~~1~~ | ~~Forge account created, platform access confirmed via `hackathon.softwareforge.ai`~~ — **DONE 2026-08-14** | owner | ~~Logged in; can create a project~~ |
| ~~2~~ | ~~Daytona account + API key; prove a sandbox spins up~~ — **DONE 2026-08-14** (key in `.env`; sandbox created, ran code, deleted) | owner | ~~`daytona.create()` returns a live sandbox from a scratch script~~ |
| 3 | Team registered (≤4) and name recorded | owner | Submission fields answerable |
| 4 | **Verify Work Orders are user-exposed in Forge**; verify whether a Forge API exists | owner | Confirmed in-product, or Decision D1 default applied |
| 5 | Stand up the Daytona environment **before** building in Forge (PDF §7) | agent | Sandbox running with the runtime the build needs |
| 6 | Author the Living Specification in Forge (problem, acceptance criteria) | agent | Spec exists on-platform with version history |
| 7 | Build mock CRM / ERP / Accounting surfaces (3 systems, minimal schema) | agent | Each accepts a record and exposes read + webhook |
| 8 | Sync agent: watch source → propose propagation → execute in sandbox | agent | Edit in system A appears in B and C |
| 9 | Work-Order layer: every propagation authorised + recorded before execution | agent | No write occurs without an authorised, logged order |
| 10 | Audit-trail UI: unbroken history from prompt to write | agent | A judge can trace any record back to its authorising order |
| 11 | Parallel-experimentation demo: ≥2 sandboxes, differing strategies | agent | Both run; the discarded one is shown as discarded |
| 12 | Security sweep of agent-generated integration code, in-sandbox | agent | Runs clean inside the sandbox, never on a host |
| 13 | E2E run: real triggers, no mocks in the happy path | agent | Full flow passes end-to-end; app console errors fail the run |
| 14 | Snapshot the green build; use as the demo base | agent | Snapshot restores to a working app |
| 15 | Deploy; capture the hosted URL | agent | URL loads for someone outside the sandbox |
| 16 | Demo: live walkthrough or 2–3 min video **from the Daytona environment** | owner | Recorded/rehearsed, opens with the problem |
| 17 | Submission: post to **RocketRide Discord `#showcase`** with the GitHub link; include URL · demo · team details · problem overview | owner | Posted before the 19:00 stop; all four PDF §6 fields present |
| 18 | Repo README carries the pitch: problem, prototype URL, demo link, team — the GitHub link *is* the submission | agent | A judge opening the repo cold understands the problem and can reach the live app |
| 19 | Confirm exact submission cut-off + demo slot at the mentor table | owner | Time known and D5 applied against it |
| 20 | Join RocketRide Discord (credits + support + `#showcase`) | owner | Able to post in `#showcase` |

---

## 5. Open decisions — decide-by-default

Proceed on the default unattended; the owner overrides at the Phase B checkpoint.

| ID | Decision | Default | Trigger to revisit |
|---|---|---|---|
| D1 | Work Orders turn out not to be user-exposed | Implement the governance layer **in our own app** and present it as the spec-derived audit trail; keep the Living Spec in Forge regardless | Item 4 comes back negative |
| D2 | Which three systems to mock | Lightweight in-repo services (CRM, ERP, Accounting) with a shared record schema — no real SaaS credentials | Owner has real sandbox tenancy for a genuine SaaS |
| D3 | SDK language | **Python** — shortest Daytona example, fastest to demo | Forge generates a TS/JS stack more naturally; then TypeScript |
| D4 | ForgeScore usage | Do not depend on it — unconfirmed in-product | Confirmed working and time remains |
| D5 | Scope pressure late in the day | Cut items 11 and 12 first; **never** cut 9, 10, 13 (they carry the 30% and 40%) | Behind schedule at the Phase C boundary |

---

## 6. Phases

- **Phase 0 — owner access (blocking, do first):** items 1–4. Nothing else can start.
- **Phase A — agent build (the bulk):** items 5–14, in order. Unattended.
- **Phase B — owner checkpoint (one sitting):** confirm D1 outcome, approve any spend,
  review the audit trail as a judge would.
- **Phase C — activation:** items 15–17. Deploy, demo, submit.

---

## 7. Watch-outs

- **Build it on-platform, from nothing.** The estate is out of scope; importing prior work
  into a sandbox is exactly the "one-off import" the PDF warns judges to look for. Every
  pattern above is built here, on Forge + Daytona.
- **Timestamps matter.** Judges look for both platforms used *throughout* the build, not
  clustered at the end. Commit spec revisions and sandbox runs as you go.
- **Forge's Living Specs / Work Orders / ForgeScore are marketing-sourced.** The app docs
  (`app.softwareforge.ai/docs/introduction`) are a JS SPA that returns only the string
  `"Forge"` to any non-browser fetch. Verify in-product before depending on them.
- **No public Forge API was found.** Searches returned only unrelated products (Atlassian
  Forge, getforge.com, SourceForge). Even if one exists, calling it undercuts the 30% —
  Forge must be where you *develop*, not a service you consume.
- **Do not repeat vendor stats as fact.** Opsera's 66% / 83% / "zero architectural drift" are
  marketing. The defensible numbers are the two re-verified at source: Parseur (>9 hrs/week,
  $28,500/employee/yr) and IFOL (66% hand-keying, 63% >10 hrs/week) — both
  vendor-commissioned, so present them as directional.
- **Reddit evidence does not exist.** Hard-blocked; zero indexed hits across 20+ queries.
  Describe sourcing to judges as "review-site and HN sourced."
- **Bash is denied in this session** — four refusals including read-only `find`. Any shell
  work needs the owner to run it or to unblock the tool.
