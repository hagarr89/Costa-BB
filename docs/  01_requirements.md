# docs/01_s.md

## 1. User Management & Authentication

| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| User registration (client / supplier) | As a client or supplier, I want to register to the system so that I can access relevant workflows. | Given a valid registration form, when submitted, then a user account is created in “pending approval” state and cannot access protected features. | Auth service, User DB | Validation rules not fully specified (required fields per role). |
| Login with JWT | As a user, I want to log in securely to access the system. | Given valid credentials, when login succeeds, then an access token and refresh token are issued and API calls with the token are authorized. | Auth service, JWT library | Token lifetime and refresh flow defined in separate security doc. |
| Role-based access control | As the system, I must restrict actions based on user role. | For each protected endpoint, when accessed by a user without required role, then the request is rejected with 403. | RBAC middleware | Granularity of roles vs permissions may evolve. |
| Admin verification flow | As an admin, I want to approve or reject users and suppliers. | Given a pending user, when admin approves, then the user status becomes “active” and access is granted. | Admin UI, Verification workflow | Legal/financial checks process is underspecified. |

---

## 2. Projects & Budgets

### Budget Model (MVP Scope)

For MVP, budget is defined at the project level only.

- Each project has a single total procurement budget.
- All RFQs and Orders are validated against the remaining project budget.
- Budget tracking includes:
  - Committed amount (approved orders)
  - Actual spend (paid invoices)

Category-level or RFQ-level budget granularity is out of scope for MVP.

The architecture must allow future extension to:
- Category-level budgets
- Phase-based budgets
- Multi-tier approval hierarchies

These capabilities are not part of the current implementation.


| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| Project creation | As a procurement manager, I want to create projects to group purchasing activity. | Given valid project data, when saved, then a project with unique ID is created and visible only to its organization. | Project service, DB | Required project fields not fully detailed. |
| Budget definition | As a manager, I want to define procurement budgets per project. | When a budget is set, then all RFQs and POs are validated against remaining budget. | Budget module | Budget granularity (category-level vs total) unclear. |
| Budget overrun approval | As a manager, I want to approve budget exceptions. | If an order exceeds budget, then it cannot be finalized until an approval action is recorded. | Approval workflow | Approval hierarchy not specified. |
| Cost dashboard | As a manager, I want to see actual vs approved budget. | Dashboard shows real-time totals of committed and spent amounts per project. | Analytics, Reporting | Performance at scale not validated. |

---

## 3. Catalog Management

| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| Central catalog (admin) | As an admin, I want to manage categories, units, and base products. | When catalog items are updated, then all users retrieve the latest version on next fetch. | Catalog service | Versioning and backward compatibility unclear. |
| Free-text items | As a site manager, I want to add non-catalog items. | Given a free-text item, it can be included in RFQs and compared manually by suppliers. | RFQ service | Normalization of free-text items not defined. |
| Spec file upload | As a user, I want to upload PDFs or images with specifications. | Uploaded files are stored securely and accessible only within the project context. | File storage, CDN | File size limits not specified. |

---

## 4. RFQ (Tender) Process

### RFQ State Machine

The RFQ lifecycle follows a strict state machine.

The authoritative RFQ states and allowed transitions
are defined in architecture.md Section 6.

This document describes business intent only.
Technical state enforcement is defined in architecture.


| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| RFQ creation | As a site manager, I want to create RFQs for materials. | Given required fields, when RFQ is submitted, then it is published to relevant suppliers. | RFQ service | Mandatory RFQ fields not fully defined. |
| Supplier targeting | As the system, I want to notify relevant suppliers by region and category. | Only suppliers matching RFQ region and category receive notifications. | Notification service, Supplier data | Region matching logic unclear. |
| Anonymous bidding | As a client, I want supplier identities hidden until deal closure. | Until PO approval, supplier identity fields are not accessible via API or UI. | Backend enforcement | Risk of leakage via metadata. |
| Second-chance bidding | As a supplier, I want to improve my offer in a second round. | When second-chance is triggered, suppliers can submit one updated offer before deadline. | RFQ workflow | Trigger conditions for second chance not specified. |

