from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import pandas as pd


def read_grid(path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        engine="openpyxl",
        header=None,
        dtype=str,
        keep_default_na=False,
    )
    # was: df = df.applymap(...)
    # pandas ≥2.3: DataFrame.applymap is deprecated → use DataFrame.map
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def n(s: Optional[str]) -> str:
    return (s or "").strip()


def norm(s: Optional[str]) -> str:
    return n(s).lower()


def find_cell(df: pd.DataFrame, needles: List[str]) -> Optional[Tuple[int, int]]:
    """Find first cell whose normalized value equals any of the needles (normalized)."""
    needles = [norm(x) for x in needles]
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            if norm(df.iat[r, c]) in needles:
                return r, c
    return None


def find_row_starting_with(df: pd.DataFrame, titles: List[str]) -> Optional[int]:
    """Find a row index where any cell equals any normalized title (section title)."""
    pos = find_cell(df, titles)
    return pos[0] if pos else None


def resolve_header_positions(
    header_row: int, df: pd.DataFrame, wanted: Dict[str, List[str]]
) -> Dict[str, int]:
    """Map logical names -> column index by matching header labels."""
    result: Dict[str, int] = {}
    width = df.shape[1]
    for j in range(width):
        label = norm(df.iat[header_row, j])
        if not label:
            continue
        for key, candidates in wanted.items():
            if key in result:
                continue
            for cand in candidates:
                if label == norm(cand):
                    result[key] = j
                    break
    return result


def extract_table_rows(
    df: pd.DataFrame,
    title_row: int,
    next_section_row: Optional[int],
    header_map: Dict[str, List[str]],
    skip_desc_row: bool = True,
) -> Tuple[Dict[str, int], List[int]]:
    """
    Given a section title row, return (header_positions, data_rows indices) for that section.
    Assumes the next row after header is a description row to skip.
    """
    header_row = title_row + 1
    data_start = header_row + (2 if skip_desc_row else 1)
    data_end = next_section_row if next_section_row is not None else df.shape[0]

    cols = resolve_header_positions(header_row, df, header_map)
    rows: List[int] = []
    for r in range(data_start, data_end):
        # consider a row "blank" if all mapped columns are empty
        if all(n(df.iat[r, c]) == "" for c in cols.values()):
            continue
        rows.append(r)
    return cols, rows


def to_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    st = n(s)
    if not st:
        return None
    st = st.replace(",", ".")
    try:
        return float(st)
    except ValueError:
        return None


def parse_process_block(
    df: pd.DataFrame, labels: Dict[str, List[str]]
) -> Tuple[str, str]:
    """
    Find 'Process' and 'Process typ(e)' rows anywhere in the grid and read the adjacent cell to the right.
    """
    name_pos = find_cell(df, labels["process_label"])
    if not name_pos:
        raise ValueError("Could not find 'Process' label in sheet.")
    r, c = name_pos
    process_name = n(df.iat[r, c + 1]) if c + 1 < df.shape[1] else ""

    type_pos = find_cell(df, labels["process_type_label"])
    if not type_pos:
        raise ValueError("Could not find 'Process type' label in sheet.")
    r2, c2 = type_pos
    process_type = n(df.iat[r2, c2 + 1]) if c2 + 1 < df.shape[1] else ""
    return process_name, process_type


