## Executive Summary

Ledgerline is an internal workflow agent that will eliminate duplicate manual data entry across disconnected enterprise systems — CRM, ERP, and Accounting — by automatically detecting changes in a designated source-of-truth system, deriving the corresponding updates for each downstream system, and presenting every proposed write to a human reviewer as a structured, field-level work order. No data will ever be written to any connected system without explicit human authorisation, and every action — approved, rejected, or amended — will be permanently recorded in an immutable, append-only audit trail.

The product serves four primary stakeholders: **Operations coordinators** who will stop manually re-keying records across systems and gain a single dashboard view of propagation health; **Finance / AP reviewers** who will see exactly what will be written before authorising each change; **Compliance / audit observers** who will reconstruct the complete authorisation chain for any write after the fact; and **IT owners** who will receive assurance that all agent-derived integration logic executes exclusively in isolated, disposable sandboxes — never within the host application.

Ledgerline targets an **80% reduction in duplicate manual re-keying volume**, a **90% reduction in downstream data-entry errors**, and a **70% reduction in time-to-reconcile mismatched records** within the first quarter of use, while maintaining full SOC 2 and GDPR compliance from day one. The initial delivery will demonstrate the thinnest viable end-to-end slice — a **Customer/Account master record** flowing through the complete detect → derive → review → execute → audit cycle across all three systems — within a one-day delivery window.

---

## Personas

| Name | Role | Goals | Pain Points |
|------|------|-------|-------------|
| **Operations Coordinator** | Operations / Shared Services | Stop manually re-keying records that already exist in other systems; monitor which records are pending synchronisation and which are confirmed synced; reduce daily administrative burden by ≥ 80%. | Spends hours each day copying data between CRM, ERP, and Accounting; has no single view of which records are in sync; errors from manual transcription cause downstream reconciliation failures. |
| **Finance / AP Reviewer** | Finance / Accounts Payable | Understand exactly what will be written to downstream systems before authorising each change; maintain separation of duties; have confidence that no financial data is modified without explicit approval. | Cannot see proposed writes before they happen; lacks field-level detail of what will change; has no structured way to reject or amend a proposed update; bears accountability for errors introduced by others' manual entry. |
| **Compliance / Audit Observer** | Compliance / Internal Audit / Risk | Reconstruct after the fact who authorised any given write, on what basis, and what logic executed; satisfy SOC 2 and GDPR audit requirements; verify that governance controls are functioning. | Audit evidence is scattered across email threads and spreadsheets; cannot prove separation of duties; no tamper-evident record of authorisation decisions; GDPR Article 30 record-keeping obligations are met manually. |
| **IT Owner / Gatekeeper** | IT / Infrastructure / Security | Require assurance that agent-generated integration code never executes against the host application and runs only in isolated sandboxes; verify that sandbox lifecycle (created → executed → destroyed) is traceable. | No visibility into what code runs where; integration scripts execute in shared environments with broad permissions; no isolation guarantees; cannot verify after the fact that execution was contained. |

### Data Classification by Persona Interaction

| Data Entity | Classification | Personas with Access | Handling Requirements |
|-------------|---------------|---------------------|----------------------|
| Customer/Account master record fields | **Confidential** | All four personas (read); Reviewer (authorise writes) | Encrypted at rest; PII fields masked in logs; GDPR subject access rights supported |
| Work order content (before/after values, derivation logic) | **Internal** | All four personas (read); Reviewer (approve/reject/amend) | Retained in audit trail ≥ 1 year; append-only storage |
| Audit trail records | **Restricted** | Compliance Observer (read-only); all others (read own actions) | Immutable; never edited or deleted; cryptographic integrity verification; retained ≥ 7 years for SOC 2 |
| Authentication credentials and session tokens | **Restricted** | System only (no human access to raw values) | Encrypted in transit and at rest; never logged; rotated per policy |
| Dashboard aggregates (counts, statuses) | **Internal** | Operations Coordinator, Reviewer | No PII; standard access controls |

