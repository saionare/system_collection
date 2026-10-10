from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str | None = None
