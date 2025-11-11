from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import text
from sqlalchemy.engine import Engine

CUSTOM_TITLES = [
    "Case Study A: From Collection to Sorting & Recycling",
    "Case Study B: From Collection to Sorting & Recycling",
]


@dataclass
class SplitConfig:
    first_root_label: str | None = "Household LVP"
    subsequent_root_label: str | None = "Household LVP"
    arrangement: str = "snap"
    pad: int = 18
    thickness: int = 20
    node_line_width: int = 1
    node_line_color: str = "rgba(0,0,0,0.15)"
    stage_colors: dict[str, str] = field(
        default_factory=lambda: {
            "Collection": "rgba(52,152,219,0.65)",  # light blue
            "Sorting": "rgba(155,89,182,0.65)",  # light purple
            "Recycling": "rgba(46,204,113,0.65)",  # light green
        }
    )
    unknown_color: str = "rgba(127,140,141,0.5)"


def fetch_joined_df(engine: Engine) -> pd.DataFrame:
    q = text(
        """
        SELECT pmf.process_id,
               p.process_type,
               pmf.direction,
               pmf.material_name,
               pmf.amount_value,
               pmf.amount_unit
        FROM process_material_flow AS pmf
        JOIN process AS p ON pmf.process_id = p.process_id
        ORDER BY pmf.process_id,
                 CASE pmf.direction WHEN 'Input' THEN 0 ELSE 1 END,
                 pmf.material_flow_id
    """
    )
    return pd.read_sql(q, engine)


def _pretty_label(s: str) -> str:

    parts = s.split(" ")
    out = []
    for t in parts:
        if "_" in t or t.isupper():
            out.append(t)
        else:
            out.append(t[:1].upper() + t[1:].lower() if t else t)
    return " ".join(out)


def normalize_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["material_name"] = df["material_name"].astype(str).map(_pretty_label)
    return df


def split_into_groups(df: pd.DataFrame) -> list[pd.DataFrame]:

    df = df.sort_values(["process_id", "direction"]).copy()
    starts = (
        df[(df["process_type"] == "Collection") & (df["direction"] == "Input")][
            "process_id"
        ]
        .drop_duplicates()
        .tolist()
    )
    if not starts:
        return [df]

    groups: list[pd.DataFrame] = []
    for i, pid in enumerate(starts):
        if i < len(starts) - 1:
            next_pid = starts[i + 1]
            groups.append(
                df[(df["process_id"] >= pid) & (df["process_id"] < next_pid)].copy()
            )
        else:
            groups.append(df[df["process_id"] >= pid].copy())
    return groups


def apply_root_overrides(
    group: pd.DataFrame, idx: int, cfg: SplitConfig
) -> pd.DataFrame:

    g = group.copy()
    mask = (g["process_type"] == "Collection") & (g["direction"] == "Input")
    if not mask.any():
        return g

    first_pid = g.loc[mask, "process_id"].min()
    if idx == 0 and cfg.first_root_label:
        g.loc[(g["process_id"] == first_pid) & mask, "material_name"] = (
            cfg.first_root_label
        )
    elif idx > 0 and cfg.subsequent_root_label:
        g.loc[(g["process_id"] == first_pid) & mask, "material_name"] = (
            cfg.subsequent_root_label
        )
    return g


def rows_to_links(group: pd.DataFrame) -> list[dict]:

    links: list[dict] = []
    for pid, chunk in group.groupby("process_id", sort=True):
        ptype = str(chunk["process_type"].iloc[0]) if not chunk.empty else "Unknown"

        inputs = chunk[chunk["direction"] == "Input"][
            ["material_name", "amount_unit"]
        ].values.tolist()
        outputs = chunk[chunk["direction"] == "Output"][
            ["material_name", "amount_value", "amount_unit"]
        ].values.tolist()
        if not outputs or not inputs:
            continue

        src, _src_unit = inputs[0]

        for tgt, val, unit in outputs:
            links.append(
                {
                    "source": src,
                    "target": tgt,
                    "value": float(val) if val is not None else 0.0,
                    "pid": int(pid),
                    "ptype": ptype,
                    "unit": unit or "",
                }
            )
    return links


