from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime, date

from sqlalchemy.orm import Session
from sqlalchemy import select

# ORM models
from ..db_models.process_kpis import (
    CollectionProcessKPI,
    SortingProcessKPI,
    RecyclingProcessKPI,
    CollectionFlowKPI,
)
from ..db_models.process import Process
from ..db_models.flows import (
    ProcessMaterialFlow,
    FlowSample,
    FlowSampleComponent,
)
from ..db_models.material import Material

# Schemas (packets built in Step 3)
from ..schemas.flow import (
    ProcessPacket,
    FlowSampleIn,
    CollectionFlowKPIIn,
)
from ..schemas.material import MaterialIn


# ---------- small helpers ----------


def _parse_date_maybe(s: Optional[str]) -> Optional[date]:
    """
    Accept common formats: dd.mm.yyyy, yyyy-mm-dd, dd/mm/yyyy
    Leave None if not parseable.
    """
    if not s or not str(s).strip():
        return None
    t = str(s).strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    return None


def _nonblank(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) and s.strip() else None


def _has_any(d: Optional[Dict[str, Any]]) -> bool:
    if not d:
        return False
    for v in d.values():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return True
    return False


def _extract_process_kpi(packet: "ProcessPacket") -> Tuple[Optional[str], Any]:
    """
    Return (kind, kpi_obj) where kind in {'collection','sorting','recycling'} or (None, None).

    Supports either:
      - packet.collection_kpi / sorting_kpi / recycling_kpi
      - or packet.process_kpi (single union), detected by field names on the object
    """
    k = getattr(packet, "collection_kpi", None)
    if k is not None:
        return "collection", k
    k = getattr(packet, "sorting_kpi", None)
    if k is not None:
        return "sorting", k
    k = getattr(packet, "recycling_kpi", None)
    if k is not None:
        return "recycling", k

    # unified field variant
    k = getattr(packet, "process_kpi", None)
    if k is None:
        return None, None

    if hasattr(k, "collection_rate_amount"):
        return "collection", k
    if hasattr(k, "sorting_yield_amount"):
        return "sorting", k
    if hasattr(k, "recycling_yield_amount"):
        return "recycling", k

    return None, None


# ---------- materials upsert & lookup ----------


