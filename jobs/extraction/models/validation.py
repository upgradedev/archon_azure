from pydantic import BaseModel


class ValidationResult(BaseModel):
    rule: str
    passed: bool
    severity: str
    message: str
    source_files: list[str]