---

## User Stories

All user stories are structured as independent backend (BE) and frontend (UI) stories per the binding user refinement. Backend stories define API contracts, business logic, and data persistence. UI stories define presentation, interaction, and accessibility. Each can be developed, tested, and delivered independently.

### Feature 1: Change Detection (P1)

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **CD-BE-001** | As the Ledgerline agent, I want to monitor the source-of-truth system (CRM) for Customer/Account master record changes via event-driven detection, so that every create or update is captured in real time without polling delays. | P1 | • Event listener detects record creation and field-level updates within 2 seconds of commit. • Each detected change produces a structured change event containing: record ID, changed fields, old values, new values, timestamp, and event source. • Duplicate events for the same change are deduplicated. • If the source system is unreachable, the agent logs a structured error with context (system, timestamp, retry count) and retries with exponential backoff up to 5 attempts. • All detected changes are persisted to a durable queue before downstream processing. • Server-side input validation: record IDs validated against allow-list format; field names validated against the shared schema. |
| **CD-UI-001** | As an Operations Coordinator, I want to see a real-time feed of detected changes on the dashboard, so that I can confirm the agent is actively monitoring the source system. | P1 | • Change feed displays within 1 second of detection event arrival. • Each entry shows: record ID, changed fields summary, detection timestamp, and source system name. • Empty state: when no changes have been detected, the feed displays "No changes detected yet — monitoring is active" with a visible heartbeat indicator. • Loading state: a skeleton loader is shown while the feed initialises. • Error state: if the WebSocket connection drops, a banner reads "Live feed interrupted — reconnecting…" with automatic retry. • Keyboard navigable (Tab/Enter to select entries). • Screen reader announces new entries via ARIA live region. • Colour contrast meets WCAG 2.1 AA (≥ 4.5:1 for text). |

### Feature 2: Work Order Derivation & Presentation (P1)

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **WO-BE-001** | As the Ledgerline agent, I want to derive downstream updates for ERP and Accounting from a detected CRM change using the shared record schema, so that a complete work order is assembled automatically with field-level before/after values and derivation logic. | P1 | • For each detected change, the system derives target writes for both ERP and Accounting using the shared Customer/Account schema mapping. • Each derived write includes: target system, target record ID (or "new"), field-by-field before/after values, and the derivation rule applied. • Derivation logic is deterministic — the same input always produces the same output. • If a required source field is null or invalid, the work order is flagged as "Incomplete" with a specific error message identifying the missing field. • Work order is persisted with status "Pending" and a unique work order ID. • All inputs are validated server-side: field values validated against schema-defined types and allow-lists; no user input is interpolated into queries. |
| **WO-BE-002** | As the Ledgerline agent, I want to support the Amend workflow by accepting reviewer modification notes and re-deriving the work order, so that amended work orders return to Pending status with a new audit trail entry linked to the original. | P1 | • Amendment creates a new version of the work order (not an in-place edit). • The new version links to the original work order ID, preserving full amendment history. • Reviewer's modification notes are stored verbatim in the audit trail. • Amended work order status is set to "Pending" and requires fresh approval. • Audit trail entry records: original work order ID, amendment timestamp, reviewer identity, and modification notes. |
| **WO-UI-001** | As a Finance / AP Reviewer, I want to view a pending work order with full field-level detail — source values, derived target values, affected systems, and derivation logic — in a single screen, so that I can make an informed authorisation decision. | P1 | • Work order detail view loads in ≤ 1.5 seconds. • Displays: work order ID, source change summary, and for each target system (ERP, Accounting): target record, field-by-field before → after values, and derivation rule. • "Incomplete" work orders display a warning banner identifying missing fields. • Empty state: if no pending work orders exist, display "No work orders awaiting review." • All text meets WCAG 2.1 AA contrast ratios. • Fully keyboard navigable; screen reader reads field labels and values in logical order. • Locale-aware formatting for dates (ISO 8601 display) and currency values (locale-appropriate decimal/thousands separators). |
| **WO-UI-002** | As a Finance / AP Reviewer, I want to submit amendment notes on a work order, so that I can request modifications before the work order is re-derived and returned to the pending queue. | P1 | • "Amend" action is available alongside Approve and Reject. • Amendment notes text field: required (non-empty), max 2000 characters, server-side validated. • On submit, the UI displays a confirmation: "Amendment submitted — work order returned to pending queue." • Loading state: submit button shows spinner and is disabled during API call. • Error state: if the API returns an error, a descriptive message is shown (e.g., "Amendment could not be saved. Please try again.") without exposing stack traces. |

