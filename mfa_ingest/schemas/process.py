from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Literal, Optional

ProcessType = Literal["Collection", "Sorting", "Recycling"]


class ProcessIn(BaseModel):
    rownum: int
    process_name: Optional[str] = None
    process_type: ProcessType

    # Optional process-level KPIs captured from sheet (if present)
    collection_rate_amount: Optional[float] = None
    collection_rate_unit: Optional[str] = None
    collection_reference_text: Optional[str] = None
    sorting_yield_amount: Optional[float] = None
    sorting_yield_unit: Optional[str] = None
    sorting_reference_text: Optional[str] = None
    recycling_yield_amount: Optional[float] = None
    recycling_yield_unit: Optional[str] = None
    recycling_reference_text: Optional[str] = None

    @field_validator("process_name", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v
