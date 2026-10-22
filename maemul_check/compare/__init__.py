"""항목별 비교 함수. 모두 순수 함수이며 ItemResult 를 돌려준다."""
from .address import compare_address
from .area import compare_area
from .date import compare_approval
from .floors import compare_floors
from .parking import compare_parking
from .purpose import compare_kind

__all__ = [
    "compare_address",
    "compare_approval",
    "compare_area",
    "compare_floors",
    "compare_kind",
    "compare_parking",
]
