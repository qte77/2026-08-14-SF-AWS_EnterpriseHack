# Forge Intent — Ledgerline

Paste-ready input for SoftwareForge. Forge derives Intent → BRD → PRD → Architecture →
UI Design → User Stories → Testing from this. Written to be specific about **problem,
constraints and acceptance**, and deliberately quiet about implementation detail Forge should
choose.

Arc: [`plans/0001-governed-sync-agent.md`](plans/0001-governed-sync-agent.md) ·
Evidence: [`problem-shortlist.md`](problem-shortlist.md) §1

---

## Intent

Build **Ledgerline**, an internal workflow agent that eliminates duplicate manual data entry
across disconnected enterprise systems — and that no enterprise has to take on trust, because
**every write it performs is authorised by a human against a spec before it happens, and is
permanently traceable afterward.**

When a customer or order record changes in one system of record, Ledgerline detects the
change, derives the corresponding updates for every downstream system, and presents them to a
human as a discrete, reviewable **work order** stating exactly what will be written, where,
and why. Nothing is written until that order is authorised. Once authorised, the agent
executes the update inside an isolated, disposable sandbox — never against the host
application — and records the completed order in an audit trail that links the original
change, the derived intent, the approver, the executed code, and the resulting write.

The product thesis is that automation of this kind already exists and is not adopted, because
finance, operations and compliance teams cannot allow an autonomous process to write to
systems of record without an answer to "who approved this, and what exactly did it do?"
Ledgerline's answer is the work order.

---

## Problem

Enterprise records are entered by hand, repeatedly, into systems that do not talk to each
other. A single new customer or order is typed into the CRM by sales, re-typed into the ERP
by operations, then exported to a spreadsheet by finance. The same facts are keyed three
times.

This produces three costs, in increasing order of severity:

1. **Time.** Survey evidence (Parseur/QuestionPro, n=500 US professionals, 2025) puts manual
   transfer of data between emails, PDFs, spreadsheets and systems at **over nine hours per
   week per employee**, costing **~$28,500 per employee per year**. *Vendor-commissioned —
   treat as directional.*
2. **Errors.** Every re-key is an opportunity for divergence. Independent survey evidence
   (IFOL AP Automation Trends 2025) finds **66% of organisations still manually enter invoice
   data into ERP systems** and **63% of AP teams spend more than ten hours a week processing
   invoices**. *Vendor-sponsored — directional.*
3. **Loss of trust in the data.** Once systems disagree, teams stop believing any of them and
   revert to spreadsheets — which is how the manual work becomes permanent rather than
   transitional.

**Why the obvious fix has not been adopted.** Point-to-point integrations and RPA scripts
both write autonomously. Finance, compliance and operations owners will not grant an
autonomous process write access to a system of record without an audit answer, so the
integration is scoped down to read-only, or shelved, and the manual entry survives. The
blocker is governance, not capability.

---

## Users

| User | Need |
|---|---|
| **Operations coordinator** (primary) | Stop re-keying records that already exist elsewhere; see at a glance what is pending and what synced |
| **Finance / AP reviewer** (approver) | Understand exactly what will be written before it is written; approve or reject per change, not per system |
| **Compliance / audit** (observer) | Reconstruct after the fact who authorised any given write, on what basis, and what code executed |
| **IT owner** (gatekeeper) | Assurance that generated integration code never executes against the host application |

---

## Desired outcome

A record changed once, in one system, propagates to every other system **after a human
authorises a work order describing the change** — with a complete, queryable trail from the
originating edit to the final write.

Concretely, for the demo: a coordinator updates a customer record in the CRM. Ledgerline
detects it, derives the ERP and Accounting updates, and raises one work order per target. The
reviewer sees the before/after diff for each, approves one and rejects one. The approved
change appears in the target system within seconds; the rejected one does not, and the
rejection is recorded with its reason. The audit view traces the written record back through
the approval to the original CRM edit.

---

## Scope

### In scope

- Change detection on a source system (webhook or poll).
- Derivation of target-system updates from a shared record schema.
- **Work order**: a discrete, human-readable unit of proposed change — target system, field
  diff, derivation rationale, and the code that will run.
- Human authorisation: approve / reject / amend, per work order.
- Sandboxed execution of the authorised change, isolated from the host application.
- Immutable audit trail linking source change → work order → approver → executed code →
  resulting write.
- Three connected systems: CRM, ERP, Accounting.

### Out of scope

- Real SaaS tenancy or production credentials. The three systems are lightweight internal
  services sharing one record schema.
- Bidirectional conflict resolution. Propagation is one-directional from the source of truth
  for this iteration.
- Role-based access control beyond a single approver role.
- Historical backfill of records that predate the agent.
- Any write that has not been authorised — there is no "auto-approve" mode, by design. This
  is a product decision, not a missing feature.

---

## Constraints

- **Delivery window: one day.** Prefer the thinnest slice that demonstrates the full loop
  end-to-end over breadth of connectors. Three systems, one record type, is sufficient.
- **Execution isolation is mandatory.** Agent-derived integration code must execute in an
  isolated, disposable sandbox provisioned per authorised work order, and torn down after.
  It must never execute in the application process. This is a security property of the
  product, not a deployment detail.
- **Nothing writes without an authorised work order.** This constraint outranks throughput,
  latency and convenience. If a code path can write without one, that is a defect of the
  highest severity.
- **The audit trail is append-only.** Records are never edited or deleted, including on
  rejection.
- **Demonstrability.** Every governance property above must be *visible in the UI*, not
  merely true in the backend. A reviewer must be able to show an auditor the chain on screen.

---

## Success criteria

The build is complete when all of the following hold, each independently demonstrable:

1. A change in the source system produces a work order without human prompting.
2. The work order states the target system, the exact field-level diff, the rationale, and
   the code to be executed — legible to a non-engineer.
3. No write occurs in any target system until a human authorises the corresponding order.
4. An approved order results in the correct write, visible in the target system.
5. A rejected order results in no write, and the rejection with its reason is recorded.
6. Authorised code executes in an isolated sandbox that is created for the order and
   destroyed after it; this is observable, not asserted.
7. Any record in a target system can be traced back through its authorising order to the
   originating change.
8. The end-to-end flow runs with real triggers — no mocked steps in the demonstrated path.

---

## Non-goals

- Not a general iPaaS or connector marketplace. The governed work-order loop is the product;
  connectors are the example.
- Not an autonomous agent. Human authorisation is the feature, not a limitation to be removed
  in a later version.
- Not a data-quality or deduplication tool. It propagates what the source says.
- Not a replacement for any system of record.

---

## Naming note

"Ledgerline" is a working name — the line of provenance running through every record. Forge
may propose an alternative; the constraint is that the name should evoke traceability rather
than automation, because the audit trail is the differentiator and the automation is the
commodity.
