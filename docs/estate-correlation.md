# Estate Correlation — SF Enterprise Hackathon (2026-08-14)

Correlates the existing estate (`polyforge-orchestrator`, `qte77/qte77`) against the
hackathon's **§4 Reference Architecture** and **§5 Judging Criteria**.

**Source of truth for §4 and §5:** `assets/2026-08-14 SF Enterprise Hackathon Problem
Statement.pdf` (4 pages). Everything quoted in those two sections below is from that PDF.

---

## 0. Ingest digest

### 0a. Problem statement (PDF — authoritative)

One-day build sprint, San Francisco, 2026-08-14. Teams of up to 4. Mandated platforms:
**SoftwareForge.ai (Forge)** for development + **Daytona** for the environment/execution
layer. Pick a real enterprise problem; go from idea to a working, deployed prototype in a
single day. Four suggested tracks: Internal Tools & Dashboards · Legacy Modernization ·
Workflow Automation · Departmental Productivity.

The PDF's own framing of Forge usage is the one that binds us: **Rapid Generation**
(scaffold components, APIs, business logic), **Iterative Refinement** (prompt, tweak,
iterate to fit complex enterprise requirements), **Full-Stack Execution** (both frontend
interface and backend service logic running through the platform).

Explicit judging note from the PDF: teams are expected to build their entire submission
using Forge for development **and** Daytona for running/testing/deploying it — *"not just
prototype an idea or write documentation. Judges will specifically look for real,
meaningful usage of **both** platforms throughout the build."*

### 0b. Forge (SoftwareForge.ai)

Positions as an **intent- and context-aware enterprise Software Factory** — "governed from
spec to production." Core primitives:

- **Living Specifications** — persistent, versioned, machine-readable specs (PRDs, BRDs,
  architecture docs, work orders) acting as the permanent system of record, so work resumes
  without losing intent or compliance context.
- **Work Orders** — discretised, human-auditable authorisations for agentic action; the
  audit trail from initial prompt through deployment.
- **Persistent context layer** — carries security, policy and rules; agents inherit intent
  and compliance rather than starting from a blank slate.
- **ForgeScore** — an 8-dimension codebase health assessment, aimed at the legacy-
  modernisation path.
- Integrates alongside Jira, GitHub, Slack and CI rather than replacing them.

