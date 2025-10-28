from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import re
from ..schemas.material import MaterialIn
from ..schemas.flow import ProcessPacket


def _canon(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _token_set_ratio(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union


def _best_match(
    query: str, candidates: List[Tuple[str, str]]
) -> Tuple[Optional[str], float]:
    cq = _canon(query)
    best_name, best_score = None, 0.0
    for disp, cc in candidates:
        score = _token_set_ratio(cq, cc)
        if score > best_score:
            best_name, best_score = disp, score
    return best_name, best_score


def match_components_to_materials(
    packets: List[ProcessPacket],
    materials: List[MaterialIn],
    cfg: Dict,
    min_score: float = 0.55,
) -> Dict[str, List[Dict]]:
    """
    Annotate ComponentIn with material suggestions:
      - exact via hardcode_map
      - synonym normalization
      - token-set similarity against polymer_type / description / common_applications
    Returns a report with unmatched / low-confidence items per material_name (flow).
    """
    scfg = cfg["material_sheet"]
    synonyms: Dict[str, List[str]] = {
        k.lower(): [s.lower() for s in v]
        for k, v in (scfg.get("synonyms") or {}).items()
    }
    hard = {k.lower(): v for k, v in (scfg.get("hardcode_map") or {}).items()}

    cand: List[Tuple[str, str]] = []
    mat_names: set[str] = set()
    for m in materials:
        disp = m.polymer_type or m.description or m.cas_number or "unknown"
        mat_names.add(disp)
        blobs = " ".join(
            [
                _canon(m.polymer_type),
                _canon(m.description),
                _canon(m.common_applications),
                _canon(m.cas_number),
                _canon(m.sorting_guidelines),
            ]
        )
        cand.append((disp, blobs))

    for canonical, alts in synonyms.items():
        cand.append((canonical, _canon(canonical)))
        for a in alts:
            cand.append((canonical, _canon(a)))

    report: Dict[str, List[Dict]] = {}

    for p in packets:
        for fp in p.flows:
            key = fp.flow.material_name or "unknown"
            bucket = []
            for comp in fp.components:
                source = comp.polymer_name or comp.description
                if not source:
                    continue

                hc = hard.get(source.lower())
                if hc:
                    comp.material_name_suggested = hc
                    comp.material_match_score = 1.0
                    continue

                match, score = _best_match(source, cand)
                if match and score >= min_score:
                    comp.material_name_suggested = match
                    comp.material_match_score = round(score, 3)
                else:
                    bucket.append(
                        {
                            "component": source,
                            "suggestion": match,
                            "score": round(score, 3),
                        }
                    )
            if bucket:
                report.setdefault(key, []).extend(bucket)

    return report
