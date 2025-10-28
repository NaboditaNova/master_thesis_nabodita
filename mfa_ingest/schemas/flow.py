from __future__ import annotations
from .process import ProcessIn
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

Direction = Literal["Input", "Output"]


def _blank_to_none(v):
    if isinstance(v, str) and not v.strip():
        return None
    return v


def _to_float_or_none(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    # handle German decimal comma
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Invalid number: {v!r}")


def _keep_text_or_none(v):
    # Keep textual values as-is (used for ComponentIn.amount_value which is VARCHAR(20) in DB)
    if v is None:
        return None
    s = str(v).strip()
    return s or None


class FlowIn(BaseModel):
    rownum: int
    direction: Direction
    material_name: Optional[str] = None
    amount_value: Optional[float] = None
    amount_unit: Optional[str] = None
    reference_text: Optional[str] = None

    _n = field_validator(
        "material_name", "amount_unit", "reference_text", mode="before"
    )(_blank_to_none)
    _f = field_validator("amount_value", mode="before")(_to_float_or_none)


class FlowSampleIn(BaseModel):
    rownum: int
    stakeholder_name: Optional[str] = None
    sample_date: Optional[str] = None  # keep as string; DB DATE parse happens later
    contamination: Optional[float] = None
    contamination_unit: Optional[str] = None
    moisture_condition: Optional[str] = None
    density: Optional[float] = None
    density_unit: Optional[str] = None
    carbon_content_pct: Optional[float] = None
    nitrogen_content_pct: Optional[float] = None
    hydrogen_content_pct: Optional[float] = None
    phosphorus_content_pct: Optional[float] = None
    oxygen_content_pct: Optional[float] = None
    color: Optional[str] = None
    amount_value: Optional[float] = None
    amount_unit: Optional[str] = None

    _n = field_validator(
        "stakeholder_name",
        "contamination_unit",
        "moisture_condition",
        "density_unit",
        "color",
        "amount_unit",
        mode="before",
    )(_blank_to_none)

    _f = field_validator(
        "contamination",
        "density",
        "carbon_content_pct",
        "nitrogen_content_pct",
        "hydrogen_content_pct",
        "phosphorus_content_pct",
        "oxygen_content_pct",
        "amount_value",
        mode="before",
    )(_to_float_or_none)


class ComponentIn(BaseModel):
    rownum: int
    polymer_name: Optional[str] = None
    description: Optional[str] = None
    amount_value: Optional[str] = None
    amount_unit: Optional[str] = None
    # NEW: material linking hints (not DB columns)
    material_name_suggested: Optional[str] = None
    material_match_score: Optional[float] = None

    _n = field_validator("polymer_name", "description", "amount_unit", mode="before")(
        _blank_to_none
    )
    # _f = field_validator("amount_value", mode="before")(_to_float_or_none)
    # Keep the original text; do NOT coerce to float here
    _t = field_validator("amount_value", mode="before")(_keep_text_or_none)


class CollectionFlowKPIIn(BaseModel):
    purity_amount: Optional[float] = None
    purity_unit: Optional[str] = None
    attached_moisture_and_dirt_amount_value: Optional[float] = None
    attached_moisture_and_dirt_amount_unit: Optional[str] = None
    npp_share_amount_value: Optional[float] = None
    npp_share_amount_unit: Optional[str] = None
    residual_waste_share_amount_value: Optional[float] = None
    residual_waste_share_amount_unit: Optional[str] = None
    eps_items_amount_value: Optional[float] = None
    eps_items_amount_unit: Optional[str] = None


class SortingFlowKPIIn(BaseModel):
    maximum_total_amount_of_impurities_amount: float | None = None
    maximum_total_amount_of_impurities_unit: str | None = None
    purity_amount: float | None = None
    purity_unit: str | None = None
    other_metal_items_amount: float | None = None
    other_metal_items_unit: str | None = None
    other_plastics_items_amount: float | None = None
    other_plastics_items_unit: str | None = None
    ppk_amount: float | None = None
    ppk_unit: str | None = None
    eps_items_amount: float | None = None
    eps_items_unit: str | None = None
    pvc_items_amount: float | None = None
    pvc_items_unit: str | None = None
    colourless_transparent_foils_amount: float | None = None
    colourless_transparent_foils_unit: str | None = None
    yield_of_ds_from_input_amount: float | None = None
    yield_of_ds_from_input_unit: str | None = None


class RecyclingFlowKPIIn(BaseModel):
    filtration_amount: float | None = None
    filtration_unit: str | None = None
    recyclate_polymer_purity_amount: float | None = None
    recyclate_polymer_purity_unit: str | None = None
    pcr_content_amount: float | None = None
    pcr_content_unit: str | None = None
    melt_flow_rate_amount: float | None = None
    melt_flow_rate_unit: str | None = None
    ash_content_amount: float | None = None
    ash_content_unit: str | None = None
    tensile_modulus_amount: float | None = None
    tensile_modulus_unit: str | None = None
    tensile_strength_amount: float | None = None
    tensile_strength_unit: str | None = None
    chapry_notch_impact_strength_amount: float | None = None
    chapry_notch_impact_strength_unit: str | None = None
    yield_flow_sample_amount: float | None = None
    yield_flow_sample_unit: str | None = None


# Higher-level grouping that the loader will consume
class ProcessPacket(BaseModel):
    process: "ProcessIn"
    flows: list["FlowPacket"]


class FlowPacket(BaseModel):
    flow: "FlowIn"
    sample: Optional["FlowSampleIn"] = None
    components: list["ComponentIn"] = Field(default_factory=list)
    collection_kpi: Optional["CollectionFlowKPIIn"] = None
    sorting_kpi: Optional["SortingFlowKPIIn"] = None
    recycling_kpi: Optional["RecyclingFlowKPIIn"] = None


# forward refs
ProcessPacket.model_rebuild()
FlowPacket.model_rebuild()
