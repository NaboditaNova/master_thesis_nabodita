from __future__ import annotations
import pandas as pd
from typing import Dict, List, Tuple


def _read_sheet(path: str, sheet: str) -> pd.DataFrame:
    # Read as strings to preserve what Excel shows; we'll parse later.
    df = pd.read_excel(
        path,
        sheet_name=sheet,
        engine="openpyxl",
        dtype=str,
        keep_default_na=False,  # keep blanks as ""
    )
    # Normalize headers
    df.columns = [normalize_header(c) for c in df.columns]
    # Strip whitespace from all string cells
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # Track original row numbers (1-based Excel row incl. header -> we approximate)
    df.insert(0, "__row__", range(2, 2 + len(df)))
    return df


def normalize_header(h: str) -> str:
    return " ".join(h.replace("\n", " ").replace("_", " ").split()).strip().lower()


class WorkbookFrames:
    def __init__(self, frames: Dict[str, pd.DataFrame]):
        self.frames = frames

    def get(self, key: str) -> pd.DataFrame:
        return self.frames[key]


def read_workbook(path: str, sheet_names: Dict[str, str]) -> WorkbookFrames:
    """
    sheet_names = {"process": "Process", "flows": "...", "material": "...", "general": "..."}
    """
    frames = {}
    for key, sheet in sheet_names.items():
        frames[key] = _read_sheet(path, sheet)
    return WorkbookFrames(frames)


def pick_columns(
    df: pd.DataFrame, candidates: List[str]
) -> Tuple[str | None, pd.Series | None]:
    """
    Find first present column by list of candidate header names (already normalized).
    Returns (column_name, series) or (None, None) if none found.
    """
    norm_candidates = [normalize_header(c) for c in candidates]
    for c in norm_candidates:
        if c in df.columns:
            return c, df[c]
    return None, None