def upsert_materials(session: Session, rows: Iterable[MaterialIn]) -> Tuple[int, int]:
    """
    Insert new / update changed materials keyed by (polymer_type).
    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0

    # build current index by polymer_type (case-insensitive)
    existing = {
        (m.polymer_type or "").strip().lower(): m
        for m in session.scalars(select(Material)).all()
    }

    for rec in rows:
        key = (rec.polymer_type or "").strip().lower()
        if not key:
            # skip records without a polymer_type anchor
            continue

        cur = existing.get(key)
        payload = rec.model_dump(exclude_none=True)

        if cur is None:
            session.add(Material(**payload))
            inserted += 1
        else:
            # Update only if any field differs (simple compare)
            changed = False
            for k, v in payload.items():
                if getattr(cur, k) != v:
                    setattr(cur, k, v)
                    changed = True
            if changed:
                updated += 1

    return inserted, updated


def build_material_name_to_id(session: Session) -> Dict[str, int]:
    """
    Map polymer_type (lowercased) -> material_id for quick resolution.
    """
    out: Dict[str, int] = {}
    for m in session.scalars(select(Material)).all():
        if m.polymer_type:
            out[m.polymer_type.strip().lower()] = m.material_id
    return out


# ---------- core load ----------


class LoadOptions:
    def __init__(
        self,
        replace_process_by_name: bool = False,
        materials: Optional[List[MaterialIn]] = None,
        auto_create_materials: bool = False,
        min_match_score: float = 0.55,
    ) -> None:
        self.replace_process_by_name = replace_process_by_name
        self.materials = materials or []
        self.auto_create_materials = auto_create_materials
        self.min_match_score = min_match_score


class LoadResult:
    def __init__(self) -> None:
        self.counts: Dict[str, int] = {
            "process": 0,
            "process_material_flow": 0,
            "collection_process_kpi": 0,
            "sorting_process_kpi": 0,
            "recycling_process_kpi": 0,
            "collection_flow_kpi": 0,
            "flow_sample": 0,
            "flow_sample_component": 0,
            "material_inserted": 0,
            "material_updated": 0,
        }
        self.components_without_material: List[Tuple[str, str]] = (
            []
        )  # [(flow_material_name, component_polymer_name)]


def load_packets(
    session: Session, packets: List[ProcessPacket], opts: LoadOptions
) -> LoadResult:
    """
    Insert the Process sheet + MFA structures produced by Step 3 into DB.
    Assumes basic validation was already performed.
    """
    res = LoadResult()

    # 0) Optional materials upsert (one-time generally)
    if opts.materials:
        ins, upd = upsert_materials(session, opts.materials)
        res.counts["material_inserted"] += ins
        res.counts["material_updated"] += upd

    # material lookup map (by polymer_type)
    mat_name_to_id = build_material_name_to_id(session)

    # 1) One process per sheet (your builder currently produces 1 packet)
    for packet in packets:
        # replace option: delete existing process by (name) to avoid duplicates
        if opts.replace_process_by_name and packet.process.process_name:
            existing_proc = session.scalar(
                select(Process).where(
                    Process.process_name == packet.process.process_name
                )
            )
            if existing_proc is not None:
                # ON DELETE CASCADE ensures children go away
                session.delete(existing_proc)
                session.flush()

        # 1a) Insert process-level KPI (if present in packet.process_kpi)
        process_kpi_id: Optional[int] = None
        kpi_table: Optional[str] = None

        kind, k = _extract_process_kpi(packet)
        if (
            packet.process.process_type == "Collection"
            and kind == "collection"
            and k is not None
        ):
            obj = CollectionProcessKPI(
                collection_rate_amount=k.collection_rate_amount,
                amount_unit=_nonblank(getattr(k, "amount_unit", None)),
                reference_text=_nonblank(getattr(k, "reference_text", None)),
            )
            session.add(obj)
            session.flush()
            res.counts["collection_process_kpi"] += 1
            process_kpi_id = obj.process_kpi_id
            kpi_table = "collection"

        elif (
            packet.process.process_type == "Sorting"
            and kind == "sorting"
            and k is not None
        ):
            obj = SortingProcessKPI(
                sorting_yield_amount=k.sorting_yield_amount,
                amount_unit=_nonblank(getattr(k, "amount_unit", None)),
                reference_text=_nonblank(getattr(k, "reference_text", None)),
            )
            session.add(obj)
            session.flush()
            res.counts["sorting_process_kpi"] += 1
            process_kpi_id = obj.process_kpi_id
            kpi_table = "sorting"

        elif (
            packet.process.process_type == "Recycling"
            and kind == "recycling"
            and k is not None
        ):
            obj = RecyclingProcessKPI(
                recycling_yield_amount=k.recycling_yield_amount,
                amount_unit=_nonblank(getattr(k, "amount_unit", None)),
                reference_text=_nonblank(getattr(k, "reference_text", None)),
            )
            session.add(obj)
            session.flush()
            res.counts["recycling_process_kpi"] += 1
            process_kpi_id = obj.process_kpi_id
            kpi_table = "recycling"

        # 1b) Insert process
        proc = Process(
            process_name=packet.process.process_name,
            process_type=packet.process.process_type,  # trigger enforces consistency
            collection_process_kpi_id=(
                process_kpi_id if kpi_table == "collection" else None
            ),
            sorting_process_kpi_id=process_kpi_id if kpi_table == "sorting" else None,
            recycling_process_kpi_id=(
                process_kpi_id if kpi_table == "recycling" else None
            ),
        )
        session.add(proc)
        session.flush()
        res.counts["process"] += 1

        # 2) Insert flows + MFA bits
        for fp in packet.flows:
            flow = ProcessMaterialFlow(
                process_id=proc.process_id,
                direction=fp.flow.direction,
                material_name=_nonblank(fp.flow.material_name),
                amount_value=fp.flow.amount_value,
                amount_unit=_nonblank(fp.flow.amount_unit),
                reference_text=_nonblank(fp.flow.reference_text),
            )
            session.add(flow)
            session.flush()
            res.counts["process_material_flow"] += 1

            # 2a) Flow KPI (collection only, for now)
            flow_kpi_id: Optional[int] = None
            if fp.collection_kpi is not None and _has_any(
                fp.collection_kpi.model_dump(exclude_none=True)
            ):
                ck: CollectionFlowKPIIn = fp.collection_kpi
                ck_obj = CollectionFlowKPI(
                    purity_amount=ck.purity_amount,
                    purity_unit=_nonblank(ck.purity_unit),
                    attached_moisture_and_dirt_amount_value=ck.attached_moisture_and_dirt_amount_value,
                    attached_moisture_and_dirt_amount_unit=_nonblank(
                        ck.attached_moisture_and_dirt_amount_unit
                    ),
                    npp_share_amount_value=ck.npp_share_amount_value,
                    npp_share_amount_unit=_nonblank(ck.npp_share_amount_unit),
                    residual_waste_share_amount_value=ck.residual_waste_share_amount_value,
                    residual_waste_share_amount_unit=_nonblank(
                        ck.residual_waste_share_amount_unit
                    ),
                    eps_items_amount_value=ck.eps_items_amount_value,
                    eps_items_amount_unit=_nonblank(ck.eps_items_amount_unit),
                )
                session.add(ck_obj)
                session.flush()
                res.counts["collection_flow_kpi"] += 1
                flow_kpi_id = ck_obj.flow_kpi_id

            # 2b) Flow sample
            if fp.sample is not None and _has_any(
                fp.sample.model_dump(exclude_none=True)
            ):
                s: FlowSampleIn = fp.sample
                sample = FlowSample(
                    material_flow_id=flow.material_flow_id,
                    collection_flow_kpi_id=flow_kpi_id,
                    stakeholder_name=_nonblank(s.stakeholder_name),
                    sample_date=_parse_date_maybe(s.sample_date),
                    contamination=s.contamination,
                    contamination_unit=_nonblank(s.contamination_unit),
                    moisture_condition=_nonblank(s.moisture_condition),
                    density=s.density,
                    density_unit=_nonblank(s.density_unit),
                    carbon_content_pct=s.carbon_content_pct,
                    nitrogen_content_pct=s.nitrogen_content_pct,
                    hydrogen_content_pct=s.hydrogen_content_pct,
                    phosphorus_content_pct=s.phosphorus_content_pct,
                    oxygen_content_pct=s.oxygen_content_pct,
                    color=_nonblank(s.color),
                    amount_value=s.amount_value,
                    amount_unit=_nonblank(s.amount_unit),
                )
                session.add(sample)
                session.flush()
                res.counts["flow_sample"] += 1

                # 2c) Components for the sample
                for comp in fp.components:
                    # Try to resolve material_id from the suggested material name (created in Step 3)
                    mat_id: Optional[int] = None
                    if comp.material_name_suggested:
                        mat_id = mat_name_to_id.get(
                            comp.material_name_suggested.strip().lower()
                        )

                        # optionally auto-create a material entry if not found
                        if mat_id is None and opts.auto_create_materials:
                            new_m = Material(polymer_type=comp.material_name_suggested)
                            session.add(new_m)
                            session.flush()
                            mat_id = new_m.material_id
                            mat_name_to_id[
                                comp.material_name_suggested.strip().lower()
                            ] = mat_id

                    if mat_id is None and comp.polymer_name:
                        # also try direct polymer_name if not suggested
                        mat_id = mat_name_to_id.get(comp.polymer_name.strip().lower())

                    # record unresolved for the report
                    if mat_id is None and (comp.polymer_name or comp.description):
                        res.components_without_material.append(
                            (
                                fp.flow.material_name or "?",
                                comp.polymer_name or comp.description or "?",
                            )
                        )

                    row = FlowSampleComponent(
                        sample_id=sample.sample_id,
                        material_id=mat_id,
                        polymer_name=_nonblank(comp.polymer_name),
                        description=_nonblank(comp.description),
                        amount_value=comp.amount_value,
                        amount_unit=_nonblank(comp.amount_unit),
                    )
                    session.add(row)
                    res.counts["flow_sample_component"] += 1

    return res
