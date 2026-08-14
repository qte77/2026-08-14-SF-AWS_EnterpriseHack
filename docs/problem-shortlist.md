# Problem Shortlist — ranked by hackathon ROI, correlated to the estate

Companion to [`estate-correlation.md`](estate-correlation.md). Source: enterprise-complaint
research, 2026-08-14 (consolidated 4-track report).

> **Revision note.** An earlier version of this file ranked on a *partial* brief that a
> research subagent sent directly, bypassing its parent. The consolidated report has since
> arrived and supersedes it. Several findings differ, two quantified stats were independently
> re-verified at source, and **the recommendation changed**. See
> [What changed](#what-changed-from-the-superseded-draft) at the end.

## Sourcing caveat — read before using any number

**Reddit was completely inaccessible.** `WebFetch` hard-blocks `reddit.com` and
`old.reddit.com`; `site:reddit.com` searches returned zero indexed hits across 20+ queries
spanning every subreddit targeted (r/sysadmin, r/ExperiencedDevs, r/ITManagers, r/accounting,
r/procurement, r/humanresources…). **No Reddit evidence exists below** — this is a gap, not a
deprioritisation. Substitutes: Hacker News (via hn.algolia.com, real permalinks),
G2/TrustRadius/Capterra **verified-buyer** reviews, and named industry surveys, labelled by
type throughout.

If the pitch leans on frequency claims, describe the sourcing to judges as
**"review-site and HN sourced"** rather than implying practitioner-forum breadth.

## ROI definition used here

The research ranked on evidence × impact × one-day buildability. That omits the **30%
"Built on Forge & Daytona"** weight, so this ranking re-scores with it:

> **ROI = evidence strength × enterprise impact (20%) × one-day buildability (40%) ×
> platform fit (30%)**

**Platform fit** = does the build *require* Forge's and Daytona's actual primitives, or
merely tolerate them? A candidate needing untrusted-code execution, isolation, or parallel
experimentation makes Daytona structural. A candidate whose governance *is* the product makes
Forge's Living Specs / Work Orders structural. Anything else risks the "one-off import" the
PDF explicitly warns judges to look for.

---

## Ranked, high → low ROI

### 1. Governed cross-system sync agent (CRM → ERP → Accounting)

**Pain.** *"Sales updates a CRM. Operations copies the same data into another system. Finance
exports everything to Excel"* — the same record typed three times, with loss of trust in the
data.

**Evidence — best triangulation in the corpus.** Three independent source types:
a practitioner blog ([dev.to](https://dev.to/mike_beentjes_253ae1fc918/stopping-double-data-entry-with-a-simple-api-integration-3157)),
HN ([Launch HN: Manaflow YC S24](https://news.ycombinator.com/item?id=41259754) — *"My
workflow lives in spreadsheets… you need to meet me where I do my work"*), and a
**source-verified survey**: [Parseur × QuestionPro, Jul 2025](https://www.prnewswire.com/news-releases/survey-manual-data-entry-costs-american-companies-more-than-28-000-per-employee-each-year-302516867.html),
n=500 US professionals — **>9 hrs/week** manually transferring data, **$28,500/employee/yr**.
*Vendor-commissioned; re-fetched and confirmed at source. Treat as directionally credible,
not precise.*

**Platform fit — the reason this is #1.** An agent that watches one system and propagates to
another executes generated integration code against live systems: that is the untrusted-code
case Daytona exists for, and the PDF names *Backend/Integration Testing Sandbox* and
*Agent/Automation Workflows* as its intended uses. The pain statement itself demands an
**audit trail** — which is Forge's Work Order primitive, not a feature we bolt on. Both
platforms are load-bearing.

**Estate correlation — the tightest available.** `polyforge`'s parallel-agent execution
re-derived as parallel sandboxes; its `--preset security-pr` (diff-scoped, **untrusted
inbound**) is the right posture for agent-generated integration code; qte77's eval-gate maps
onto "no propagation without its check passing."

**One-day buildability: Yes.** Watch a webhook/spreadsheet edit → propagate to a mock ERP
record → show the audit trail.

---

### 2. Governed internal-tool / admin-panel generator

**Pain (two halves).** *(a)* Teams hand-build the same admin panel repeatedly — one takes
*"a few days, if not weeks"* — and it rots. *(b)* Homegrown tools have **no governance
layer**, so teams either grant broad prod access or lock non-technical users out.

**Evidence.** [Show HN: Avo](https://news.ycombinator.com/item?id=31824877) (creator built
*"countless admin panels"* over 10 years); Retool verified-buyer reviews —
*"as applications grow, Retool apps can become harder to maintain"* (May 2026),
*"When the application is big it is very slow"* (Jul 2026)
([source](https://aws.amazon.com/marketplace/reviews/reviews-list/prodview-cqgbgmrm63i4y)).
Market signal: **5+ independently funded Show HN launches** (Dropbase 141 pts, Jet Admin
123 pts, UI Bakery, Dashi, Abra Actions) all pitched at the identical pain. Governance half
from the Onu thread: *"How do I check permissions?"*; *"compliance… features are required to
gain entry in companies who would pay a lot."*

**Platform fit — very strong, and the research flagged it too.** Generated tools **must
execute somewhere** → Daytona is structural, not decorative. And half (b) is a 1:1 match for
Forge's two headline primitives. No other candidate uses Forge's actual differentiators as
the product's own mechanism.

**Estate correlation.** Half (b) is **qte77's thesis restated by strangers** — agentic
capability without an enforcement gate. The eval-gate and the META/MECHANISM/STATE authority
split map directly onto "every internal action is spec-derived and Work-Order-authorised."

**Risk, stated plainly.** Building a tool-generator *on* a tool-generator reads as meta.
**Lead with governance, not generation**, or it looks like a demo of Forge rather than a
product.

**One-day buildability: Yes** for generation; **Partly** for governance (a permission-gated
"wrap this script as a governed action" slice is demoable; a full audit layer is not).

---

### 3. Invoice / AP extraction with PO matching

**Pain.** AP teams still hand-key invoice line items into the ERP and manually match POs.

**Evidence — the strongest *quantified* item in the corpus.**
[IFOL — AP Automation Trends 2025](https://acarp-edu.org/accounts-payable-automation-trends-2025/),
6th annual edition, **independently re-fetched and confirmed at source**: **66% still
manually entering invoice data into ERP**; **63% of AP teams spend >10 hrs/week processing
invoices.** *Sponsored by an AP-automation vendor with no disclosed methodology — directionally
right, not precise.*

**Why not higher.** Platform fit is the weak link. OCR/LLM extraction is a data pipeline; it
runs fine in a sandbox but doesn't *need* isolation, parallelism, or Work-Order authorisation.
That puts the 30% at risk of reading as incidental.

**Estate correlation.** Thin — this is pipeline work, not governance or parallel execution.

**One-day buildability: Yes** — extract fields → match against a mock PO list → flag
exceptions. A well-worn pattern, which is both its strength and its differentiation problem.

---

### 4. Procurement approval-routing tracker

**Pain.** *"Sending a tender document to suppliers takes anywhere between 5 hours to 5 days
depending on approval gateways, compared to 5 minutes via email."*

**Evidence.** [SAP Ariba Capterra reviews](https://www.capterra.com/p/227334/SAP-Ariba/reviews/),
verified buyers, **directly fetched**: the quote above (Jul 2021), plus *"clunky… completely
lacks the agility of modern SaaS tools"* (Mar 2026). Coupa is weaker secondary corroboration
(search-summarised, not re-fetched). **Single practitioner source for the headline number** —
do not present as an industry figure.

**Why not higher.** Best *single quotable number* of any candidate and very tightly scoped —
but minimal Daytona necessity (a routing tracker executes no untrusted code) and near-zero
estate correlation.

**One-day buildability: Yes** — show who is holding up a request, which is the literal
complaint.

---

### 5. COBOL / mainframe "explain this legacy code" tool

**Pain.** The people who understand mission-critical COBOL are retiring with no pipeline
behind them.

**Evidence.** [Hopper Show HN](https://news.ycombinator.com/item?id=48111143) (97 pts/51
comments), 4+ independent commenters converging unprompted: *"Majority of devs are over 60."*
The quotable one — a global bank with *"one mainframe developer past 70… paid upper-6-figures
to work 20 hrs/week"* — is a **secondhand anecdote relayed by a founder**. Use as colour,
label as anecdote. (The research self-corrected here, dropping a separate misattributed quote
rather than keeping it.)

**Platform fit.** Better than it looks: Forge markets a modernisation blueprint and
**ForgeScore** (8-dimension codebase health) at exactly this. **Unconfirmed** — that comes
from marketing copy, not the product; the app docs never loaded. Verify before betting on it.

**One-day buildability: Partly.** Must narrow hard to snippet → plain-English explanation +
dependency map. Scope creep is the main risk.

---

## Also documented, not shortlisted

| Item | Track | Why not |
|---|---|---|
| ServiceNow click-heavy ticket triage (1b) | Internal Tools | Quote came via a search snippet; the page 403'd on direct fetch — **not verified at source** |
| Alert fatigue / noisy on-call dashboards (1c) | Internal Tools | Big numbers (Catchpoint, Splunk n=1,855, Harness) but **all vendor-conducted and unverified at primary source**; proving real outage reduction isn't demoable |
| Legacy IE/ActiveX lock-in (2b) | Legacy Modernization | Single thread (17 pts); the real fix is VDI/PAM infra |
| SAP ECC UI complaints (2c) | Legacy Modernization | One aggregator page; real SAP integration impossible in a day |
| Cross-dept approval chains (3c) | Workflow Automation | **Vendor content marketing only** — no independent practitioner quote. Superseded by #4, which has verified reviews |
| Legal contract review (4a) | Departmental Productivity | See below — evidence improved, platform fit still weak |
| HR/payroll/benefits sync (4b) | Departmental Productivity | Namely Capterra, 3+ named reviewers but **one product, 2018–19**; corroboration attempts 403'd. Redundant with #1's stronger general case |
| Month-end close reconciliation (4c) | Departmental Productivity | Several named reviewers over 4 years, but single-vendor (BlackLine); partly buildable only |

**On legal contract review specifically** — the earlier draft demoted it because every source
was a vendor blog. **That rationale no longer holds**: the consolidated report supplies
verified-buyer Capterra quotes (*"Practically impossible to find old documents and
contracts"*, Dec 2025) and a genuinely interesting HN thread where
[AI redlining favoured the counterparty](https://news.ycombinator.com/item?id=36422807) and
*increased* billable hours. Two objections survive and keep it off the list: it needs no
untrusted execution (weak 30%), and it is among the most-attempted hackathon patterns. The
commonly cited *"3.1 hours per contract review"* traces only to a vendor blog — **do not
cite it.**

---

## Recommendation

**#1 (governed cross-system sync agent), with #2's governance framing as the pitch.**

The two top items converge on the same architecture, which is why they rank above better-
quantified candidates: *an automation agent whose every action is spec-derived and
Work-Order-authorised, executing its generated integration code in a disposable Daytona
sandbox.* Each criterion is carried by a different strength:

- **40% Working Prototype** — the sync demo is concrete and live: edit a record, watch it
  propagate, see the audit trail.
- **30% Forge & Daytona** — Forge Living Specs + Work Orders *are* the audit mechanism the
  pain demands; Daytona is the mandatory runtime for agent-generated integration code, plus
  parallel experimentation. Neither is decorative.
- **20% Impact** — the verified Parseur figures (>9 hrs/week, $28,500/employee/yr), with the
  IFOL AP numbers from #3 as corroborating support for the same underlying manual-entry cost.
- **10% Presentation** — "we made the agent auditable" answers the first objection any
  enterprise buyer raises.

This also re-uses the most estate leverage — `polyforge`'s parallel-agent execution and
untrusted-code posture, plus qte77's eval-gate-before-work — **re-implemented on-platform**,
which is what the 30% requires.

**Before committing, verify two things** (both currently rest on marketing copy, not the
product, because the app docs never loaded):
1. Forge's **Work Order** primitive is actually exposed to users in the hackathon build — the
   governance half depends on it.
2. Whether Forge exposes an API at all. No public API documentation was found; searches
   returned only unrelated products (Atlassian Forge, getforge.com, SourceForge).

---

## What changed from the superseded draft

| | Superseded draft | This version |
|---|---|---|
| **#1** | LLM browser-agent replacing brittle RPA (Skyvern, 422 pts/139 comments) | Governed cross-system sync agent |
| **Why** | Skyvern **does not appear in the consolidated report at all** — it came only from the bypassing subagent. The evidence is real and checkable, but it is now single-sourced from a superseded brief, so it is not safe to build the pitch on | The consolidated Track 3 supplies **source-verified** quantified evidence the draft lacked |
| **New** | — | Procurement approval tracker (#4), ServiceNow triage, alert fatigue, HR sync, month-end close |
| **Legal** | Demoted to #5: "every source is a vendor blog" | That reason was **wrong under the fuller evidence** — verified Capterra quotes + an HN thread exist. Off-list now for platform-fit and crowding reasons only |
| **HR** | #3, on an ADP case study (Craig Perry, ~15 min/hire) | Replaced by Namely verified-buyer reviews; drops off-list as redundant with #1 |
| **Stats** | Mostly secondhand | Two figures **independently re-fetched and confirmed at source** (Parseur, IFOL) |
