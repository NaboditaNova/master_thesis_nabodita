from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


def _n(s: Optional[str]) -> str:
    return (s or "").strip()


def _norm(s: Optional[str]) -> str:
    return _n(s).lower()


def _to_float(s: Optional[str]) -> Optional[float]:
    t = _n(s)
    if not t:
        return None
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _looks_numeric(s: Optional[str]) -> bool:
    t = _n(s)
    if not t:
        return False
    t = t.replace(",", ".")
    try:
        float(t)
        return True
    except ValueError:
        return False


def read_grid(path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        engine="openpyxl",
        header=None,
        dtype=str,
        keep_default_na=False,
        engine_kwargs={"data_only": True},  # evaluate formulas
    )
    # strip whitespace; pandas ≥2.3 prefers .map over .applymap
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def _find_row_by_first_col(df: pd.DataFrame, labels: List[str]) -> Optional[int]:
    labs = [label.lower() for label in labels]
    for r in range(df.shape[0]):
        if _norm(df.iat[r, 0]) in labs:
            return r
    return None


def _find_section_row(df: pd.DataFrame, titles: List[str]) -> Optional[int]:
    return _find_row_by_first_col(df, titles)


def _collect_materials_from_top_row(df: pd.DataFrame) -> List[Tuple[str, int]]:
    """Top row index 0: col0='Name of the sample', col1='Description', col>=2 => material/flow names."""
    mats: List[Tuple[str, int]] = []
    for j in range(2, df.shape[1]):
        label = _n(df.iat[0, j])
        if label:
            mats.append((label, j))
    return mats


def _pair_columns_for_section(
    df: pd.DataFrame, header_row: int, n_materials: int, unit_labels: List[str]
) -> List[Tuple[int, int]]:
    """
    For a section with per-material pairs (Amount, Unit[*]), scan the header_row starting from col 2 and
    build [(amount_col, unit_col)] for each material in order.
    """
    pairs: List[Tuple[int, int]] = []
    j = 2
    unit_tokens = [u.lower() for u in unit_labels]
    while j < df.shape[1] and len(pairs) < n_materials:
        head = _norm(df.iat[header_row, j])
        if head == "amount":
            # find unit in the next column(s)
            unit_col = None
            if j + 1 < df.shape[1]:
                nxt = _norm(df.iat[header_row, j + 1])
                if any(nxt.startswith(u) for u in unit_tokens):
                    unit_col = j + 1
            pairs.append((j, unit_col if unit_col is not None else -1))
            j += 2
        else:
            j += 1
    return pairs


