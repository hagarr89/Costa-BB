Absolutely — here’s the full content of the generated costa_postgres_schema.md:

COSTA — PostgreSQL Primary DB Schema (MVP)
Generated from the COSTA PRD. Focus: primary OLTP schema for multi-project (project-scoped) procurement workflows.
1) High-level entity overview
Identity & tenancy
organizations: Companies using the platform (customers/contractors/developers and suppliers).
users: Human accounts; belong to an organization; admin-vetted.
project_memberships: Users assigned to projects with project-level roles.
projects: Procurement projects owned by a customer organization; the primary tenant boundary for most data.
Catalog
catalog_categories: Admin-managed category taxonomy.
catalog_units: Admin-managed units of measure.
catalog_products: Admin-managed master products (base products).
supplier_product_offers: Supplier-specific availability/pricing metadata for catalog products (inventory/regions/base pricing).
RFQ → Quote → Order
rfqs: Request for quotation; includes location and anonymized tender state.
rfq_attachments: Specs/photos/PDFs tied to an RFQ.
rfq_items: Line items requested; supports catalog-backed or free-text items.
rfq_suppliers: Which suppliers were invited/notified for an RFQ (supports filtering by delivery region).
quotes: Supplier submissions per RFQ (anonymized pre-award); supports “Second Chance” revisions.
quote_items: Supplier pricing and lead times per RFQ item and revision.
orders: Purchase orders generated from an accepted quote; reveals supplier post-award.
order_items: Line items for the PO.
signatures: Digital signatures (PO signing, delivery confirmation), stored with audit trail.
Logistics
deliveries: Delivery records per order (may be multiple drops/partials if enabled).
delivery_events: Status history for deliveries.
Contracts
contracts: Framework agreements linked to customer+supplier (+region); can block order release until signed.
Finance
invoices: Supplier invoices linked to project and supplier.
invoice_lines: Invoice line items.
supplier_onboarding_documents: Supplier-provided finance/legal docs used for onboarding ZIP and ERP setup tracking.
Comms & notifications
chats: Project-based chat containers (one per project; can extend to RFQ-level later).
messages: Messages with optional anti-leakage moderation flags.
notifications: System notifications (RFQ events, invoice events, onboarding events, approvals).
Admin & monetization
vetting_reviews: Admin verification workflow for organizations/users.
subscriptions: Customer subscriptions (SaaS revenue).
commissions: Supplier commission (1–3%) per closed deal; supports settlement lifecycle.