### Feature 3: Human Authorisation — Approve / Reject / Amend (P1)

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **HA-BE-001** | As the authorisation service, I want to enforce that only users with the Approver role can approve, reject, or amend work orders, so that the single-approver RBAC model is enforced server-side with deny-by-default. | P1 | • API endpoints for approve, reject, and amend return HTTP 403 for any user without the Approver role. • Role check is performed server-side on every request; client-side role display is cosmetic only. • Deny-by-default: all authorisation endpoints reject requests unless the caller's role is explicitly verified. • Concurrent session handling: if the same approver is logged in on two devices, both sessions can view work orders but only one approval per work order is accepted (optimistic locking). |
| **HA-BE-002** | As the authorisation service, I want to record every approve, reject, or amend decision as an immutable audit trail entry, so that the decision, reviewer identity, timestamp, and full work order content at the time of decision are permanently preserved. | P1 | • Each decision produces an append-only audit record containing: work order ID, decision (approve/reject/amend), reviewer user ID, ISO 8601 timestamp, and a snapshot of the full work order content at decision time. • Rejection records include the reviewer's reason (required, 1–2000 characters). • No audit record can be updated or deleted by any user, including administrators. • Audit records are retained for a minimum of 7 years. |
| **HA-UI-001** | As a Finance / AP Reviewer, I want to approve, reject, or amend a work order from the detail view with clear confirmation and feedback, so that I am confident my decision has been recorded. | P1 | • Three action buttons: Approve (green), Reject (red), Amend (amber) — all meeting WCAG 2.1 AA contrast. • Approve and Reject require a confirmation dialog: "Are you sure you want to [approve/reject] this work order?" with Cancel and Confirm options. • Reject requires a reason field (1–2000 characters, validated client-side and server-side). • On successful action, a success toast displays: "Work order [ID] [approved/rejected/amended] successfully." • On failure, an error message displays without stack traces or secrets. • Loading state: buttons disabled and spinner shown during API call. • Keyboard accessible: all actions reachable via Tab; confirmation dialogs trap focus. • Screen reader announces action outcomes via ARIA live region. |
| **HA-UI-002** | As an Operations Coordinator, I want to view work order details and status but be unable to approve, reject, or amend, so that the separation of duties is visible in the interface. | P1 | • Users without the Approver role see the work order detail view with Approve/Reject/Amend buttons disabled and visually greyed out. • A tooltip or label reads: "Only users with the Approver role can authorise work orders." • No client-side workaround can enable the buttons; server-side enforcement is the authority. |

