from __future__ import annotations
from typing import Dict, List, Tuple
from ..schemas.flow import (
    FlowPacket,
    ProcessPacket,
    FlowSampleIn,
    ComponentIn,
    CollectionFlowKPIIn,
    SortingFlowKPIIn,
    RecyclingFlowKPIIn,
)
from ..schemas.process import ProcessType


def _blank(v):
    return v in (None, "", []) or (isinstance(v, str) and not v.strip())


def _has_any(d: dict) -> bool:
    return any((not _blank(v)) for v in d.values())


def _payload_has_data(payload: Dict) -> bool:
    if _has_any(payload.get("sample") or {}):
        return True
    if _has_any(payload.get("collection_kpi") or {}):
        return True
    if _has_any(payload.get("sorting_kpi") or {}):
        return True
    if _has_any(payload.get("recycling_kpi") or {}):
        return True
    if payload.get("components"):
        return True
    return False


# def merge_mfa_into_packets(packets: List[ProcessPacket], per_material: Dict[str, Dict]) -> None:
#     """
#     Mutates packets in-place:
#       - attaches FlowSampleIn if any sample field provided
#       - attaches CollectionFlowKPIIn if any KPI field provided
#       - appends ComponentIn rows
#     Matching is by exact material_name (case-insensitive).
#     """
#     # Build a lookup from flow material_name (lower) -> FlowPacket
#     flow_lookup: Dict[str, List] = {}
#     for p in packets:
#         for fp in p.flows:
#             key = (fp.flow.material_name or "").strip().lower()
#             flow_lookup.setdefault(key, []).append(fp)

#     for mat_name, payload in per_material.items():
#         key = (mat_name or "").strip().lower()
#         if not key or key not in flow_lookup:
#             continue  # ignore materials that are not part of this process

#         for fp in flow_lookup[key]:
#             # sample
#             sample_d = payload.get("sample") or {}
#             if _has_any(sample_d):
#                 fp.sample = FlowSampleIn(rownum=0, **sample_d)

#             # collection KPI
#             kpi_d = payload.get("collection_kpi")
#             if kpi_d and _has_any(kpi_d):
#                 fp.collection_kpi = CollectionFlowKPIIn(**kpi_d)

#             # components
#             comps = payload.get("components") or []
#             for c in comps:
#                 # Only if any of description/amount/unit present (polymer_name can be alone but rule said skip if D/A/U all empty)
#                 if not _blank(c.get("description")) or (c.get("amount_value") is not None) or not _blank(c.get("amount_unit")):
#                     fp.components.append(ComponentIn(rownum=0, **c))


def merge_mfa_into_packets(
    packets: List[ProcessPacket], per_material: Dict[str, Dict]
) -> List[str]:
    """
    Mutates packets in-place; returns list of MFA material names that didn't match any flow
    but contained data (likely a column-name typo).
    """
    # flow lookup
    # Build a lookup: flow_name(lower) -> list of (FlowPacket, process_type)
    flow_lookup: Dict[str, List[Tuple[FlowPacket, ProcessType]]] = {}
    for p in packets:
        ptype: ProcessType = (
            p.process.process_type
        )  # "Collection" | "Sorting" | "Recycling"
        for fp in p.flows:
            key = (fp.flow.material_name or "").strip().lower()
            flow_lookup.setdefault(key, []).append((fp, ptype))

    unmatched: List[str] = []

    for mat_name, payload in per_material.items():
        key = (mat_name or "").strip().lower()
        if key and key in flow_lookup:
            for fp, ptype in flow_lookup[key]:
                # Sample
                sample_d = payload.get("sample") or {}
                if _has_any(sample_d):
                    fp.sample = FlowSampleIn(rownum=0, **sample_d)

                # KPI: choose by process type
                if ptype == "Collection":
                    kpi_d = payload.get("collection_kpi") or {}
                    if _has_any(kpi_d):
                        fp.collection_kpi = CollectionFlowKPIIn(**kpi_d)
                    # clear others for safety
                    fp.sorting_kpi = None
                    fp.recycling_kpi = None

                elif ptype == "Sorting":
                    kpi_d = payload.get("sorting_kpi") or {}
                    if _has_any(kpi_d):
                        fp.sorting_kpi = SortingFlowKPIIn(**kpi_d)
                    fp.collection_kpi = None
                    fp.recycling_kpi = None

                elif ptype == "Recycling":
                    kpi_d = payload.get("recycling_kpi") or {}
                    if _has_any(kpi_d):
                        fp.recycling_kpi = RecyclingFlowKPIIn(**kpi_d)
                    fp.collection_kpi = None
                    fp.sorting_kpi = None

                # Components
                comps = payload.get("components") or []
                for c in comps:
                    if (
                        not _blank(c.get("description"))
                        or (c.get("amount_value") is not None)
                        or not _blank(c.get("amount_unit"))
                        or not _blank(c.get("polymer_name"))
                    ):
                        fp.components.append(ComponentIn(rownum=0, **c))
        else:
            if _payload_has_data(payload):
                unmatched.append(mat_name)

    return unmatched
