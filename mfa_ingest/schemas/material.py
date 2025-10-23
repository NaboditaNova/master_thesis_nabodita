from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator


def _blank_to_none(v):
    if isinstance(v, str) and not v.strip():
        return None
    return v


class MaterialIn(BaseModel):
    polymer_type: Optional[str] = None
    description: Optional[str] = None
    chemical_formula: Optional[str] = None
    carbon_content: Optional[str] = None
    standard_density_kg_m3: Optional[str] = None
    density_reference: Optional[str] = None
    cas_number: Optional[str] = None
    color: Optional[str] = None
    common_applications: Optional[str] = None
    standardized_sorting_number: Optional[str] = None
    sorting_guidelines: Optional[str] = None
    din_spec_91446_comments: Optional[str] = None

    _n = field_validator(
        "polymer_type",
        "description",
        "chemical_formula",
        "carbon_content",
        "standard_density_kg_m3",
        "density_reference",
        "cas_number",
        "color",
        "common_applications",
        "standardized_sorting_number",
        "sorting_guidelines",
        "din_spec_91446_comments",
        mode="before",
    )(_blank_to_none)