### Feature 4: Sandboxed Execution (P1)

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **SE-BE-001** | As the execution service, I want to provision a new isolated, disposable sandbox for each approved work order, execute the derived writes within it, and destroy the sandbox immediately after, so that no agent-generated code ever runs in the host application process. | P1 | • Each approved work order triggers creation of a dedicated sandbox (one sandbox per work order, never shared). • Sandbox has no access to the host application process, other sandboxes, or unrelated network resources. • Resource limits enforced: memory ≤ 256 MB, CPU ≤ 0.5 cores, execution timeout ≤ 30 seconds. • Derived writes execute against real downstream system endpoints (no mocked steps). • Execution results (success/failure per target system, response payloads, error messages) are captured before sandbox destruction. • Sandbox is destroyed immediately after execution completes, regardless of outcome. • Sandbox lifecycle (created → executed → destroyed) is recorded in the audit trail with sandbox identifier and timestamps. |
| **SE-BE-002** | As the execution service, I want to auto-retry a failed sandbox execution up to 3 times before marking the work order as "Failed," so that transient downstream errors are handled without requiring immediate human intervention. | P1 | • On execution failure, the system retries automatically up to 3 times with exponential backoff (1s, 2s, 4s). • Each retry provisions a fresh sandbox (the failed sandbox is destroyed first). • Each retry attempt is recorded in the audit trail with: attempt number, error details, sandbox ID, and timestamp. • After 3 failed attempts, the work order status is set to "Failed" with a detailed error summary. • A failed work order cannot be retried without a new human authorisation cycle (fresh approval required). |
| **SE-UI-001** | As an IT Owner, I want to see the sandbox lifecycle (created → executed → destroyed) and sandbox identifier for each executed work order in the audit trail, so that I can verify execution isolation after the fact. | P1 | • Work order detail view includes a "Sandbox Execution" section showing: sandbox ID, creation timestamp, execution timestamp, destruction timestamp, and resource limits applied. • For retried work orders, each attempt is listed with its own sandbox details. • Failed executions display the error summary and retry history. • Governance indicator: a visible badge confirms "Executed in isolated sandbox" (green) or "Execution failed" (red). |

### Feature 5: Immutable Audit Trail (P1)

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **AT-BE-001** | As the audit trail service, I want to persist every work order lifecycle event as an append-only, immutable record with actor identity, timestamp, resource, and change details, so that no record can ever be edited or deleted by any user including administrators. | P1 | • Audit records are insert-only; UPDATE and DELETE operations on audit tables are blocked at the database level via triggers or policies. • Each record contains: event type, work order ID, actor user ID, ISO 8601 timestamp, full event payload (work order snapshot, decision, execution results as applicable). • PII fields within audit records are encrypted at rest. • PII is masked in application logs (e.g., customer name → "C***r"). • Audit trail supports GDPR data subject access requests: the system can produce a complete record of how a data subject's data was processed, by whom, and for what purpose. • Retention period: minimum 7 years (SOC 2); automated purge after retention period using cryptographic erasure. |
| **AT-BE-002** | As the audit trail service, I want to support search and filter by date range, system, record identifier, reviewer, and work order status, so that compliance observers can efficiently locate relevant entries. | P1 | • Search API accepts filters: date range (ISO 8601), target system (CRM/ERP/Accounting), record ID, reviewer user ID, work order status (Pending/Approved/Rejected/Amended/Synced/Failed). • API response time ≤ 500 ms for queries returning up to 100 records. • Results are paginated (default 25, max 100 per page). • All query parameters are validated server-side against allow-lists; no SQL interpolation. |
| **AT-BE-003** | As the audit trail service, I want to support export of audit trail records in a structured format suitable for external auditors, so that SOC 2 and GDPR compliance evidence can be provided on demand. | P1 | • Export endpoint produces JSON and CSV formats. • Exported records include all fields from the audit trail without modification. • Export is restricted to users with the Compliance Observer or Approver role. • Export actions are themselves recorded in the audit trail. |
| **AT-UI-001** | As a Compliance / Audit Observer, I want to search, filter, and browse the audit trail through a read-only interface, so that I can reconstruct the complete authorisation chain for any work order. | P1 | • Audit trail view loads in ≤ 2 seconds. • Filter controls for: date range, system, record ID, reviewer, status. • Each audit entry is expandable to show the full event payload. • Empty state: "No audit records match your filters." • Loading state: skeleton loader during search. • Error state: "Audit trail search failed — please try again" with no stack traces. • Read-only: no edit or delete controls are present in the UI. • Export button triggers download in selected format (JSON/CSV). • Fully keyboard navigable; screen reader compatible with ARIA labels on all controls. |