def parse_mfa_sheet(path: str, cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Returns:
    {
      material_name -> {
        "sample": {... FlowSampleIn fields ...},    # may be empty dict if nothing provided
        "collection_kpi": {...} or None,
        "components": [ {...}, ... ],
        "flags": {...}
      }
    }
    """
    scfg = cfg["mfa_sheet"]
    df = read_grid(path, scfg["sheet_name"])
    materials = _collect_materials_from_top_row(df)

    # NEW: allow empty MFA sheet (no top headers/material columns)
    # Default is True; set mfa_sheet.allow_empty_top_header: false in config to restore old behavior.
    allow_empty = (
        True
        if "allow_empty_top_header" not in scfg
        else bool(scfg["allow_empty_top_header"])
    )
    if not materials:
        if allow_empty:
            return {}  # Gracefully skip MFA merge; nothing to parse
        else:
            raise ValueError("No material/flow columns found in top header row.")

    # --- Stakeholder / Date (single-value per material, not Amount/Unit pairs) ---
    r_stk = _find_row_by_first_col(df, scfg["labels"]["stakeholder_name"])
    r_date = _find_row_by_first_col(df, scfg["labels"]["date"])

    # Flexible ETL buckets: values can be str/float/None; annotate as Any to keep mypy happy
    per_mat: Dict[str, Dict[str, Any]] = {
        name: {
            "sample": {},
            "collection_kpi": None,
            "sorting_kpi": None,
            "recycling_kpi": None,
            "components": [],
            "flags": {},
        }
        for name, _ in materials
    }

    for name, jcol in materials:
        if r_stk is not None:
            v = _n(df.iat[r_stk, jcol])
            if v:
                per_mat[name]["sample"]["stakeholder_name"] = v
        if r_date is not None:
            v = _n(df.iat[r_date, jcol])
            if v:
                per_mat[name]["sample"][
                    "sample_date"
                ] = v  # keep raw; loader will parse

    # Helper to fill sample fields from a 3-col section ("label","Amount","Unit") with per-material pairs
    def _fill_generic_like(section_key: str) -> None:
        title_row = _find_section_row(df, scfg["sections"][section_key])
        if title_row is None:
            return
        # title_row has first cell like "Generic Data"; header row is title_row
        # Next row is description; data start at title_row+2.
        header_row = title_row
        data_start = header_row + 2
        pairs = _pair_columns_for_section(
            df, header_row, len(materials), scfg["subheaders"]["unit"]
        )
        for r in range(data_start, df.shape[0]):
            key = _norm(df.iat[r, 0])
            if not key:
                # heuristic: skip empty lines; real end is detected by next section title
                continue
            # stop on the next section title
            if key in (
                _norm(scfg["sections"]["elementary"][0]),
                _norm(scfg["sections"]["psd_collection"][0]),
                _norm(scfg["sections"]["psd_sorting"][0]),
                _norm(scfg["sections"]["psd_recycling"][0]),
                _norm(scfg["sections"]["material_composition"][0]),
            ):
                break

            # --- Generic Data mapping (mix of text and numeric fields)
            if section_key == "generic_data":
                gmap = scfg["map_generic_rows"]
                if key in gmap:
                    spec = gmap[key]
                    fv = spec.get("field_value")
                    fu = spec.get("field_unit")
                    vtype = (spec.get("type") or "float").lower()

                    for idx, (mat_name, _) in enumerate(materials):
                        if idx >= len(pairs):
                            break
                        a_col, u_col = pairs[idx]
                        a_cell = df.iat[r, a_col] if a_col != -1 else None
                        u_cell = df.iat[r, u_col] if (u_col != -1) else None

                        sample_generic: Dict[str, Any] = per_mat[mat_name]["sample"]

                        if vtype == "text":
                            # Parse text value
                            aval_text: Optional[str] = _n(a_cell) or None
                            # flag: value looks numeric (user put a number where text is expected)
                            # (existing flagging for numeric-looking text can remain above)
                            if aval_text is not None and _looks_numeric(aval_text):
                                per_mat[mat_name]["flags"].setdefault(
                                    "text_numeric", []
                                ).append({"field": key, "value": aval_text})
                            # flag: unit present where text-only row
                            if u_cell is not None and _n(u_cell):
                                per_mat[mat_name]["flags"].setdefault(
                                    "text_unit_present", []
                                ).append({"field": key, "unit": _n(u_cell)})

                            if fv and aval_text is not None:
                                sample_generic[fv] = aval_text
                        else:
                            # Parse numeric value
                            num_val_generic: Optional[float] = _to_float(a_cell)
                            if fv and num_val_generic is not None:
                                sample_generic[fv] = num_val_generic

                        uval_str: str = _n(u_cell) if u_cell is not None else ""
                        if fu and uval_str:
                            sample_generic[fu] = uval_str

            # --- Elementary composition (all numeric; units not allowed)
            elif section_key == "elementary":
                emap = scfg["map_elementary_rows"]
                if key in emap:
                    for idx, (mat_name, _) in enumerate(materials):
                        if idx >= len(pairs):
                            break
                        a_col, u_col = pairs[idx]
                        sample_elem: Dict[str, Any] = per_mat[mat_name]["sample"]

                        elem_val_num: Optional[float] = (
                            _to_float(df.iat[r, a_col]) if a_col != -1 else None
                        )
                        if elem_val_num is not None:
                            sample_elem[emap[key]] = elem_val_num

                        # flag: unit present even though this section should not provide units
                        if u_col != -1:
                            u_cell = df.iat[r, u_col]
                            if _n(u_cell):
                                per_mat[mat_name]["flags"].setdefault(
                                    "elementary_unit_present", []
                                ).append({"field": key, "unit": _n(u_cell)})

            # --- Process Specific Data (Collection) → flow KPI (numeric + unit)
            elif section_key == "psd_collection":
                cmap = scfg["map_collection_kpi_rows"]
                if key in cmap:
                    for idx, (mat_name, _) in enumerate(materials):
                        if idx >= len(pairs):
                            break
                        a_col, u_col = pairs[idx]

                        val_num_kpi: Optional[float] = (
                            _to_float(df.iat[r, a_col]) if a_col != -1 else None
                        )
                        unit_str: str = _n(df.iat[r, u_col]) if (u_col != -1) else ""

                        # Keep only rows that have some data (value or unit)
                        if val_num_kpi is None and not unit_str:
                            continue

                        # ensure dict exists
                        kpi_dict: Dict[str, Any] = (
                            per_mat[mat_name]["collection_kpi"] or {}
                        )
                        per_mat[mat_name]["collection_kpi"] = kpi_dict

                        fv = cmap[key]["field_value"]
                        fu = cmap[key]["field_unit"]
                        if val_num_kpi is not None:
                            kpi_dict[fv] = val_num_kpi
                        if fu and unit_str:
                            kpi_dict[fu] = unit_str

            # --- Process Specific Data (Sorting) → flow KPI (numeric + unit)
            elif section_key == "psd_sorting":
                smap = scfg["map_sorting_kpi_rows"]
                if key in smap:
                    for idx, (mat_name, _) in enumerate(materials):
                        if idx >= len(pairs):
                            break
                        a_col, u_col = pairs[idx]
                        aval = _to_float(df.iat[r, a_col]) if a_col != -1 else None
                        uval = _n(df.iat[r, u_col]) if (u_col != -1) else ""
                        if aval is None and not _n(uval):
                            continue
                        if per_mat[mat_name].get("sorting_kpi") is None:
                            per_mat[mat_name]["sorting_kpi"] = {}
                        fv = smap[key]["field_value"]
                        fu = smap[key]["field_unit"]
                        if aval is not None:
                            per_mat[mat_name]["sorting_kpi"][fv] = aval
                        if fu and _n(uval):
                            per_mat[mat_name]["sorting_kpi"][fu] = uval

            # --- Process Specific Data (Recycling) → flow KPI (numeric + unit)
            elif section_key == "psd_recycling":
                rmap = scfg["map_recycling_kpi_rows"]
                if key in rmap:
                    for idx, (mat_name, _) in enumerate(materials):
                        if idx >= len(pairs):
                            break
                        a_col, u_col = pairs[idx]
                        aval = _to_float(df.iat[r, a_col]) if a_col != -1 else None
                        uval = _n(df.iat[r, u_col]) if (u_col != -1) else ""
                        if aval is None and not _n(uval):
                            continue
                        if per_mat[mat_name].get("recycling_kpi") is None:
                            per_mat[mat_name]["recycling_kpi"] = {}
                        fv = rmap[key]["field_value"]
                        fu = rmap[key]["field_unit"]
                        if aval is not None:
                            per_mat[mat_name]["recycling_kpi"][fv] = aval
                        if fu and _n(uval):
                            per_mat[mat_name]["recycling_kpi"][fu] = uval

    # Fill: Generic Data, Elementary, PSD (Collection)
    _fill_generic_like("generic_data")
    _fill_generic_like("elementary")
    _fill_generic_like("psd_collection")
    _fill_generic_like("psd_sorting")  # NEW
    _fill_generic_like("psd_recycling")  # NEW

    # --- Material Composition (polymer_name/description + per-material amount/unit) ---
    mc_row = _find_section_row(df, scfg["sections"]["material_composition"])
    if mc_row is not None:
        header_row = mc_row
        data_start = header_row + 2  # skip description row
        pairs = _pair_columns_for_section(
            df, header_row, len(materials), scfg["subheaders"]["unit"]
        )
        for r in range(data_start, df.shape[0]):
            key = _n(df.iat[r, 0])  # "Material Composition" (polymer name)
            desc = _n(df.iat[r, 1])  # Description
            if not key and not desc:
                # if row entirely blank, likely end
                continue
            for idx, (mat_name, _) in enumerate(materials):
                if idx >= len(pairs):
                    break
                a_col, u_col = pairs[idx]
                comp_val_num: Optional[float] = (
                    _to_float(df.iat[r, a_col]) if a_col != -1 else None
                )
                uval_str: str = _n(df.iat[r, u_col]) if (u_col != -1) else ""
                # Rule: if Description, Amount, Unit ALL empty -> skip, even if polymer name exists
                if not desc and comp_val_num is None and not uval_str:
                    continue
                comp: Dict[str, Any] = {
                    "polymer_name": key or None,
                    "description": desc or None,
                    "amount_value": comp_val_num,
                    "amount_unit": uval_str or None,
                }
                per_mat[mat_name]["components"].append(comp)

    return per_mat
