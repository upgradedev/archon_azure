-- Archon — Azure Database for PostgreSQL schema
-- Version: 1.0
--
-- Four concern areas, each with a single-responsibility table group:
--   1. Document registry   — tracks every uploaded and extracted document
--   2. Employee master      — built from payslip extraction, enriched over time
--   3. Payroll events       — links the three payroll doc subtypes per period
--   4. Validation results   — cross-document consistency audit trail

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Document registry
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id       TEXT NOT NULL,
    period          TEXT NOT NULL,
    source_file     TEXT NOT NULL,
    doc_type        TEXT NOT NULL,
    detected_lang   TEXT,
    issue_date      DATE,
    vendor_name     TEXT,
    vendor_tax_id   TEXT,
    recipient_name  TEXT,
    currency        CHAR(3) DEFAULT 'EUR',
    subtotal        NUMERIC(14,2),
    vat_amount      NUMERIC(14,2),
    vat_rate_pct    NUMERIC(5,2),
    total_amount    NUMERIC(14,2) NOT NULL,
    invoice_number  TEXT,
    confidence      NUMERIC(4,3),
    extraction_model TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_period ON documents (period);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents (doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_upload_id ON documents (upload_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Employee master
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_code   TEXT UNIQUE,
    full_name       TEXT,
    tax_id          TEXT,
    bank_account    TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS employee_payroll (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID REFERENCES employees(id) ON DELETE CASCADE,
    period          TEXT NOT NULL,
    gross_pay       NUMERIC(12,2),
    net_pay         NUMERIC(12,2) NOT NULL,
    employer_cost   NUMERIC(12,2),
    ika_employee    NUMERIC(12,2),
    ika_employer    NUMERIC(12,2),
    income_tax      NUMERIC(12,2),
    document_id     UUID REFERENCES documents(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (employee_id, period)
);

CREATE INDEX IF NOT EXISTS idx_employee_payroll_period ON employee_payroll (period);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Payroll events
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS payroll_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period                  TEXT NOT NULL,
    company_name            TEXT,
    bank_doc_id             UUID REFERENCES documents(id),
    register_doc_id         UUID REFERENCES documents(id),
    net_total               NUMERIC(12,2),
    gross_total             NUMERIC(12,2),
    employer_cost_total     NUMERIC(12,2),
    employee_count          INT,
    is_complete             BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ DEFAULT now(),
    UNIQUE (period, company_name)
);

CREATE TABLE IF NOT EXISTS payroll_event_payslips (
    payroll_event_id    UUID REFERENCES payroll_events(id) ON DELETE CASCADE,
    document_id         UUID REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (payroll_event_id, document_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Validation results
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS validation_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period              TEXT NOT NULL,
    upload_id           TEXT,
    rule                TEXT NOT NULL,
    passed              BOOLEAN NOT NULL,
    severity            TEXT NOT NULL,
    message             TEXT,
    source_files        TEXT[],
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_validation_period ON validation_results (period);
CREATE INDEX IF NOT EXISTS idx_validation_passed ON validation_results (passed);
