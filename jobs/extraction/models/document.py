from enum import Enum
from pydantic import BaseModel


class DocType(str, Enum):
    INVOICE = "invoice"
    SALES = "sales"
    EXPENSE = "expense"
    PAYROLL_REGISTER = "payroll_register"
    BANK_CONFIRMATION = "bank_confirmation"
    PAYSLIP = "payslip"
    PAYROLL = "payroll"
    ACCOUNT_STATEMENT = "account_statement"
    UNKNOWN = "unknown"


class VatTreatment(str, Enum):
    STANDARD = "standard"
    REVERSE_CHARGE = "reverse_charge"
    EXEMPT = "exempt"
    ZERO_RATE = "zero_rate"
    NONE = "none"


class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    total: float


class ExtractedDocument(BaseModel):
    source_file: str
    doc_type: DocType
    detected_language: str
    issue_date: str | None
    vendor_name: str | None
    vendor_tax_id: str | None
    recipient_name: str | None
    currency: str
    original_currency: str | None = None
    original_amount: float | None = None
    subtotal: float | None
    vat_amount: float | None
    vat_rate_pct: float | None
    vat_treatment: VatTreatment | None = None
    total_amount: float
    line_items: list[LineItem]
    payment_due_date: str | None
    invoice_number: str | None
    notes: str | None
    raw_text_excerpt: str
    extraction_model: str
    confidence: float

    # Payroll-specific fields
    employee_count: int | None = None
    gross_pay_total: float | None = None
    employer_cost_total: float | None = None
    net_pay_total: float | None = None
    employee_name: str | None = None
    employee_code: str | None = None

    # Account statement fields
    statement_balance: float | None = None
    statement_overdue: float | None = None
    statement_entries: list[dict] | None = None
