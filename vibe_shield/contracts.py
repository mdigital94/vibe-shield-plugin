"""Provider-neutral results. Missing usage is unknown, never zero."""
from dataclasses import dataclass
from typing import Dict, Optional

class ProviderError(Exception):
    """Safe, user-facing provider failure (never raw transport output)."""

@dataclass(frozen=True)
class ReviewResult:
    text: str
    model: Optional[str]
    usage: Dict[str, Optional[int]]
    complete: bool = True
    error: Optional[str] = None
    response_segments: int = 1
