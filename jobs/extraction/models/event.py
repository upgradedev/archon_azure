from __future__ import annotations
from pydantic import BaseModel
from models.document import ExtractedDocument


class PayrollEvent(BaseModel):
    period: str
    company_name: str | None
    bank_confirmation: ExtractedDocument | None
    payroll_register: ExtractedDocument | None
    payslips: list[ExtractedDocument]
    is_complete: bool