> **Provenance caveat.** `app.softwareforge.ai/docs/introduction` (ingest item 2) is a
> JavaScript SPA and returns only the string "Forge" to any non-browser fetch; `/llms.txt`
> likewise. The description above is therefore assembled from `softwareforge.ai` plus press
> coverage of the Opsera Forge launch — **the softwareforge.ai = Opsera Forge identification
> rests on the domain and product-name match**, not on a first-party statement we retrieved.
> Vendor performance figures (66% rework eliminated, 83% faster delivery, "zero architectural
> drift") are **marketing claims, unverified** — do not repeat them to judges as fact.
> Confirm all of this against the logged-in product on the day; the PDF's Rapid Generation /
> Iterative Refinement / Full-Stack Execution framing is what we build to until then.

### 0c. Daytona

Secure, elastic infrastructure for running code — including AI-generated code — in
isolated, disposable sandboxes. Claimed sub-90ms creation; sandboxes run indefinitely;
**environment snapshots** for save/restore/resume; multi-region. Surface we care about:
**Process Execution API** (run commands with real-time output streaming), **File System
operations**, **Git integration**, **LSP support**, SSH / VS Code Browser / Web Terminal
access, Docker-native image building, and SDKs for Python, TypeScript, Ruby, Go and Java.

The PDF's suggested Daytona uses map almost one-to-one onto what our estate already does
locally: instant standardised environments, safe execution of AI-generated code, **parallel
experimentation** (multiple sandboxes side-by-side), reproducible demos via snapshot,
integration-testing sandboxes, and sandboxes as the secure runtime for an agent that writes
and executes its own code.

---

## 1. The correlation, stated honestly

Our estate and the mandated platforms are **the same idea at two different layers**:

| Estate concept | Forge/Daytona counterpart | Reading |
|---|---|---|
| `qte77` goals.json OKRs — each KR a **pre-committed eval** | Forge **Living Specification** | Both capture intent as a durable, machine-readable record *before* code exists |
| `qte77` **eval-gate** (enforces) + `goal_id` links (traces) | Forge **Work Order** authorisation | Both make unapproved/unproven work structurally unable to ship |
| `qte77` `STATUS.md` rollup — achievement traces up as % | Forge "unbroken project history from prompt to deployment" | Both close the loop from intent to evidence |
| `polyforge` `cc-parallel.sh` — fan agents across repos | Daytona **parallel sandboxes** | Both are "run N isolated attempts at once, discard the losers" |
| `polyforge` `--preset validate` / `security-all` / `security-pr` | Daytona **Process Execution API** as the gate runner | Our gates need a clean, reproducible box to run in — that is exactly Daytona |
| `polyforge` devcontainer-lifecycle replay (sibling `devcontainer.json` hooks) | Daytona **snapshots** + Docker-native images | Both solve "everyone gets the identical, pre-configured environment" |

**The consequence — and this is the load-bearing point of this document.** Judges score
*"real, meaningful usage of both platforms — not a one-off import."* The estate is therefore
**leverage, not the submission**. Every row above is a design we already know works and can
re-derive fast; none of them can be *pointed at* to earn credit. Each one must be
**re-implemented inside Forge + Daytona on the day**. Importing `polyforge` into a sandbox
and calling that "Daytona usage" is precisely the one-off import the PDF warns against.

**One honest gap to note:** `qte77/goals.json` is empty and `STATUS.md` reads *"No goals
defined yet … the rails (eval-gate, this rollup) are dormant-but-ready."* The governed loop
is designed and railed but has never been run against live goals. That is not a weakness for
this event — it means the hackathon build can be the loop's first real instantiation, and we
carry the design, not stale state.

---

## 2. §4 Reference Architecture — mapping

The PDF's Data Flow, verbatim: *"Describe system requirements to Forge → Iterate frontend
and backend code on-platform → Spin up a Daytona sandbox to run and test the generated build
→ Connect enterprise integrations and validate them inside the sandbox → Deploy the
functional end-to-end prototype to users, using the Daytona environment as the reproducible
base for the live demo."*

| # | Stage (PDF) | What the estate already gives us | What must be net-new on Forge/Daytona |
|---|---|---|---|
| 1 | **Describe system requirements to Forge** | `qte77` operating model: intent as OKR + **pre-committed eval per KR** — we know how to write a spec whose acceptance test is fixed up front. `AGENTS.md`/`CLAUDE.md` house-rules style. | Author the requirement as a **Living Specification inside Forge**, with acceptance criteria as first-class spec content. Do not draft in markdown and paste — the spec must live on-platform, because its version history *is* the evidence for the 30% criterion. |
| 2 | **Iterate frontend and backend code on-platform** | Prompt→iterate→gate discipline; `AGENT_LEARNINGS.md` compound-learning loop; strict-lint/typing/security defaults. | Full-stack generation **through Forge's engines** (PDF: Rapid Generation, Iterative Refinement, Full-Stack Execution). Refinement rounds must be visible on-platform, ideally as **Work Orders**, so iteration is auditable rather than invisible. |
| 3 | **Spin up a Daytona sandbox to run and test the generated build** | `polyforge` `scripts/cc-parallel.sh --preset validate`; the devcontainer-lifecycle replay pattern; "run the exact CI gate locally before pushing." | Recreate the **validate preset as a Daytona sandbox run** via the Process Execution API — same gate, executed in the disposable box instead of the devcontainer. Take a **snapshot** the moment the build first goes green: that snapshot becomes the demo base (stage 5). |
| 4 | **Connect enterprise integrations and validate them inside the sandbox** | `--preset security-all` (repo-wide) and `security-pr` (diff-scoped, untrusted inbound); the security-audit skills (OWASP, secrets, dependency scanning). | Stand up the integration surface (APIs, webhooks, data connectors) **inside the sandbox** and validate there — the PDF's stated reason is to avoid risking a shared/production-like environment. Run the security sweep in-sandbox so untrusted AI-generated integration code never touches a host. |
| 5 | **Deploy the E2E prototype; Daytona env = reproducible demo base** | Unattended-execution rules: ship-a-phase, live-prove with real triggers not mocks; UI e2e discipline (viewport/device variation, click real controls, capture console errors, fail on app console errors). | Deploy from the sandbox and **demo from the snapshot**, so what judges see is provably what we built (PDF: "no last-minute 'it worked earlier' surprises"). Submission needs a **hosted URL** built on Forge and verified in a Daytona sandbox. |

**Parallelism is the estate's sharpest transferable move.** `polyforge` exists to fan agents
across a polyrepo; the PDF explicitly invites **Parallel Experimentation** — multiple
sandboxes trying different architectural approaches side-by-side, discarding the failures at
zero cleanup cost. On a one-day clock that is the highest-leverage pattern we own, and it
demonstrates non-trivial Daytona usage rather than "we ran it in a box."

---

## 3. §5 Judging Criteria — mapping

Weights and focus text are quoted from the PDF.

| Category | Weight | Focus (PDF) | What the estate contributes | Evidence judges actually see |
|---|---|---|---|---|
| **Working Prototype** | **40%** | "Does the application run end-to-end and actually solve the target problem?" | Ship-a-phase discipline: TDD slice → full gates → deploy → **live-prove with real triggers, never mocks**. The rule "rendering/wiring = e2e is the test" keeps a one-day build honest without over-testing. | A hosted URL that works live, driven end-to-end in front of judges from the Daytona snapshot. Real data path, no mocked happy path. |
| **Built on Forge & Daytona** | **30%** | "Real, substantial use of Forge for development and Daytona for running/testing throughout the build — not a one-off import." | Nothing, by itself — **this is the criterion the estate cannot buy**. It must be earned on-platform on the day. | Living Spec version history; a **Work Order trail** from prompt to deploy; multiple sandboxes (parallel experiments, integration testing, demo base); gate runs executed via Daytona, timestamped **throughout** the day rather than clustered at the end. |
| **Impact** | **20%** | "How much friction, time, or cost this would realistically save in an enterprise setting." | The estate's own thesis — governance so an agentic estate "compounds instead of forgetting" — is a credible enterprise pain narrative. `cto-handbook-mapping.md` ties the dev-loop to an external engineering-leadership reference. | A specific, **sourced** pain point (practitioner complaints, not vendor stats) with an honest before/after: hours or handoffs removed. Cite the source; mark any number as practitioner-reported vs. analyst vs. vendor. |
| **Presentation** | **10%** | "Clarity of the live demo and how well the problem and solution are communicated." | House doc-structure conventions; the `Why/What/How` README shape; existing SVG architecture diagrams as a visual-explanation pattern. | A 2–3 minute walkthrough run **from the Daytona environment**, opening with the problem and its evidence, not the tech. |

**Where the weights should push our effort.** 40 + 30 = 70% of the score is "it genuinely
runs" and "you genuinely used both platforms." Both are execution, not design — and both are
verifiable, so neither can be recovered by a good story at the end. Impact (20%) is the one
category where preparation *before* the day pays: the problem must be real and sourced.
Presentation (10%) is last, and the estate's diagramming habits mostly cover it.

**Submission checklist (PDF §6):** working prototype link (hosted, built on Forge, verified
in a Daytona sandbox) · live demo or 2–3 min video from the Daytona environment · team
details · problem overview with enterprise value.

**Setup, before the day (PDF §7):** Forge account via `https://hackathon.softwareforge.ai/`
· Daytona account with a sandbox provably spinning up · team formed (≤4) · target pain points
brainstormed · **Daytona environment stood up before building in Forge, so the first
generated build has somewhere to run.**

---

## 4. Suggested angle (suggestion only — not a plan)

The estate's native subject matter — governed, traceable, parallel agent execution — maps
most naturally onto the **Workflow Automation** track, and the PDF names that track as a
natural fit for agent/automation workflows using Daytona as the agent's secure runtime.
Concretely: an internal-workflow agent whose every action is spec-derived and audit-trailed
(Forge Living Spec + Work Orders) and which executes its own generated code in a disposable
Daytona sandbox. That reuses the qte77 governance thesis and the polyforge parallel-execution
pattern while re-implementing both on-platform, which is what the 30% criterion demands.

Problem selection should wait on the sourced enterprise-complaint research, so Impact (20%)
rests on evidence rather than on our own intuition.

---

## Sources

- `assets/2026-08-14 SF Enterprise Hackathon Problem Statement.pdf` — §4, §5, §6, §7
- [softwareforge.ai](https://softwareforge.ai/) — Forge positioning, Living Specs, Work Orders, ForgeScore
- [Opsera newsroom — Forge launch](https://opsera.ai/newsroom/opsera-launches-forge-the-first-intent-and-context-aware-enterprise-software-factory/) · [SD Times coverage](https://sdtimes.com/softwaredev/opsera-launches-forge-the-first-intent-and-context-aware-enterprise-software-factory/)
- [daytona.io](https://www.daytona.io/) — sandbox model, snapshots, Process Execution API, SDKs
- `polyforge-orchestrator/README.md` — presets, parallel execution, devcontainer lifecycle bridging
- `qte77/qte77/README.md`, `docs/architecture.md`, `STATUS.md` — governed loop, authority chain, dormant-rails status
- **Not retrieved:** `app.softwareforge.ai/docs/introduction` (SPA, requires login) — see provenance caveat in §0b
