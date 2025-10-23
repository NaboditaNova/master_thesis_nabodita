from __future__ import annotations
from typing import Dict, List, Optional
import pandas as pd
from ..schemas.material import MaterialIn


def _n(s: Optional[str]) -> str:
    return (s or "").strip()


def _norm(s: Optional[str]) -> str:
    return _n(s).lower()


def _read_table(path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        engine="openpyxl",
        header=0,
        dtype=str,
        keep_default_na=False,
    )
    # normalize headers
    df.columns = [_norm(c) for c in df.columns]
    # drop the second row (descriptions)
    if len(df) >= 1:
        df = df.drop(index=0).reset_index(drop=True)
    # strip cells
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def _pick(df: pd.DataFrame, mapping: Dict[str, List[str]]) -> Dict[str, str]:
    pos: Dict[str, str] = {}
    for field, candidates in mapping.items():
        for c in candidates:
            cc = _norm(c)
            if cc in df.columns:
                pos[field] = cc
                break
    return pos


def parse_material_sheet(path: str, cfg: Dict) -> List[MaterialIn]:
    scfg = cfg["material_sheet"]
    df = _read_table(path, scfg["sheet_name"])
    pos = _pick(df, scfg["header_map"])

    materials: List[MaterialIn] = []
    for _, row in df.iterrows():
        rec = {k: row.get(col) for k, col in pos.items()}
        # skip fully empty rows (all values None/blank)
        if not any(_n(v) for v in rec.values()):
            continue
        materials.append(MaterialIn(**rec))
    return materials