def node_stage_map_from_links(
    links: list[dict], default_stage: str = "Collection"
) -> dict[str, str]:

    node_stage: dict[str, str] = {}

    for link in links:
        tgt = link["target"]
        ptype = link.get("ptype")
        if ptype:
            node_stage[tgt] = ptype

    all_nodes = {
        *(link["source"] for link in links),
        *(link["target"] for link in links),
    }
    targets = {link["target"] for link in links}
    for src_only in all_nodes - targets:
        node_stage.setdefault(src_only, default_stage)

    return node_stage


def links_to_figure(
    links: list[dict], title: str, cfg: SplitConfig, node_stage_map: dict[str, str]
) -> go.Figure:
    labels: list[str] = sorted(
        {*[link["source"] for link in links], *[link["target"] for link in links]}
    )
    idx = {lab: i for i, lab in enumerate(labels)}
    sources = [idx[link["source"]] for link in links]
    targets = [idx[link["target"]] for link in links]
    values = [link["value"] for link in links]
    link_labels = [f'{link["source"]} → {link["target"]}' for link in links]

    in_sum = {lab: 0.0 for lab in labels}
    out_sum = {lab: 0.0 for lab in labels}
    for link in links:
        out_sum[link["source"]] += link["value"]
        in_sum[link["target"]] += link["value"]

    units = {link.get("unit", "") for link in links if link.get("unit")}
    unit_suffix = f" {units.pop()}" if len(units) == 1 else ""

    def fmt(v: float) -> str:
        return f"{v:,.1f}".replace(",", " ")

    display_value = {}
    for lab in labels:
        display_value[lab] = in_sum[lab] if in_sum[lab] > 0 else out_sum[lab]

    node_labels = [
        (
            f"{lab}<br>{fmt(display_value[lab])}{unit_suffix}"
            if display_value[lab] > 0
            else lab
        )
        for lab in labels
    ]

    node_colors = [
        cfg.stage_colors.get(node_stage_map.get(lab, "Unknown"), cfg.unknown_color)
        for lab in labels
    ]

    stage_link_colors = {
        "Collection": "rgba(52,152,219,0.28)",
        "Sorting": "rgba(155,89,182,0.28)",
        "Recycling": "rgba(46,204,113,0.28)",
    }
    link_colors = [
        stage_link_colors.get(str(link.get("ptype") or ""), "rgba(120,120,120,0.25)")
        for link in links
    ]

    sankey = go.Sankey(
        arrangement=cfg.arrangement,
        node=dict(
            label=node_labels,
            color=node_colors,
            pad=cfg.pad,
            thickness=cfg.thickness,
            line=dict(color=cfg.node_line_color, width=cfg.node_line_width),
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            label=link_labels,
            color=link_colors,
        ),
    )
    fig = go.Figure(sankey)
    fig.update_layout(
        title=title,
        font=dict(size=12),
        template="plotly_white",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def generate_sankey_groups(
    engine: Engine,
    outdir: str,
    cfg: SplitConfig = SplitConfig(),
) -> int:

    os.makedirs(outdir, exist_ok=True)

    raw = fetch_joined_df(engine)
    norm = normalize_labels(raw)
    groups = split_into_groups(norm)

    made = 0
    for i, g in enumerate(groups, start=1):
        g = apply_root_overrides(g, idx=i - 1, cfg=cfg)
        links = rows_to_links(g)
        node_stage_map = node_stage_map_from_links(links, default_stage="Collection")
        fig = links_to_figure(
            links,
            title="",
            cfg=cfg,
            node_stage_map=node_stage_map,
        )

        letter = chr(ord("A") + i - 1)
        title = (
            CUSTOM_TITLES[i - 1]
            if i - 1 < len(CUSTOM_TITLES)
            else f"Case Study {letter}: From collection to sorting & recycling"
        )

        fig.update_layout(title=title)

        html_path = os.path.join(outdir, f"sankey_diagram_{i}.html")
        fig.write_html(html_path, include_plotlyjs="cdn", full_html=True)
        made += 1
    return made