def parse_process_sheet(path: str, cfg: Dict) -> Dict:
    """
    Returns a dict:
    {
      "process": {"process_name":..., "process_type":..., "kpi": {...} or None},
      "flows": [ {"direction":"Input"|"Output","material_name":...,"amount_value":...,"amount_unit":...,"reference_text":...}, ... ]
    }
    """
    ps_cfg = cfg["process_sheet"]
    sheet_name = ps_cfg["sheet_name"]
    df = read_grid(path, sheet_name)

    # 1) Process header
    process_name, process_type = parse_process_block(df, ps_cfg["labels"])
    if not process_type:
        raise ValueError("Process type is empty.")

    # 2) section row indexes
    in_row = find_row_starting_with(df, ps_cfg["sections"]["input_flows_title"])
    tech_row = find_row_starting_with(df, ps_cfg["sections"]["technology_title"])
    out_row = find_row_starting_with(df, ps_cfg["sections"]["output_flows_title"])
    if in_row is None or tech_row is None or out_row is None:
        raise ValueError(
            "Could not locate one or more sections (Input flows / Technology / Output flows)."
        )

    # 3) Input flows
    in_cols, in_rows = extract_table_rows(
        df, in_row, tech_row, ps_cfg["input_flows"]["header_map"]
    )
    keep_inputs = [norm(x) for x in ps_cfg["input_flows"]["keep_value_in_input_col"]]
    input_flows = []
    for r in in_rows:
        input_flag = n(df.iat[r, in_cols["input"]]) if "input" in in_cols else ""
        if norm(input_flag) not in keep_inputs:
            continue
        name = n(df.iat[r, in_cols["name"]]) if "name" in in_cols else ""
        value = to_float(df.iat[r, in_cols["value"]]) if "value" in in_cols else None
        unit = n(df.iat[r, in_cols["unit"]]) if "unit" in in_cols else ""
        ref = n(df.iat[r, in_cols["reference"]]) if "reference" in in_cols else ""
        # skip if all 5 fields are empty
        # 🚫 NEW: drop rows that contain only the flag (no other data)
        # Keep the row only if at least one of {name, value, unit, ref} is present.
        if not any([name, value is not None, unit, ref]):
            continue
        input_flows.append(
            {
                "direction": "Input",
                "material_name": name or None,
                "amount_value": value,
                "amount_unit": unit or None,
                "reference_text": ref or None,
            }
        )

    # 4) Output flows
    out_cols, out_rows = extract_table_rows(
        df, out_row, None, ps_cfg["output_flows"]["header_map"]
    )
    keep_outputs = [norm(x) for x in ps_cfg["output_flows"]["keep_value_in_output_col"]]
    output_flows = []
    for r in out_rows:
        output_flag = n(df.iat[r, out_cols["output"]]) if "output" in out_cols else ""
        if norm(output_flag) not in keep_outputs:
            continue
        name = n(df.iat[r, out_cols["name"]]) if "name" in out_cols else ""
        value = to_float(df.iat[r, out_cols["value"]]) if "value" in out_cols else None
        unit = n(df.iat[r, out_cols["unit"]]) if "unit" in out_cols else ""
        ref = n(df.iat[r, out_cols["reference"]]) if "reference" in out_cols else ""

        # 🚫 NEW: drop rows that contain only the flag (no other data)
        if not any([name, value is not None, unit, ref]):
            continue
        output_flows.append(
            {
                "direction": "Output",
                "material_name": name or None,
                "amount_value": value,
                "amount_unit": unit or None,
                "reference_text": ref or None,
            }
        )

    # 5) Technology → process-level KPI for the selected type
    tech_cols, tech_rows = extract_table_rows(
        df, tech_row, out_row, ps_cfg["technology"]["header_map"]
    )

    def row_str(r, key):
        return n(df.iat[r, tech_cols[key]]) if key in tech_cols else ""

    def row_val(r, key):
        return to_float(df.iat[r, tech_cols[key]]) if key in tech_cols else None

    patterns = ps_cfg["technology"]["patterns"]
    t = norm(process_type)
    if t not in ("collection", "sorting", "recycling"):
        raise ValueError(f"Unexpected process_type: {process_type}")

    p_cfg = patterns[t]
    kpi = None
    for r in tech_rows:
        params = row_str(r, "process_params").lower()
        name = row_str(r, "name").lower()
        if p_cfg["params_contains"] in params and p_cfg["name_equals"] == name:
            val = row_val(r, "value")
            unit = row_str(r, "unit")
            ref = row_str(r, "reference")
            # if all three empty -> no KPI row
            if not any([val is not None, unit, ref]):
                kpi = None
            else:
                if t == "collection":
                    kpi = {
                        "table": "collection_process_kpi",
                        "collection_rate_amount": val,
                        "amount_unit": unit or None,
                        "reference_text": ref or None,
                    }
                elif t == "sorting":
                    kpi = {
                        "table": "sorting_process_kpi",
                        "sorting_yield_amount": val,
                        "amount_unit": unit or None,
                        "reference_text": ref or None,
                    }
                else:
                    kpi = {
                        "table": "recycling_process_kpi",
                        "recycling_yield_amount": val,
                        "amount_unit": unit or None,
                        "reference_text": ref or None,
                    }
            break

    return {
        "process": {
            "process_name": process_name or None,
            "process_type": process_type,
            "kpi": kpi,
        },
        "flows": input_flows + output_flows,
    }