### Second-Chance Bidding (MVP Rule)

Second-chance bidding allows suppliers to improve their offer
after initial quote submission.

Trigger Conditions (MVP):

- Only a procurement_manager may trigger second chance.
- RFQ must currently be in `bidding` state.
- Second chance may be triggered once per RFQ.
- All suppliers who submitted a valid quote are eligible.
- Each supplier may submit exactly one revision.
- A new deadline must be defined.
- After deadline, RFQ returns to normal evaluation flow.

The authoritative state transitions are defined in architecture.md Section 6.


---

## 5. Orders, Contracts & Signatures

### Order State Machine

Order status transitions follow a strict state machine.

The authoritative Order states and transition rules
are defined in architecture.md Section 6.

All transitions must be enforced transactionally.


| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| Offer approval & PO creation | As a manager, I want to approve an offer and generate a PO. | When an offer is approved, then a PO is generated with immutable terms. | PO service | PO schema details not finalized. |
| Digital signature (PO) | As a user, I want to sign POs digitally. | A signed PO includes signer identity, timestamp, and audit trail. | E-signature service | Choice of signature provider not specified. |
| Framework contracts | As a manager, I want to upload and sign framework contracts. | Orders cannot be released if required contract is missing or unsigned. | Contract management | Contract versioning rules unclear. |
| Identity reveal post-approval | As the system, I want to reveal identities after approval. | After PO approval, both parties can view full organization details. | Access control | Edge cases around partial approvals. |

---

## 6. Logistics & Delivery

| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| Order status tracking | As a user, I want real-time order status updates. | Status transitions follow predefined states and are logged. | Order service | Exact status state machine not defined. |
| Delivery confirmation | As a site manager, I want to confirm delivery digitally. | Delivery is marked complete only after digital signature is captured. | E-signature service | Offline signature sync edge cases. |

---

## 7. Finance & Invoicing

| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| Invoice repository | As a finance manager, I want centralized invoices per project. | All invoices are linked to project and supplier and downloadable. | Finance module, Storage | Invoice formats not standardized. |
| Vendor onboarding pack | As a finance manager, I want to download a ZIP for ERP onboarding. | Generated ZIP contains all required supplier documents. | File generation service | ERP-specific requirements vary. |
| Invoice tracking | As a supplier, I want to track invoice payment status. | Invoice status updates are visible and consistent with finance records. | ERP integration | ERP integration scope unclear. |

---

## 8. Communication & Notifications

| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| Project chat | As a user, I want to communicate within a project context. | Messages are scoped to project and stored with timestamps. | Chat service | Message volume and retention policy undefined. |
| Anti-leakage filtering | As the system, I want to block sharing contact details before deal closure. | Messages containing phone/email patterns are blocked until PO approval. | Regex filter, Backend enforcement | Regex false positives/negatives. |
| Notifications | As a user, I want alerts for relevant events. | Notifications are triggered for RFQs, offers, approvals, and deliveries. | Notification service | Channel preferences (email/push) not specified. |

---

## 9. Non-Functional Requirements

| Feature / Capability | User Story | Acceptance Criteria | Dependencies | Risks / Unknowns |
|---|---|---|---|---|
| Multi-tenancy isolation | As the system, I must isolate data per project. | Every query enforces Project ID filtering and cross-project access is impossible. | DB schema, Middleware | Risk of accidental leaks via joins. |
| Offline support | As a field user, I want to work with poor connectivity. | Drafts are saved locally and synced when connection is restored. | Client storage, Sync engine | Conflict resolution strategy unclear. |
| Performance & UX | As a user, I want a fast mobile-first experience. | Critical actions complete within defined SLA under normal load. | Frontend, API | SLA thresholds not defined. |

---

## Open Questions to Resolve Before Implementation

1. What are the exact mandatory fields and validation rules for RFQs, POs, and Projects?
2. How is “second-chance” bidding triggered and limited?
3. What digital signature provider and legal standard will be used?
4. What is the detailed budget model (per category vs per project)?
5. How deep is ERP integration expected in MVP vs later phases?
6. What are the exact order status states and transitions?


