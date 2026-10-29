# AICTE Approva
**Integrated Approval Workflow Automation, Compliance Monitoring and Alert Management System**

A reference implementation of a role-based AICTE approval workspace. The complete interactive workspace is delivered in `index.html` and runs entirely in the browser with deterministic seed data. A runnable Flask integration service (`run.py`) exposes the read-only adapter API and a seeded SQLite database (`seed.py`) for existing AICTE systems.

> **Human oversight:** Approva alerts and recommends. It does **not** make scrutiny, verification, committee, approval or rejection decisions. Every decision is a manual, attributed action by a competent authority. This safeguard is shown in the UI and cannot be disabled.

---

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python run.py
```

Open **http://127.0.0.1:5000**. The workspace is also a self-contained UI: opening `index.html` directly in a modern browser starts the demo.

The service seeds `instance/approva.db` with:
- 4 regions
- 40 technical institutions
- 150 applications across Scrutiny, EVC, SAC/SHC, Approval, Approved and Returned
- overdue, nearing-SLA, new-institution, expiring-document and unfulfilled-undertaking examples
- 18 time-bound undertakings and 24 document-validity records
- an append-only, hash-linked audit stream

The demo workspace begins with a pre-authenticated Bureau Officer session so the command centre is immediately visible. Use **Sign out** to exercise the login screen, or the profile menu to switch roles.

---

## Demo credentials

| Role | Name | Scope | Password |
|---|---|---|---|
| Bureau Officer | Dr. Meera Krishnan | National | `AICTE@2026` |
| Regional Officer | K. Ramanathan | South | `AICTE@2026` |
| Scrutiny Officer | Aditi Rao | South | `AICTE@2026` |
| EVC Coordinator | Arjun Menon | South | `AICTE@2026` |
| Committee Member (SAC/SHC) | Prof. S. Nair | South | `AICTE@2026` |
| Institution | Dr. Rohan Deshpande | Vidyanagara Institute of Technology | `AICTE@2026` |
| System Administrator | Neha Sharma | National | `AICTE@2026` |

`demo1234` is also accepted by the demonstration login. Demonstration data is synthetic and contains no real AICTE records or personal data.

---

## Module coverage

### A. Workflow automation
- Configurable routes are stored as editable records, not hardcoded control flow.
- Seeded routes: **Only Scrutiny**, **Scrutiny + EVC**, **EVC + SAC/SHC**, **Only EVC**, **Scrutiny + EVC + SAC/SHC**, and an admin-defined **Scrutiny + SAC/SHC** route.
- Administrators can create combinations of Scrutiny, EVC and SAC/SHC; final approval is always the terminal human stage.
- Completing an authorised stage automatically moves the case to the next configured stage and notifies the next owner.
- Return/revert supports deficiency, clarification, re-verification and administrative correction. A detailed reason is mandatory and recorded.
- Standard communications are generated from controlled templates. The printable electronic case summary is available from every case file.
- Workflow Studio exposes automation rules and guardrails. The human-decision safeguard is fixed on.

### B. Dashboard and pendency
- Live KPI calculations from the scoped register.
- Region, stage, institution, officer/committee, status and ageing visibility.
- Ageing buckets: 0–7, 8–15, 16–30, 30+ days.
- Stage SLAs, workload ownership and the highlighted bottleneck stage.
- SLA watch list and escalation queue.
- Separate scope-aware command views for Bureau, Regional, Scrutiny, EVC, Committee and Institution roles.
- Full movement, observation, action and decision timeline in each application drawer.

### C. EVC scheduling
- Auto-queued EVC cases after scrutiny completion/direct-EVC routing.
- Committee and date assignment with mode and instructions.
- Seven-day visit schedule and completion tracking.
- New-institution priority watch.
- Reminder and escalation visibility for approaching or overdue visits.
- Manual completion of a visit can advance the case under the configured workflow.

### D. Undertakings and compliance
- Time-bound conditions with evidence requirements and due dates.
- Institution view of upcoming/overdue obligations.
- Evidence upload with PDF/JPG/PNG and 5 MB validation (client-side demonstration; server-side validation is the production requirement).
- Officer verification: accept, reject or request further evidence, with mandatory observations.
- Reminder ladder and escalation path.

### E. Lease and document validity
- Lease deeds, fire-safety NOCs, AICTE approvals, building certificates and title records.
- Issue date, expiry, category and required-document status.
- Configurable 90 / 60 / 30 / 7-day alerts and post-expiry escalation.
- Renewal evidence upload by the institution; officer verification and date update.
- Renewal-quality and alert-ladder panels.

### F. Notifications, escalation, reporting and audit
- Central in-app notification bell and simulated console/SMTP email delivery.
- Configurable Level 1 → 2 → 3 escalation matrix (admin only).
- Daily APScheduler integration jobs and **Run alert scan now**.
- Reports for pendency, EVC status, undertaking compliance, document validity, region performance and overdue cases.
- Functional CSV downloads and an A4 print/Save-as-PDF report view.
- Append-only audit register with predecessor and content hashes.
- **Audit verified** badge and full chain verification, including auditing the verification event itself.

---

## Role visibility

| Area | Institution | Scrutiny | Regional | Bureau | EVC | Committee | Admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Dashboard | Own | Region | Region | National | Region | Region | National |
| Applications | Own | Region | Region | All | Region | Region | All |
| Schedule EVC | View own | View | Assign | Oversight | Assign | View | Oversight |
| Stage decisions | — | Scrutiny | Final | Final | Visit completion | SAC/SHC | Config only |
| Undertakings / docs | Upload own | View | Verify | Oversight | View | View | Verify/config |
| Workflow Studio | — | — | View | View | — | — | Configure |
| Audit | — | — | Scoped | Full | — | — | Full |
| Administration | — | — | — | — | — | — | Full |

The prototype defaults to the Bureau view. Switching to **Institution** immediately rescopes the register and exposes the institution upload experience; switching to **Admin** exposes configuration controls.

---

## Read-only adapter API

`python run.py` provides:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Service and database health |
| GET | `/api/v1/institutions` | Institution master |
| GET | `/api/v1/applications` | Scoped application list; filters `region`, `stage`, `status` |
| GET | `/api/v1/applications/{id}` | Single application and stage history |
| GET | `/api/v1/evc-sessions` | Scheduled / completed EVC sessions |
| GET | `/api/v1/compliance/undertakings` | Undertaking register |
| GET | `/api/v1/documents/validity` | Document validity and renewal state |
| GET | `/api/v1/reports/pendency` | Aggregated stage pendency |

All endpoints are **GET-only**. Set `API_READ_TOKEN` to require `X-API-Key` on every data endpoint. There are intentionally no write endpoints.

### Adapter interface

`run.py` is the reference adapter boundary. An existing AICTE system can call these normalised JSON endpoints without coupling to workflow or compliance internals. In production, replace the SQLite connection with the institutional data services while preserving the response shape, read-only contract, audit scope filtering and authentication. Adapters can never issue a decision.

---

## Security and data protection

- Role-based route and data scoping in the UI; server implementation documents RBAC decorators and CSRF as production controls.
- Seeded server passwords use Werkzeug salted password hashes; demo credentials are documented above.
- Password fields are never written to the audit register or console logs.
- Upload type/size validation is demonstrated in the interface; production requires server MIME inspection and storage outside the public root.
- The demo avoids sensitive data in logs and uses synthetic records only.
- Audit entries are append-only and hash-linked; any historical edit causes verification to fail.
- Session timeout, CSRF protection, secure headers and environment-held secrets are represented in the interface and configuration files.
- `.env` and the SQLite instance directory are excluded from source control.

---

## Tests

```bash
pytest -q
```

`tests/test_domain.py` covers:
- allowed workflow route combinations
- next-stage routing
- mandatory return/revert reason
- SLA nearing/breach boundaries
- escalation day thresholds
- document expiry alert ladder
- undertaking fulfilment
- audit hash-chain integrity and tamper detection

---

## Configuration

Copy `.env.example` to `.env` and set values for your environment:

```bash
SECRET_KEY=change-me
API_READ_TOKEN=your-read-token
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
DATABASE_PATH=instance/approva.db
```

With no SMTP credentials, the notification engine uses the documented console fallback. Never commit `.env`.

---

## Project structure

```text
.
├── index.html                 # Complete interactive workspace (roles, modules, charts, audit)
├── run.py                     # Flask integration service + read-only API
├── seed.py                    # Deterministic SQLite seed (40 institutions / 150 applications)
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── instance/
│   └── approva.db             # Generated by seed.py (ignored in Git)
└── tests/
    └── test_domain.py