### Feature 6: Dashboard — Pending & Synced Overview (P2)

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **DB-BE-001** | As the dashboard service, I want to provide real-time aggregated counts and lists of work orders by status (Pending, Synced, Failed, Rejected), so that the UI can render a single-pane-of-glass view without client-side aggregation. | P2 | • API returns: count per status, list of work orders per status (paginated, default 25). • Response time ≤ 500 ms. • Data refreshes via server-sent events or WebSocket push within 2 seconds of any status change. • API validates all query parameters server-side. |
| **DB-UI-001** | As an Operations Coordinator, I want a real-time dashboard showing pending, synced, failed, and rejected work orders with governance indicators, so that I have a single view of cross-system propagation health. | P2 | • Dashboard loads in ≤ 2 seconds. • Four status sections: Pending (amber), Synced (green), Failed (red), Rejected (grey) — all colours meeting WCAG 2.1 AA contrast with accompanying text labels (not colour-only). • Each work order entry shows: work order ID, source record, affected systems, time in current status, and reviewer (if applicable). • Governance indicators visible: sandbox isolation status badge, audit trail completeness badge. • Clicking a work order navigates to its detail view. • Empty state per section: "No [status] work orders." • Loading state: skeleton cards during initial load. • Error state: "Dashboard data unavailable — retrying…" with automatic reconnection. • Responsive layout for desktop (1280px+). • Keyboard navigable; screen reader announces status counts on page load. |
| **DB-UI-002** | As a Finance / AP Reviewer, I want to open pending work orders directly from the dashboard to begin the authorisation process, so that I can efficiently work through my approval queue. | P2 | • Pending work orders in the dashboard are clickable links to the work order detail/authorisation view. • Badge shows count of pending work orders requiring action. • Reviewer's own approved/rejected work orders are visually distinguished. |

### Cross-Cutting: Authentication & Session Management (P1)

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **AU-BE-001** | As the authentication service, I want to authenticate users, assign roles (Approver, Coordinator, Observer, IT Owner), and enforce session policies, so that RBAC is consistently applied across all API endpoints. | P1 | • Authentication via username/password with MFA enrolment required for Approver role. • Session timeout: 30 minutes of inactivity; absolute timeout: 8 hours. • Concurrent sessions: allowed (max 3 per user); oldest session invalidated when limit exceeded. • All authentication events (login, logout, failed attempt, MFA challenge) are recorded in the audit trail. • Passwords are never logged. • API returns 401 for unauthenticated requests, 403 for insufficient role. |
| **AU-UI-001** | As any user, I want a login experience with MFA support, session timeout warnings, and clear logout, so that I can securely access Ledgerline with confidence in session integrity. | P1 | • Login form: username + password fields with client-side and server-side validation. • MFA enrolment flow for Approver role: QR code display, backup codes, verification step. • MFA recovery: backup code entry with clear instructions. • Session timeout warning: modal appears 5 minutes before expiry with "Extend Session" and "Log Out" options. • Logout: clears session; redirects to login; confirmation message displayed. • Failed login: "Invalid credentials" (no indication of which field is wrong). • Loading state: spinner on submit. • WCAG 2.1 AA compliant: all form fields labelled, error messages associated with fields, keyboard navigable. |

### Internationalisation & Localisation

| Story ID | Story | Priority | Acceptance Criteria |
|----------|-------|----------|---------------------|
| **I18N-001** | As a product decision, Ledgerline will launch in English only (en-GB / en-US) with locale-aware formatting for dates, currencies, and numbers, but will not require multi-language UI translations or right-to-left layout support for the initial release. | P2 | • All dates displayed in ISO 8601 or locale-appropriate format (e.g., "14 Aug 2026" for en-GB). • Currency values display with locale-appropriate decimal and thousands separators. • Number formatting respects browser locale. • UI text is externalised into a resource file to enable future translation without code changes. • RTL layout is not required for initial release. |

