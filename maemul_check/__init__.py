"""매물검수: 광고 명시사항 ↔ 건축물대장 대조."""
from .engine import verify
from .schema import AdInput, ItemResult, Report

__version__ = "0.1.0"
__all__ = ["AdInput", "ItemResult", "Report", "verify"]