```

The workspace's front end uses local storage only for demonstration persistence. Use **Reset demonstration data** in the profile menu to restore the seed after experimenting.

---

## Five-minute demo script

**0:00 — Command centre (30 seconds).** Open the dashboard as Dr. Meera Krishnan, Bureau Officer. Point out 150-cycle volume, SLA watch, bottleneck EVC stage, ageing buckets and the region/institution scoping note. Explain the always-visible human-oversight safeguard.

**0:30 — Alert scan (25 seconds).** Select **Run alert scan**. Show the scan summary: records inspected, SLA exceptions, compliance obligations, document alerts, and the simulated email delivery log. Return to the notification bell and open a critical EVC alert.

**0:55 — Application workflow (60 seconds).** Go to **Applications**, filter to *Needs attention*, and open an EVC-stage case. Walk through the route, timeline, owner, stage SLA and system recommendation. As Bureau, **Complete stage** with a recorded note (or switch to Scrutiny for a scrutiny case). Return to the case: the next stage and the audit event are visible.

**1:55 — Return/revert control (40 seconds).** Open **Return / revert**, choose *Deficiency*, enter a detailed reason. Emphasise the mandatory reason, institution communication and permanent audit record. Continue to the EVC desk, assign committee and date, and show the committee schedule / new-institution watch.

**2:35 — Institution compliance (45 seconds).** Switch role to **Institution**. Open **Undertakings**, find a due obligation, upload a PDF/JPG/PNG under 5 MB, and submit. Switch back to Bureau/Regional, verify the evidence with observations, and show acceptance/request-more-evidence outcomes.

**3:20 — Documents & expiry (30 seconds).** Open **Document validity**. Point out lease/fire NOC records, 90/60/30/7-day alert ladder, uploaded renewal awaiting verification, and expired escalation examples. Open a renewal and record officer verification.

**3:50 — Reports (30 seconds).** Open **Reports**, switch across Pendency, EVC status, Compliance, Document validity, Region performance and Overdue. Apply a region filter, export CSV, and open the PDF print view.

**4:20 — Audit & admin (40 seconds).** Open the **Audit trail**, show the **Audit verified** badge, inspect a record's hashes and run **Verify hash chain**. Explain append-only correction. Switch to **Admin**, open Workflow Studio, create an admin-defined route, toggle an automation rule, and note that the human-decision safeguard remains locked. Close with the escalation matrix and integration-ready read-only API.

---

## Screenshots

Capture these views after `python run.py` or by opening `index.html`:

| View | What to show |
|---|---|
| Command centre | Dark Bureau KPI, application-flow chart, SLA watch, ageing profile |
| Application case | Route diagram, stage timeline, oversight recommendation, decision footer |
| EVC schedule | Seven-day visit strip, committee workload, new-institution watch |
| Compliance | Due/deadline ladder, evidence upload and officer verification |
| Document validity | Lease renewal, expiry windows and escalation |
| Audit trail | Verified hash chain and immutable event register |
| Administration | Workflow configuration, scheduled jobs and API adapters |

Suggested folder: `docs/screenshots/`. Add PNG captures and reference them in this section for the GitHub repository.

---

## License

MIT. See `LICENSE`.
