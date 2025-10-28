from __future__ import annotations
from typing import List
from ..schemas.flow import ProcessPacket


class Issue:
    def __init__(self, sheet: str, rownum: int, message: str):
        self.sheet = sheet
        self.rownum = rownum
        self.message = message

    def __repr__(self):
        return f"[{self.sheet} row {self.rownum}] {self.message}"


def _pair(value, unit) -> bool:
    return (
        value is None and (unit is None or (isinstance(unit, str) and not unit.strip()))
    ) or (value is not None and (unit is not None and str(unit).strip() != ""))


def validate_packets(packets: List[ProcessPacket]) -> List[Issue]:
    issues: List[Issue] = []

    for p in packets:
        proc = p.process
        if proc.collection_rate_amount is not None and not proc.collection_rate_unit:
            issues.append(
                Issue(
                    "Process",
                    proc.rownum,
                    "collection_rate_amount provided but unit missing",
                )
            )

        for fp in p.flows:
            f = fp.flow
            if f.amount_value is not None and not f.amount_unit:
                issues.append(
                    Issue(
                        "Flows",
                        f.rownum,
                        "flow amount_value provided but amount_unit missing",
                    )
                )

            if fp.sample:
                s = fp.sample
                if s.contamination is not None and not s.contamination_unit:
                    issues.append(
                        Issue(
                            "Flow Sample",
                            s.rownum,
                            "contamination provided but contamination_unit missing",
                        )
                    )
                if s.density is not None and not s.density_unit:
                    issues.append(
                        Issue(
                            "Flow Sample",
                            s.rownum,
                            "density provided but density_unit missing",
                        )
                    )
                if s.amount_value is not None and not s.amount_unit:
                    issues.append(
                        Issue(
                            "Flow Sample",
                            s.rownum,
                            "sample amount_value provided but amount_unit missing",
                        )
                    )

                for name in (
                    "carbon_content_pct",
                    "nitrogen_content_pct",
                    "hydrogen_content_pct",
                    "phosphorus_content_pct",
                    "oxygen_content_pct",
                ):
                    v = getattr(s, name)
                    if v is not None and not (0.0 <= v <= 100.0):
                        issues.append(
                            Issue(
                                "Flow Sample", s.rownum, f"{name} out of range [0,100]"
                            )
                        )

            if getattr(fp, "collection_kpi", None):
                k = fp.collection_kpi
                if k is not None:

                    def _pair_ok(val, unit):
                        return (
                            val is None
                            and (
                                unit is None
                                or (isinstance(unit, str) and not unit.strip())
                            )
                        ) or (
                            val is not None
                            and unit is not None
                            and str(unit).strip() != ""
                        )

                    pairs = [
                        ("purity_amount", k.purity_amount, k.purity_unit),
                        (
                            "attached_moisture_and_dirt_amount_value",
                            k.attached_moisture_and_dirt_amount_value,
                            k.attached_moisture_and_dirt_amount_unit,
                        ),
                        (
                            "npp_share_amount_value",
                            k.npp_share_amount_value,
                            k.npp_share_amount_unit,
                        ),
                        (
                            "residual_waste_share_amount_value",
                            k.residual_waste_share_amount_value,
                            k.residual_waste_share_amount_unit,
                        ),
                        (
                            "eps_items_amount_value",
                            k.eps_items_amount_value,
                            k.eps_items_amount_unit,
                        ),
                    ]
                    any_value = False
                    for name, val, unit in pairs:
                        if val is not None:
                            any_value = True
                        if not _pair_ok(val, unit):
                            issues.append(
                                Issue(
                                    "MFA (Collection KPI)",
                                    0,
                                    f"{name} provided but unit missing",
                                )
                            )

                    if not any_value:
                        issues.append(
                            Issue(
                                "MFA (Collection KPI)",
                                0,
                                "KPI object present but no values provided",
                            )
                        )

            for c in fp.components:
                if c.amount_value is not None and not c.amount_unit:
                    issues.append(
                        Issue(
                            "Component",
                            c.rownum,
                            "component amount_value provided but amount_unit missing",
                        )
                    )
                if not any(
                    [
                        c.polymer_name and c.polymer_name.strip(),
                        c.description and c.description.strip(),
                        c.amount_value is not None,
                        c.amount_unit and c.amount_unit.strip(),
                    ]
                ):
                    issues.append(
                        Issue(
                            "Component",
                            c.rownum,
                            "component must have at least one identifying/value field",
                        )
                    )

    return issues