2) Schema SQL (PostgreSQL)
-- Enable UUID generation (choose one)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================
-- ENUMS
-- =========================
DO $$ BEGIN
  CREATE TYPE organization_type AS ENUM ('customer', 'supplier');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE vetting_status AS ENUM ('pending', 'approved', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE project_role AS ENUM ('procurement_manager', 'site_manager', 'finance_manager', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE rfq_status AS ENUM ('draft', 'published', 'bidding', 'second_chance', 'awarded', 'closed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE quote_status AS ENUM ('submitted', 'revised', 'withdrawn', 'expired', 'accepted', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE order_status AS ENUM ('pending_signature', 'signed', 'released', 'in_delivery', 'delivered', 'cancelled', ‘completed’);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE delivery_status AS ENUM ('pending', 'scheduled', 'in_transit', 'delivered', 'failed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE contract_status AS ENUM ('draft', 'sent', 'signed', 'expired', 'terminated');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE invoice_status AS ENUM ('draft', 'issued', 'approved', 'disputed', 'paid', 'void');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE notification_type AS ENUM (
    'rfq_published','quote_received','second_chance_started','order_created','order_signed',
    'delivery_updated','invoice_uploaded','supplier_onboarding_required','vetting_required'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE commission_status AS ENUM ('pending', 'accrued', 'invoiced', 'settled', 'void');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =========================
-- CORE: organizations, users, projects
-- =========================
CREATE TABLE IF NOT EXISTS organizations (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  type               organization_type NOT NULL,
  name               text NOT NULL,
  legal_name         text,
  country_code       char(2),
  vat_id             text,
  registration_id    text,
  website_url        text,
  phone              text,
  email              text,
  vetting_status     vetting_status NOT NULL DEFAULT 'pending',
  vetted_at          timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id    uuid REFERENCES organizations(id) ON DELETE CASCADE,
  email              citext NOT NULL,
  full_name          text NOT NULL,
  phone              text,
  is_system_admin    boolean NOT NULL DEFAULT false,
  vetting_status     vetting_status NOT NULL DEFAULT 'pending',
  vetted_at          timestamptz,
  last_login_at      timestamptz,
  is_active          boolean NOT NULL DEFAULT true,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS projects (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  name               text NOT NULL,
  code               text, -- optional client-facing project identifier
  description        text,
  currency_code      char(3) NOT NULL DEFAULT 'EUR',
  planned_budget     numeric(14,2),
  budget_enforced    boolean NOT NULL DEFAULT true,
  start_date         date,
  end_date           date,
  is_active          boolean NOT NULL DEFAULT true,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (customer_org_id, code)
);

CREATE TABLE IF NOT EXISTS project_memberships (
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id            uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role               project_role NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);

-- Budget exception approvals (for "approve exceptions before orders are placed")
CREATE TABLE IF NOT EXISTS budget_exceptions (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  requested_by_user  uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  approved_by_user   uuid REFERENCES users(id) ON DELETE RESTRICT,
  requested_amount   numeric(14,2) NOT NULL,
  approved_amount    numeric(14,2),
  reason             text,
  status             text NOT NULL DEFAULT 'pending', -- keep flexible; can be enum later
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- CATALOG (admin managed)
-- =========================
CREATE TABLE IF NOT EXISTS catalog_categories (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id          uuid REFERENCES catalog_categories(id) ON DELETE SET NULL,
  name               text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (parent_id, name)
);

CREATE TABLE IF NOT EXISTS catalog_units (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code               text NOT NULL, -- e.g. m2, pcs, kg
  name               text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (code)
);

CREATE TABLE IF NOT EXISTS catalog_products (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id        uuid REFERENCES catalog_categories(id) ON DELETE SET NULL,
  sku                text, -- optional internal sku
  name               text NOT NULL,
  description        text,
  default_unit_id    uuid REFERENCES catalog_units(id) ON DELETE SET NULL,
  is_active          boolean NOT NULL DEFAULT true,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (sku)
);

-- Supplier-specific catalog offer + delivery region/inventory knobs
CREATE TABLE IF NOT EXISTS supplier_product_offers (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  product_id         uuid NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  base_price         numeric(14,4),
  currency_code      char(3) NOT NULL DEFAULT 'EUR',
  in_stock_qty       numeric(14,4),
  min_lead_days      integer,
  max_lead_days      integer,
  delivery_regions   text[], -- MVP: simple; normalize later if needed
  is_active          boolean NOT NULL DEFAULT true,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (supplier_org_id, product_id)
);

-- =========================
-- RFQ
-- =========================
CREATE TABLE IF NOT EXISTS rfqs (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  created_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  title              text NOT NULL,
  description        text,
  status             rfq_status NOT NULL DEFAULT 'draft',
  currency_code      char(3) NOT NULL DEFAULT 'EUR',
  expires_at         timestamptz, -- quote validity window
  gps_lat            numeric(9,6),
  gps_lng            numeric(9,6),
  published_at       timestamptz,
  awarded_at         timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rfq_attachments (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rfq_id             uuid NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  uploaded_by_user   uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  file_name          text NOT NULL,
  mime_type          text,
  storage_url        text NOT NULL,
  sha256             text,
  created_at         timestamptz NOT NULL DEFAULT now()
);

-- Items can be catalog-backed OR free-text
CREATE TABLE IF NOT EXISTS rfq_items (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rfq_id             uuid NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  line_no            integer NOT NULL,
  product_id         uuid REFERENCES catalog_products(id) ON DELETE SET NULL,
  free_text_name     text, -- required when product_id is null
  specification      text,
  quantity           numeric(14,4) NOT NULL,
  unit_id            uuid REFERENCES catalog_units(id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (rfq_id, line_no),
  CHECK (
    (product_id IS NOT NULL AND free_text_name IS NULL)
    OR
    (product_id IS NULL AND free_text_name IS NOT NULL)
  )
);

-- Which suppliers are invited/notified
CREATE TABLE IF NOT EXISTS rfq_suppliers (
  rfq_id             uuid NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  invited_at         timestamptz NOT NULL DEFAULT now(),
  notified_at        timestamptz,
  PRIMARY KEY (rfq_id, supplier_org_id)
);

-- =========================
-- QUOTES (supports "Second Chance" revisions)
-- =========================
CREATE TABLE IF NOT EXISTS quotes (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rfq_id             uuid NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  submitted_by_user  uuid REFERENCES users(id) ON DELETE RESTRICT,
  revision_no        integer NOT NULL DEFAULT 1, -- 1=initial, 2+=second chance revisions
  status             quote_status NOT NULL DEFAULT 'submitted',
  notes              text,
  total_amount       numeric(14,2),
  lead_days          integer,
  submitted_at       timestamptz NOT NULL DEFAULT now(),
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (rfq_id, supplier_org_id, revision_no)
);

CREATE TABLE IF NOT EXISTS quote_items (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  quote_id           uuid NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  rfq_item_id        uuid NOT NULL REFERENCES rfq_items(id) ON DELETE RESTRICT,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  unit_price         numeric(14,4) NOT NULL,
  quantity           numeric(14,4) NOT NULL,
  tax_rate           numeric(6,4), -- e.g. 0.19
  line_total         numeric(14,2) GENERATED ALWAYS AS (round(unit_price * quantity, 2)) STORED,
  delivery_days      integer,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (quote_id, rfq_item_id)
);

-- =========================
-- CONTRACTS (framework agreements)
-- =========================
CREATE TABLE IF NOT EXISTS contracts (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  region_code        text, -- e.g. "DE-BE" or internal region identifier
  status             contract_status NOT NULL DEFAULT 'draft',
  effective_from     date,
  effective_to       date,
  signed_at          timestamptz,
  signed_by_user_id  uuid REFERENCES users(id) ON DELETE SET NULL,
  storage_url        text, -- signed PDF/contract artifact
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (customer_org_id, supplier_org_id, region_code)
);

-- =========================
-- ORDERS (POs)
-- =========================
CREATE TABLE IF NOT EXISTS orders (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  rfq_id             uuid REFERENCES rfqs(id) ON DELETE SET NULL,
  accepted_quote_id  uuid NOT NULL REFERENCES quotes(id) ON DELETE RESTRICT,
  customer_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  contract_id        uuid REFERENCES contracts(id) ON DELETE SET NULL,
  status             order_status NOT NULL DEFAULT 'pending_signature',
  po_number          text,
  total_amount       numeric(14,2),
  currency_code      char(3) NOT NULL DEFAULT 'EUR',
  requires_contract  boolean NOT NULL DEFAULT false,
  contract_required_by timestamptz,
  released_at        timestamptz,
  created_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (customer_org_id, po_number)
);

CREATE TABLE IF NOT EXISTS order_items (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id           uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  rfq_item_id        uuid REFERENCES rfq_items(id) ON DELETE SET NULL,
  product_id         uuid REFERENCES catalog_products(id) ON DELETE SET NULL,
  description        text NOT NULL,
  quantity           numeric(14,4) NOT NULL,
  unit_id            uuid REFERENCES catalog_units(id) ON DELETE SET NULL,
  unit_price         numeric(14,4) NOT NULL,
  tax_rate           numeric(6,4),
  line_total         numeric(14,2) GENERATED ALWAYS AS (round(unit_price * quantity, 2)) STORED,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- SIGNATURES (PO signing, delivery confirmation)
-- =========================
CREATE TABLE IF NOT EXISTS signatures (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         uuid REFERENCES projects(id) ON DELETE CASCADE,
  signed_by_user_id  uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  signed_at          timestamptz NOT NULL DEFAULT now(),
  purpose            text NOT NULL, -- 'po_sign', 'delivery_confirm', 'contract_sign', etc.
  entity_type        text NOT NULL, -- 'orders','deliveries','contracts', etc.
  entity_id          uuid NOT NULL,
  signature_payload  jsonb NOT NULL, -- device+biometric hash, image, certificate, etc.
  ip_address         inet,
  user_agent         text,
  created_at         timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- DELIVERIES
-- =========================
CREATE TABLE IF NOT EXISTS deliveries (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id           uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  status             delivery_status NOT NULL DEFAULT 'pending',
  scheduled_for      timestamptz,
  delivered_at       timestamptz,
  tracking_ref       text,
  proof_signature_id uuid REFERENCES signatures(id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS delivery_events (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id        uuid NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  status             delivery_status NOT NULL,
  note               text,
  occurred_at        timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- INVOICES
-- =========================
CREATE TABLE IF NOT EXISTS invoices (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  order_id           uuid REFERENCES orders(id) ON DELETE SET NULL,
  invoice_number     text NOT NULL,
  status             invoice_status NOT NULL DEFAULT 'issued',
  currency_code      char(3) NOT NULL DEFAULT 'EUR',
  subtotal_amount    numeric(14,2),
  tax_amount         numeric(14,2),
  total_amount       numeric(14,2),
  issued_at          date,
  due_at             date,
  storage_url        text, -- PDF
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (supplier_org_id, invoice_number)
);

CREATE TABLE IF NOT EXISTS invoice_lines (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id         uuid NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  line_no            integer NOT NULL,
  description        text NOT NULL,
  quantity           numeric(14,4),
  unit_price         numeric(14,4),
  tax_rate           numeric(6,4),
  line_total         numeric(14,2),
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (invoice_id, line_no)
);

-- Supplier onboarding docs for finance/ERP setup
CREATE TABLE IF NOT EXISTS supplier_onboarding_documents (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  project_id         uuid REFERENCES projects(id) ON DELETE SET NULL, -- some docs may be global to supplier
  doc_type           text NOT NULL, -- tax_form, bank_details, incorporation, etc.
  file_name          text NOT NULL,
  storage_url        text NOT NULL,
  status             text NOT NULL DEFAULT 'received', -- received/validated/rejected
  uploaded_by_user   uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- NOTIFICATIONS
-- =========================
CREATE TABLE IF NOT EXISTS notifications (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         uuid REFERENCES projects(id) ON DELETE CASCADE,
  recipient_user_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type               notification_type NOT NULL,
  title              text NOT NULL,
  body               text,
  data               jsonb NOT NULL DEFAULT '{}'::jsonb,
  read_at            timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- CHAT (project-based) + anti-leakage flags
-- =========================
CREATE TABLE IF NOT EXISTS chats (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  topic              text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id)
);

CREATE TABLE IF NOT EXISTS messages (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id            uuid NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
  project_id         uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  sender_user_id     uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  body               text NOT NULL,
  is_blocked         boolean NOT NULL DEFAULT false,
  blocked_reason     text, -- regex match etc.
  created_at         timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- ADMIN: vetting + monetization
-- =========================
CREATE TABLE IF NOT EXISTS vetting_reviews (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_type       text NOT NULL, -- 'organizations' | 'users'
  subject_id         uuid NOT NULL,
  reviewer_user_id   uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status             vetting_status NOT NULL,
  notes              text,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  plan_code          text NOT NULL,
  status             text NOT NULL DEFAULT 'active',
  started_at         date NOT NULL DEFAULT current_date,
  ended_at           date,
  amount_monthly     numeric(14,2),
  currency_code      char(3) NOT NULL DEFAULT 'EUR',
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS commissions (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id           uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  supplier_org_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  rate              numeric(6,4) NOT NULL, -- e.g. 0.01 to 0.03
  amount            numeric(14,2) NOT NULL,
  status            commission_status NOT NULL DEFAULT 'pending',
  accrued_at        timestamptz NOT NULL DEFAULT now(),
  settled_at        timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (order_id)
);


3) Indexes & constraints
-- CORE
CREATE INDEX IF NOT EXISTS idx_users_org ON users (organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_customer ON projects (customer_org_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON project_memberships (user_id);

-- Tenant scoping helpers (project_id everywhere)
CREATE INDEX IF NOT EXISTS idx_rfqs_project_status ON rfqs (project_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rfq_items_rfq ON rfq_items (rfq_id, line_no);

CREATE INDEX IF NOT EXISTS idx_quotes_rfq_supplier ON quotes (rfq_id, supplier_org_id, revision_no DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_project_status ON quotes (project_id, status, submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_quote_items_quote ON quote_items (quote_id);

CREATE INDEX IF NOT EXISTS idx_orders_project_status ON orders (project_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);

CREATE INDEX IF NOT EXISTS idx_deliveries_order ON deliveries (order_id);
CREATE INDEX IF NOT EXISTS idx_delivery_events_delivery ON delivery_events (delivery_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_invoices_project_status ON invoices (project_id, status, issued_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications (recipient_user_id, read_at);

-- Chat
CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages (chat_id, created_at);

-- Signatures: often queried by entity
CREATE INDEX IF NOT EXISTS idx_signatures_entity ON signatures (entity_type, entity_id);

Recommended (optional) Row-Level Security (RLS)
If you want “absolute data isolation by Project ID”, enable PostgreSQL RLS and set app.current_project_id at session level,
then enforce project_id = current_setting('app.current_project_id')::uuid on all project-scoped tables.

4) Assumptions & open questions
Strict multi-tenancy is enforced by project_id on almost all transactional tables and by recommended RLS.
Organizations are either customer or supplier (an org cannot be both in MVP).
Second Chance is modeled as quotes.revision_no (1..N); you may also want an rfq_events table later.
Supplier anonymization is application-layer (mask identity in responses); DB still stores supplier_org_id for integrity. If you require DB-level anonymization, add a surrogate rfq_supplier_aliases table with random aliases per RFQ.
“Market average price” is not modeled yet (PRD open question); if needed, add market_prices with source + effective dates.
Partial deliveries / partial fulfillment: schema allows multiple deliveries per order; business rules can restrict if MVP wants single delivery only.
Budget utilization: current schema stores planned budget. Actual spend can be derived from accepted orders/invoices; if you need fast dashboards, add aggregated materialized views.
Anti-leakage filtering: stored via messages.is_blocked + reason; if you want full audit, add message_moderation_events.
Onboarding ZIP: stored as individual docs; if you need ZIP artifact tracking, add onboarding_packages with a generated storage_url.

If you want, I can also produce a migration-ready version (001_init.sql) with:
citext extension enablement
updated_at trigger function for all tables
stricter CHECKs for “supplier/customer org must match type” (enforced via triggers)

