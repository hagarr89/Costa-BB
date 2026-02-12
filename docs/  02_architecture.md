# COSTA Backend Architecture
Authoritative Specification
Single Source of Truth

All generated code MUST strictly follow this document.
No architectural deviations are allowed without explicit approval.

---

# 1. System Overview

COSTA is a multi-tenant B2B construction procurement platform.

The system is:

- Modular monolith (domain-based)
- Strictly multi-tenant (project-scoped)
- Workflow-driven (state machines mandatory)
- Financial and legally sensitive
- Production-grade from day one
- Horizontally scalable

Architecture layering is mandatory:

Controller → Service → Repository → Database

Rules:

- No business logic in controllers
- No direct DB access outside repositories
- Explicit dependency injection
- Async-first design
- Production-safe from first deployment
---

# 2. Technology Stack

- FastAPI (async)
- PostgreSQL
- SQLAlchemy 2.0 (async)
- Alembic (migrations)
- Redis (cache + rate limiting + Celery broker)
- Celery (background jobs)
- Stripe (subscriptions + commissions)
- Structlog (structured logging)
- Pydantic v2 (validation)
- JWT (access + refresh tokens)
- bcrypt (password hashing)

---

# 3. Multi-Tenancy & Isolation Model (Authoritative)

This section defines the isolation model of COSTA.

COSTA operates with two distinct isolation layers:

1. Platform Tenant (Organization-Level)
2. Operational Tenant (Project-Level)

These two layers serve different responsibilities and must never be conflated.

This section is authoritative.


---

## 3.1 Tenant Model Definition

### Platform Tenant = Organization  
### Operational Tenant = Project

When the term "tenant" is used without qualification:

- In workflow context → Tenant = Project
- In identity, billing, or platform context → Tenant = Organization

This distinction is mandatory and must not be blurred.


---

## 3.2 Platform Tenant (Organization-Level Isolation)

Organizations represent companies using the platform.

An organization can be:

- Customer
- Supplier

This layer governs:

- User identity
- Authentication
- Vetting and onboarding
- Subscriptions (SaaS billing)
- Supplier commissions
- Organization settings

### Rules

- Users belong to exactly one organization.
- Organization data must never cross organization boundaries.
- Subscription data is scoped by `organization_id`.
- Commission records are scoped by `supplier_org_id`.
- Authorization must validate organization membership.
- No cross-organization data access is allowed without explicit workflow authorization (e.g., awarded order).

Organization isolation governs platform access and company-level boundaries.


---

## 3.3 Operational Tenant (Project-Level Isolation)

Projects are the primary tenant boundary for procurement workflows.

All transactional and financial workflow data MUST be strictly project-scoped.

### Project-Scoped Entities

The following entities MUST include `project_id` (NOT NULL unless explicitly justified):

- RFQs
- RFQ Items
- Quotes
- Quote Items
- Orders
- Order Items
- Deliveries
- Delivery Events
- Invoices
- Invoice Lines
- Messages
- Notifications
- Budget Exceptions
- Signatures
- Any future workflow entity

### Mandatory Rules

- Every transactional query MUST include:

  WHERE project_id = :current_project_id

- Repository layer MUST enforce project filtering automatically.
- Controllers MUST reject requests missing `project_id`.
- Services MUST never bypass tenant filtering.
- Cross-project joins are forbidden.
- No implicit project inference is allowed.
- Admin bypass requires explicit override flag.

Project isolation defines the legal and financial security boundary of the system.


---

## 3.4 Table Classification

Tables are divided into three categories.


### A. Project-Scoped (Transactional / Workflow Tables)

- Must include `project_id`
- Must enforce strict filtering
- Must never be globally queried


### B. Organization-Scoped (Identity & Billing Layer)

Must include `organization_id` and MUST NOT include `project_id`:

- organizations
- users
- subscriptions
- vetting_reviews


### C. Global Platform Tables (Reference Data)

Must NOT include `project_id` or `organization_id`:

- catalog_categories
- catalog_units
- catalog_products

These are platform-wide reference tables.


---

## 3.5 Enforcement Strategy

Isolation is enforced through:

- Explicit `organization_id` and `project_id` columns
- Repository-level automatic scoping
- Service-layer RBAC validation
- Explicit project membership validation
- Optional PostgreSQL Row-Level Security (RLS) for defense-in-depth
- Automated tenant isolation tests

Security enforcement must always live in the backend.
Frontend masking or filtering is not trusted.


---

## 3.6 Non-Negotiable Principles

- No cross-project data access.
- No cross-organization access without explicit workflow authorization.
- No tenant inference.
- No business logic in controllers.
- No security enforcement delegated to frontend.
- No deviation from this model without explicit approval.


---

This tenant model is mandatory and defines the isolation guarantees of the system.

---

# 4. Domain Architecture (Modular Monolith)

The system is organized by domain.

Each domain MUST contain:

- controller
- service
- repository
- dto
- validation
- types

Folder structure:

app/
  core/
  auth/
  organizations/
  projects/
  procurement/
  contracts/
  logistics/
  finance/
  catalog/
  notifications/

