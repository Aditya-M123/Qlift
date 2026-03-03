# qlift/target/__init__.py

from qlift.target.ta01a.adapter import TargetAdapter
from qlift.target.ta01a.schemas import ColumnProfile, TableProfile

__all__ = [
    "TargetAdapter",
    "TableProfile",
    "ColumnProfile",
]