---

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|  
| **Duplicate manual re-keying reduction** | ≥ 80% reduction within first quarter of use | Compare volume of manual data-entry tasks performed by Operations coordinators before and after Ledgerline activation, measured by task tracking or time-study sampling. Baseline established during first two weeks of deployment. |
| **Downstream data-entry error reduction** | ≥ 90% reduction within first quarter of use | Track reconciliation discrepancies between CRM, ERP, and Accounting records monthly. Compare error counts pre- and post-activation. |
| **Time-to-reconcile reduction** | ≥ 70% reduction within first quarter of use | Measure average elapsed time from record change in source system to confirmed sync in all downstream systems. Compare against manual baseline. |
| **Zero unauthorised writes** | 0 writes executed without an approved work order — any violation is a highest-severity (P0) defect | Continuous automated monitoring: every write to a downstream system is cross-referenced against the approved work order log. Any unmatched write triggers an immediate alert. |
| **Audit trail completeness** | 100% of work order lifecycle events recorded | Automated reconciliation: compare work order state transitions against audit trail entries. Any missing entry triggers an alert. Monthly compliance report. |
| **Sandbox isolation compliance** | 100% of executions run in isolated, disposable sandboxes | Automated verification: every execution record in the audit trail must include a unique sandbox ID with created/destroyed timestamps. Any execution without sandbox metadata is a P0 defect. |
| **Work order review throughput** | Average time from Pending to decision ≤ 4 hours during business hours | Measure elapsed time between work order creation and first reviewer action (approve/reject/amend). Dashboard displays average and P95 latency. |
| **Dashboard page load time** | ≤ 2 seconds (P95) | Real User Monitoring (RUM) measuring time-to-interactive for the dashboard view. |
| **API response time** | ≤ 500 ms (P95) for all read endpoints; ≤ 1 second (P95) for write endpoints | Application Performance Monitoring (APM) on all API endpoints. |
| **Concurrent user capacity** | ≥ 25 concurrent users without degradation | Load testing during pre-launch; sustained monitoring in production. |
| **User activation rate** | ≥ 90% of Operations coordinators and ≥ 100% of Finance reviewers actively using the system within 2 weeks of launch | Track unique user logins and work order interactions per role per week. |
| **Audit export turnaround** | Compliance observer can produce a full audit export for any date range in ≤ 30 seconds | Measure export API response time for typical query ranges (1 day, 1 week, 1 month). |
| **GDPR data subject request fulfilment** | ≤ 72 hours from request to complete data extract | Track time from DSAR receipt to delivery of the data subject's processing record. |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **One-day delivery window is insufficient for end-to-end slice** | Medium | High — failure to demonstrate the core value proposition delays stakeholder buy-in | Scope the thin slice to a single record type (Customer/Account master) with one change type (update). Defer multi-record and create/delete scenarios to Phase 2. Pre-build the shared record schema and lightweight stub services before the demonstration day. |
| **Sandbox provisioning latency degrades user experience** | Medium | Medium — slow sandbox spin-up frustrates reviewers waiting for execution confirmation | Pre-warm a pool of sandbox containers; enforce a 30-second execution timeout; display a progress indicator in the UI with estimated time. Target sandbox provisioning ≤ 3 seconds. |
| **Sandbox escape or isolation failure** | Low | Critical — agent-generated code accesses host application or other sandboxes, violating the core security property | Use container-level isolation with gVisor runtime for kernel-level sandboxing. Enforce `--network none`, read-only root filesystem, non-root user, dropped capabilities, memory/CPU/PID limits. Automated security tests verify isolation on every deployment. |
| **Audit trail storage grows unboundedly** | Medium | Medium — performance degradation on audit queries; increased storage costs | Implement tiered storage: hot (≤ 90 days, fast query), warm (90 days–1 year, standard query), cold (1–7 years, archive). Partition audit tables by month. Monitor storage growth and set alerts at 80% capacity. |
| **Reviewer bottleneck — single approver role creates a queue** | High | Medium — work orders pile up in Pending status, negating the speed benefit of automation | Dashboard prominently displays queue depth and average wait time. Implement email/notification alerts when pending count exceeds threshold (e.g., > 10 work orders). Future phase: support multiple approvers with delegation. |
| **Source system event delivery is unreliable** | Medium | High — missed changes mean records fall out of sync silently | Implement at-least-once delivery with deduplication. Periodic reconciliation job compares source system state against last-known-good state. Dashboard displays "last heartbeat" timestamp for the source system monitor. |
| **Shared record schema does not cover all field variations across CRM, ERP, and Accounting** | Medium | Medium — derivation logic produces incomplete or incorrect work orders | Define the schema collaboratively with stakeholders from all three system teams before build. Flag unmapped fields as "Incomplete" in work orders rather than silently dropping them. |
| **GDPR compliance gap — PII flows through audit trail without adequate protection** | Low | Critical — regulatory penalty and reputational damage | Encrypt PII at rest in audit records. Mask PII in application logs. Implement DSAR export endpoint. Conduct a Data Protection Impact Assessment (DPIA) before launch. |
| **88% of agentic AI pilots fail to reach production (industry benchmark)** | Medium | High — project cancellation before delivering value | Ledgerline mitigates the top failure causes (governance and integration) by design: governance is the product's core feature, not an afterthought. The one-day thin slice forces early proof of end-to-end viability. |
| **EU AI Act Article 14 compliance (effective August 2026)** | Low | High — non-compliance with human oversight requirements for high-risk AI systems | Ledgerline's HITL architecture inherently satisfies Article 14: every AI-derived action requires explicit human approval. Document compliance posture and maintain evidence in the audit trail. |