Domains are isolated.

Rules:

- No cross-domain repository access.
- Domains communicate via services only.
- No circular dependencies.

---

# 5. Layer Responsibilities

## 5.1 Controllers

- Handle HTTP only
- Validate request DTOs
- Call services
- Return structured responses
- No business logic
- No DB access

## 5.2 Services

- Contain all business logic
- Enforce state machines
- Enforce anonymity rules
- Enforce RBAC
- Manage transactions
- Publish events post-commit

## 5.3 Repositories

- Data access only
- Apply automatic `project_id` filtering
- No business logic
- No workflow decisions

---

# 6. State Machines (Mandatory)

All workflow entities MUST have explicit state machines.
Invalid transitions MUST be rejected.

## RFQ States

- draft
- published
- second_chance
- awarded
- cancelled
- bidding
- closed


## Order States

- pending_signature
- signed
- released
- in_delivery
- delivered
- completed
- cancelled

Rules:

- State transitions MUST be validated in service layer.
- Transitions MUST run inside database transactions.
- Invalid transitions MUST raise INVALID_STATE_TRANSITION.

---

# 7. Security Requirements

- Validate all inputs (DTO validation mandatory)
- Never trust client-provided IDs
- Always verify project membership
- Always verify organization membership
- Never expose supplier identity pre-award
- Never log secrets, tokens, or raw PII
- Store digital signature metadata with audit trail
- Implement regex-based anti-leakage filtering for chat

Anonymity enforcement MUST live in service layer.
Frontend masking is not trusted.

---

# 8. Role-Based Access Control (RBAC)

Roles:

Customer:
- procurement_manager
- site_manager
- finance_manager

Supplier:
- sales_rep
- supplier_manager
- finance_rep

Admin:
- system_admin

Rules:

- Every endpoint MUST enforce role checks.
- Authorization must validate:
  - Role
  - Organization membership
  - Project membership
- Unauthorized access MUST return 403.

---

# 9. Transactions & Data Integrity

Transactions are mandatory for:

- Awarding RFQ
- Creating Orders
- Signing Orders
- Delivery confirmation
- Budget exception approvals

Rules:

- No multi-step write without transaction.
- Use DB constraints (FK, unique, enums).
- Enforce workflow invariants in service layer AND guard at DB when possible.

---

# 10. Background Jobs

Use async jobs for:

- Quote expiration
- Second chance triggers
- Notifications
- Analytics aggregation
- Commission calculation

Rules:

- Jobs must be idempotent.
- Events published only after successful commit.
- Include correlation_id.
- Retry with exponential backoff.
- Dead-letter queue required.

---

# 11. Observability

Structured logging (JSON) required with:

- request_id
- user_id
- organization_id
- project_id
- operation name
- latency

Metrics required:

- Request latency per endpoint
- Error rate per endpoint
- Queue lag
- Workflow KPIs (RFQ publish, quote submit, award, order sign)

Tracing required across HTTP and background jobs.

---

# 12. Error Handling

All errors must follow structure:

{
  "code": "ERROR_CODE",
  "message": "Human readable message",
  "details": {}
}

Standard error codes include:

- PROJECT_SCOPE_REQUIRED
- UNAUTHORIZED_ROLE
- INVALID_STATE_TRANSITION
- BUDGET_EXCEEDED
- RFQ_LOCKED
- ANONYMITY_VIOLATION

Never expose raw database or provider errors.

---

# 13. Performance & Scalability

- Avoid N+1 queries
- Index all `project_id` columns
- Paginate all list endpoints
- Cache safe-to-stale reads in Redis
- Use optimistic locking for concurrent updates
- Horizontal scalability supported

---

# 14. Non-Negotiable Rules

- No business logic in controllers
- No direct DB access outside repositories
- No cross-project joins
- No cross-domain repository access
- No tenant inference
- No security logic in frontend
- No deviation from this architecture without approval
 
—
## 14.1 Cross-Project Access Rule (Authoritative)

The prohibition on cross-project joins does NOT forbid relational integrity
between workflow tables (e.g., orders → quotes → rfqs → projects).

Foreign keys between workflow entities are allowed and required
for data integrity.

However:

No query may access or return data from multiple projects
within the same execution context.

All workflow queries MUST be explicitly scoped by `project_id`.

Mandatory rules:

- Queries MUST include:

  WHERE project_id = :current_project_id

- Querying by `id` alone is forbidden.
- Project context MUST NOT be inferred indirectly via joins.
- The repository layer MUST enforce project filtering automatically.
- Services MUST validate project membership before invoking repositories.
- Admin override requires an explicit, audited flag.

Example — Forbidden:

  SELECT * FROM orders WHERE id = :order_id;

Example — Required:

  SELECT * FROM orders
  WHERE id = :order_id
  AND project_id = :current_project_id;

The database guarantees relational consistency.
The application guarantees tenant isolation.

Tenant isolation is a security boundary and is non-negotiable.

—-


This architecture defines production-grade infrastructure
for a financial and legal workflow system.


