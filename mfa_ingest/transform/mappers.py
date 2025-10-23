from __future__ import annotations
from typing import Dict, List, Literal, cast
import pandas as pd
from ..extract.excel_reader import WorkbookFrames, pick_columns
from ..schemas.process import ProcessIn
from ..schemas.flow import FlowIn, FlowSampleIn, ComponentIn, ProcessPacket, FlowPacket

ProcessType = Literal["Collection", "Sorting", "Recycling"]


def _first_present(df: pd.DataFrame, mapping: Dict[str, list[str]], key: str):
    col, series = pick_columns(df, mapping.get(key, []))
    return col


def map_all(wb: WorkbookFrames, cfg: Dict) -> List[ProcessPacket]:
    """Return a list of ProcessPacket, each with child flows/samples/components."""
    mp_proc = cfg["mapping"]["process"]["columns"]
    mp_flow = cfg["mapping"]["flows"]["columns"]
    mp_sample = cfg["mapping"]["flow_sample"]["columns"]
    mp_comp = cfg["mapping"]["flow_sample_component"]["columns"]

    dfp = wb.get("process")
    dff = wb.get("flows")

    # Resolve columns once (normalized)
    P = {k: _first_present(dfp, mp_proc, k) for k in mp_proc.keys()}
    F = {k: _first_present(dff, mp_flow, k) for k in mp_flow.keys()}

    # Optional: you may have the sample/component data on the same flows sheet; if separate, read those as wb.get("...").
    S = {k: _first_present(dff, mp_sample, k) for k in mp_sample.keys()}
    C = {k: _first_present(dff, mp_comp, k) for k in mp_comp.keys()}

    packets: List[ProcessPacket] = []

    # For simplicity, pair each process row with all following flow rows until next process marker;
    # If your workbook links flows to process by a key/column, adjust this join accordingly.
    # Here, we do a cartesian-by-row-index example: 1 process → all flows (adjust if needed).
    for _, prow in dfp.iterrows():
        ptype_raw = (prow.get("process_type") or "").strip()
        if ptype_raw not in ("Collection", "Sorting", "Recycling"):
            raise ValueError(f"Invalid process_type: {ptype_raw!r}")
        ptype = cast(ProcessType, ptype_raw)
        p = ProcessIn(
            rownum=int(prow["__row__"]),
            process_name=(
                prow.get(P.get("process_name")) if P.get("process_name") else None
            ),
            process_type=ptype,
            collection_rate_amount=_try_float(
                prow.get(P.get("collection_rate_amount"))
            ),
            collection_rate_unit=_nz(prow.get(P.get("collection_rate_unit"))),
            sorting_yield_amount=_try_float(prow.get(P.get("sorting_yield_amount"))),
            sorting_yield_unit=_nz(prow.get(P.get("sorting_yield_unit"))),
            recycling_yield_amount=_try_float(
                prow.get(P.get("recycling_yield_amount"))
            ),
            recycling_yield_unit=_nz(prow.get(P.get("recycling_yield_unit"))),
        )

        flow_packets: List[FlowPacket] = []
        for _, frow in dff.iterrows():
            # Flow
            f = FlowIn(
                rownum=int(frow["__row__"]),
                direction=_nz(frow.get(F.get("direction"))) or "Input",
                material_name=_nz(frow.get(F.get("material_name"))),
                amount_value=_try_float(frow.get(F.get("amount_value"))),
                amount_unit=_nz(frow.get(F.get("amount_unit"))),
                reference_text=_nz(frow.get(F.get("reference_text"))),
            )

            # Sample (optional)
            s = FlowSampleIn(
                rownum=int(frow["__row__"]),
                stakeholder_name=_nz(frow.get(S.get("stakeholder_name"))),
                sample_date=_nz(frow.get(S.get("sample_date"))),
                contamination=_try_float(frow.get(S.get("contamination"))),
                contamination_unit=_nz(frow.get(S.get("contamination_unit"))),
                moisture_condition=_nz(frow.get(S.get("moisture_condition"))),
                density=_try_float(frow.get(S.get("density"))),
                density_unit=_nz(frow.get(S.get("density_unit"))),
                carbon_content_pct=_try_float(frow.get(S.get("carbon_content_pct"))),
                nitrogen_content_pct=_try_float(
                    frow.get(S.get("nitrogen_content_pct"))
                ),
                hydrogen_content_pct=_try_float(
                    frow.get(S.get("hydrogen_content_pct"))
                ),
                phosphorus_content_pct=_try_float(
                    frow.get(S.get("phosphorus_content_pct"))
                ),
                oxygen_content_pct=_try_float(frow.get(S.get("oxygen_content_pct"))),
                color=_nz(frow.get(S.get("color"))),
                amount_value=_try_float(frow.get(S.get("amount_value"))),
                amount_unit=_nz(frow.get(S.get("amount_unit"))),
            )

            # Components: minimal example assumes 1 component per row (extend if you have repeated columns)
            comp = ComponentIn(
                rownum=int(frow["__row__"]),
                polymer_name=_nz(frow.get(C.get("polymer_name"))),
                description=_nz(frow.get(C.get("description"))),
                amount_value=_try_float(frow.get(C.get("amount_value"))),
                amount_unit=_nz(frow.get(C.get("amount_unit"))),
            )
            comps = (
                [comp]
                if any(
                    [
                        comp.polymer_name,
                        comp.description,
                        comp.amount_value,
                        comp.amount_unit,
                    ]
                )
                else []
            )

            flow_packets.append(FlowPacket(flow=f, sample=s, components=comps))

        packets.append(ProcessPacket(process=p, flows=flow_packets))

    return packets


def _nz(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _try_float(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None