```mermaid

```

---

## Rollout Plan

```mermaid
gantt
    title Ledgerline Rollout Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d
    
    section Phase 1 — MVP
    Shared schema & stub services     :p1a, 2026-08-18, 3d
    Change detection (BE)              :p1b, after p1a, 3d
    Work order derivation (BE)         :p1c, after p1a, 4d
    Authorisation service (BE)         :p1d, after p1c, 3d
    Sandbox execution (BE)             :p1e, after p1d, 4d
    Audit trail service (BE)           :p1f, after p1a, 5d
    Auth & session service (BE)        :p1g, after p1a, 3d
    Login & auth UI                    :p1h, after p1g, 3d
    Work order detail UI               :p1i, after p1c, 4d
    Authorisation UI                   :p1j, after p1d, 3d
    Sandbox status UI                  :p1k, after p1e, 2d
    Audit trail UI                     :p1l, after p1f, 4d
    End-to-end integration testing     :p1m, after p1k, 3d
    Security & accessibility audit     :p1n, after p1m, 2d
    MVP sign-off                       :milestone, after p1n, 0d
    
    section Phase 2 — Beta
    Dashboard (BE + UI)                :p2a, after p1n, 5d
    Change feed UI                     :p2b, after p1n, 3d
    Retry & failure handling polish    :p2c, after p1n, 3d
    DSAR export endpoint               :p2d, after p1n, 3d
    Load testing (25 concurrent users) :p2e, after p2a, 3d
    Beta user onboarding (5 users)     :p2f, after p2e, 5d
    Beta feedback incorporation        :p2g, after p2f, 5d
    Beta sign-off                      :milestone, after p2g, 0d
    
    section Phase 3 — GA
    Notification system (email alerts) :p3a, after p2g, 3d
    Audit trail tiered storage         :p3b, after p2g, 4d
    Performance optimisation           :p3c, after p2g, 3d
    SOC 2 evidence package             :p3d, after p3b, 3d
    Full team onboarding               :p3e, after p3c, 5d
    GA release                         :milestone, after p3e, 0d
```

### Phase 1 — MVP (Weeks 1–5, Target: 22 September 2026)

**Objective:** Deliver the thinnest end-to-end slice — a Customer/Account master record change detected in CRM, derived into work orders for ERP and Accounting, reviewed and approved by a Finance reviewer, executed in an isolated sandbox, and permanently recorded in the audit trail.

