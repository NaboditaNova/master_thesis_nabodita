from __future__ import annotations
from typing import Dict, List
from ..schemas.process import ProcessIn
from ..schemas.flow import FlowIn, FlowPacket, ProcessPacket


def build_packets_from_process_dict(d: Dict) -> List[ProcessPacket]:
    pinfo = d["process"]
    process = ProcessIn(
        rownum=1,
        process_name=pinfo.get("process_name"),
        process_type=pinfo["process_type"],
        collection_rate_amount=(
            pinfo["kpi"].get("collection_rate_amount")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "collection_process_kpi"
            else None
        ),
        collection_rate_unit=(
            pinfo["kpi"].get("amount_unit")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "collection_process_kpi"
            else None
        ),
        collection_reference_text=(
            pinfo["kpi"].get("reference_text")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "collection_process_kpi"
            else None
        ),
        sorting_yield_amount=(
            pinfo["kpi"].get("sorting_yield_amount")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "sorting_process_kpi"
            else None
        ),
        sorting_yield_unit=(
            pinfo["kpi"].get("amount_unit")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "sorting_process_kpi"
            else None
        ),
        sorting_reference_text=(
            pinfo["kpi"].get("reference_text")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "sorting_process_kpi"
            else None
        ),
        recycling_yield_amount=(
            pinfo["kpi"].get("recycling_yield_amount")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "recycling_process_kpi"
            else None
        ),
        recycling_yield_unit=(
            pinfo["kpi"].get("amount_unit")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "recycling_process_kpi"
            else None
        ),
        recycling_reference_text=(
            pinfo["kpi"].get("reference_text")
            if pinfo.get("kpi") and pinfo["kpi"]["table"] == "recycling_process_kpi"
            else None
        ),
    )

    flow_packets: List[FlowPacket] = []
    for idx, f in enumerate(d["flows"], start=1):
        fin = FlowIn(
            rownum=idx,
            direction=f["direction"],
            material_name=f.get("material_name"),
            amount_value=f.get("amount_value"),
            amount_unit=f.get("amount_unit"),
            reference_text=f.get("reference_text"),
        )
        flow_packets.append(FlowPacket(flow=fin, sample=None, components=[]))

    return [ProcessPacket(process=process, flows=flow_packets)]