**Entry Criteria:** Shared record schema agreed with stakeholders; lightweight CRM, ERP, and Accounting stub services deployed; development environment provisioned.

**Deliverables:**
1. Change detection service monitoring CRM for Customer/Account record changes (CD-BE-001)
2. Work order derivation engine with shared schema mapping (WO-BE-001, WO-BE-002)
3. Human authorisation service with single-approver RBAC (HA-BE-001, HA-BE-002)
4. Sandboxed execution service with auto-retry (SE-BE-001, SE-BE-002)
5. Immutable audit trail service with search and export (AT-BE-001, AT-BE-002, AT-BE-003)
6. Authentication and session management service (AU-BE-001)
7. Login UI with MFA support (AU-UI-001)
8. Work order detail and authorisation UI (WO-UI-001, WO-UI-002, HA-UI-001, HA-UI-002)
9. Sandbox execution status UI (SE-UI-001)
10. Audit trail search and export UI (AT-UI-001)

**Exit Criteria:** End-to-end flow demonstrated with real triggers (no mocked steps); zero unauthorised writes; 100% audit trail completeness; WCAG 2.1 AA compliance verified; security review passed.

**Owner:** Product Lead + Engineering Lead

---

### Phase 2 — Beta (Weeks 6–9, Target: 20 October 2026)

**Objective:** Add the real-time dashboard, polish error handling and retry flows, onboard 5 beta users (2 Operations coordinators, 2 Finance reviewers, 1 Compliance observer), and validate performance under realistic load.

**Entry Criteria:** Phase 1 MVP sign-off complete; beta users identified and trained.

**Deliverables:**
1. Real-time dashboard with status aggregation and governance indicators (DB-BE-001, DB-UI-001, DB-UI-002)
2. Change detection feed UI (CD-UI-001)
3. GDPR data subject access request export endpoint (AT-BE-003 enhancement)
4. Load testing validated at 25 concurrent users
5. Beta user feedback collected and prioritised

**Exit Criteria:** All P1 and P2 stories verified in beta; ≥ 80% beta user satisfaction; P95 API response time ≤ 500 ms; P95 dashboard load ≤ 2 seconds; no P0/P1 defects open.

**Owner:** Product Lead + QA Lead

---

### Phase 3 — General Availability (Weeks 10–13, Target: 17 November 2026)

**Objective:** Harden for production use, implement notification system, optimise audit trail storage for long-term retention, prepare SOC 2 compliance evidence package, and onboard the full user base.

**Entry Criteria:** Phase 2 Beta sign-off complete; no open P0/P1 defects; SOC 2 auditor engaged.

**Deliverables:**
1. Email notification system for pending work order alerts and failure notifications
2. Tiered audit trail storage (hot/warm/cold) with automated lifecycle management
3. Performance optimisation based on beta feedback
4. SOC 2 compliance evidence package (audit trail exports, access control documentation, sandbox isolation verification)
5. Full team onboarding: all Operations coordinators, Finance reviewers, Compliance observers, and IT owners
6. Operational runbook and incident response procedures

**Exit Criteria:** All target KPIs met (80% re-keying reduction, 90% error reduction, 70% reconciliation time reduction); SOC 2 evidence package accepted by auditor; full user base onboarded and active; monitoring and alerting operational.

**Owner:** Product Lead + Operations Lead + Compliance Lead


---

## Confidence

Overall: **100%**

| Section | Score | Why | How to Improve |
|---------|-------|-----|----------------|
| Intent Alignment | 100% | All 6 intent features covered. | Intent is well-captured. Consider adding comments for priority rankings or phasing details. |
| Policy Compliance | 100% | All 19 policies addressed. | Good policy alignment. Verify any industry-specific regulations are covered. |
| Context Documents | N/A | Not provided — no documents uploaded for this dimension. | Upload the relevant documents to enable this check. |
| Structural Completeness | 100% | All 6 required sections present. | All expected sections are present. Add comments on any section if you want more depth. |

> Strongly aligned with project intent and provided context.