from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import text
from sqlalchemy.engine import Engine

# ---------- Config ----------

CUSTOM_TITLES = [
    "Case Study A: From Collection to Sorting & Recycling",
    "Case Study B: From Collection to Sorting & Recycling",
]


@dataclass
class SplitConfig:
    first_root_label: str | None = "Household LVP"
    subsequent_root_label: str | None = "Household LVP"
    # title_prefix: str = "MFA Sankey"
    arrangement: str = (
        "snap"  # "snap" looks tidy. ("freeform" needs x/y you set manually)
    )
    pad: int = 18
    thickness: int = 20
    node_line_width: int = 1
    node_line_color: str = "rgba(0,0,0,0.15)"
    # randomize_node_colors: bool = True

    # NEW: stage colors (light shades)
    stage_colors: dict[str, str] = field(
        default_factory=lambda: {
            "Collection": "rgba(52,152,219,0.65)",  # light blue
            "Sorting": "rgba(155,89,182,0.65)",  # light purple
            "Recycling": "rgba(46,204,113,0.65)",  # light green
        }
    )
    unknown_color: str = "rgba(127,140,141,0.5)"  # fallback


# ---------- Query + prep ----------


def fetch_joined_df(engine: Engine) -> pd.DataFrame:
    """
    process_material_flow JOIN process, ordered by process_id and direction (Input first).
    """
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
    """
    Title-case *words separated by spaces* only.
    - Words with underscores are left as-is.
    - ALL-CAPS tokens (e.g., PET, HDPE) kept as-is.
    """
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
    """
    Split the rows whenever we encounter a Collection Input again.
    Each group becomes one Sankey diagram.

    Heuristic: find process_ids where (process_type=='Collection' & direction=='Input'),
    then cut ranges between those pids.
    """
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
    """
    For each group, override the *first* Collection Input label:
      - Group 0 -> cfg.first_root_label (if provided)
      - Group N>0 -> cfg.subsequent_root_label (if provided)
    """
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


# ---------- Build links ----------

# def rows_to_links(group: pd.DataFrame) -> list[dict]:
#     """
#     Within each process_id, connect the (first) Input material_name -> each Output material_name,
#     with value = amount_value of the Output row.
#     """
#     links: list[dict] = []
#     for pid, chunk in group.groupby("process_id", sort=True):
#         inputs = chunk[chunk["direction"] == "Input"]["material_name"].tolist()
#         outputs = chunk[chunk["direction"] == "Output"][["material_name", "amount_value"]].values.tolist()
#         if not outputs:
#             continue
#         if not inputs:
#             # No explicit input declared; skip (or could fan-out from a stage label)
#             continue
#         src = inputs[0]
#         for tgt, val in outputs:
#             links.append({
#                 "source": src,
#                 "target": tgt,
#                 "value": float(val) if val is not None else 0.0,
#                 "pid": int(pid),
#             })
#     return links


def rows_to_links(group: pd.DataFrame) -> list[dict]:
    """
    For each process_id, connect the (first) Input -> each Output.
    Attach process_type and amount_unit to every link.
    """
    links: list[dict] = []
    for pid, chunk in group.groupby("process_id", sort=True):
        ptype = str(chunk["process_type"].iloc[0]) if not chunk.empty else "Unknown"

        # Grab inputs/outputs
        inputs = chunk[chunk["direction"] == "Input"][
            ["material_name", "amount_unit"]
        ].values.tolist()
        outputs = chunk[chunk["direction"] == "Output"][
            ["material_name", "amount_value", "amount_unit"]
        ].values.tolist()
        if not outputs or not inputs:
            continue

        src, _src_unit = inputs[0]  # first input as the source label

        for tgt, val, unit in outputs:
            links.append(
                {
                    "source": src,
                    "target": tgt,
                    "value": float(val) if val is not None else 0.0,
                    "pid": int(pid),
                    "ptype": ptype,
                    "unit": unit or "",  # keep unit if present
                }
            )
    return links


def node_stage_map_from_links(
    links: list[dict], default_stage: str = "Collection"
) -> dict[str, str]:
    """
    Color nodes by the stage that PRODUCES them:
      - the target of a link inherits that link's process_type.
      - sources that never appear as a target get default_stage (root inputs).
    """
    node_stage: dict[str, str] = {}

    # Targets inherit the producing process' type
    for link in links:
        tgt = link["target"]
        ptype = link.get("ptype")
        if ptype:
            node_stage[tgt] = ptype

    # Any node that is only a source (never a target) → default to 'Collection'
    all_nodes = {
        *(link["source"] for link in links),
        *(link["target"] for link in links),
    }
    targets = {link["target"] for link in links}
    for src_only in all_nodes - targets:
        node_stage.setdefault(src_only, default_stage)

    return node_stage


# ---------- Plotly ----------

# def _rand_rgba(alpha: float = 0.85) -> str:
#     r = random.randint(40, 215)
#     g = random.randint(40, 215)
#     b = random.randint(40, 215)
#     return f"rgba({r},{g},{b},{alpha})"


# def links_to_figure(links: list[dict], title: str, cfg: SplitConfig) -> go.Figure:
#     if not links:
#         # Empty figure with a friendly title
#         fig = go.Figure()
#         fig.update_layout(title=title, template="plotly_white")
#         return fig

#     labels: list[str] = sorted({*[l["source"] for l in links], *[l["target"] for l in links]})
#     idx = {lab: i for i, lab in enumerate(labels)}
#     sources = [idx[l["source"]] for l in links]
#     targets = [idx[l["target"]] for l in links]
#     values = [l["value"] for l in links]
#     link_labels = [f'{l["source"]} → {l["target"]}' for l in links]

#     # Node colors
#     if cfg.randomize_node_colors:
#         node_colors = [_rand_rgba() for _ in labels]
#     else:
#         node_colors = ["rgba(100,100,100,0.85)"] * len(labels)

#     # Make link colors slightly translucent
#     link_colors = ["rgba(120,120,120,0.35)"] * len(values)

#     sankey = go.Sankey(
#         arrangement=cfg.arrangement,  # "snap" is tidy; plotly does not support interactive dragging
#         node=dict(
#             label=labels,
#             color=node_colors,
#             pad=cfg.pad,
#             thickness=cfg.thickness,
#             line=dict(color=cfg.node_line_color, width=cfg.node_line_width),
#         ),
#         link=dict(
#             source=sources,
#             target=targets,
#             value=values,
#             label=link_labels,
#             color=link_colors,
#         ),
#     )
#     fig = go.Figure(sankey)
#     fig.update_layout(
#         title=title,
#         font=dict(size=12),
#         template="plotly_white",
#         margin=dict(l=10, r=10, t=60, b=10),
#     )
#     return fig


# def links_to_figure(links: list[dict], title: str, cfg: SplitConfig, node_stage_map: dict[str, str]) -> go.Figure:
#     ...
#     labels: list[str] = sorted({*[l["source"] for l in links], *[l["target"] for l in links]})
#     idx = {lab: i for i, lab in enumerate(labels)}
#     sources = [idx[l["source"]] for l in links]
#     targets = [idx[l["target"]] for l in links]
#     values = [l["value"] for l in links]
#     link_labels = [f'{l["source"]} → {l["target"]}' for l in links]

#     # Node colors by stage
#     node_colors = [cfg.stage_colors.get(node_stage_map.get(lab, "Unknown"), cfg.unknown_color) for lab in labels]

#     # Link colors by producing stage (lower alpha)
#     stage_link_colors = {
#         "Collection": "rgba(52,152,219,0.28)",
#         "Sorting":    "rgba(155,89,182,0.28)",
#         "Recycling":  "rgba(46,204,113,0.28)",
#     }
#     link_colors = [stage_link_colors.get(l.get("ptype"), "rgba(120,120,120,0.25)") for l in links]

#     sankey = go.Sankey(
#         arrangement=cfg.arrangement,
#         node=dict(
#             label=labels,
#             color=node_colors,
#             pad=cfg.pad,
#             thickness=cfg.thickness,
#             line=dict(color=cfg.node_line_color, width=cfg.node_line_width),
#         ),
#         link=dict(
#             source=sources,
#             target=targets,
#             value=values,
#             label=link_labels,
#             color=link_colors,
#         ),
#     )
#     fig = go.Figure(sankey)
#     fig.update_layout(
#         title=title,
#         font=dict(size=12),
#         template="plotly_white",
#         margin=dict(l=10, r=10, t=60, b=10),
#     )
#     return fig


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

    # -------- NEW: node totals (prefer incoming, else outgoing) --------
    in_sum = {lab: 0.0 for lab in labels}
    out_sum = {lab: 0.0 for lab in labels}
    for link in links:
        out_sum[link["source"]] += link["value"]
        in_sum[link["target"]] += link["value"]

    # Decide a single unit to print if consistent; otherwise omit
    units = {link.get("unit", "") for link in links if link.get("unit")}
    unit_suffix = f" {units.pop()}" if len(units) == 1 else ""

    def fmt(v: float) -> str:
        # thousands-sep + 1 decimal; tweak as you like
        return f"{v:,.1f}".replace(",", " ")  # thin space as thousands sep

    display_value = {}
    for lab in labels:
        display_value[lab] = in_sum[lab] if in_sum[lab] > 0 else out_sum[lab]

    # Put amount on a second line under the node label
    node_labels = [
        (
            f"{lab}<br>{fmt(display_value[lab])}{unit_suffix}"
            if display_value[lab] > 0
            else lab
        )
        for lab in labels
    ]

    # Node colors by stage (as you already have)
    node_colors = [
        cfg.stage_colors.get(node_stage_map.get(lab, "Unknown"), cfg.unknown_color)
        for lab in labels
    ]

    # Link colors by producing stage (lower alpha)
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
            label=node_labels,  # ← use augmented labels
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


# ---------- Orchestration ----------


def generate_sankey_groups(
    engine: Engine,
    outdir: str,
    cfg: SplitConfig = SplitConfig(),
) -> int:
    """
    Fetch data, split into groups, render and write HTMLs.
    Returns the number of diagrams created.
    """
    os.makedirs(outdir, exist_ok=True)

    raw = fetch_joined_df(engine)
    norm = normalize_labels(raw)
    groups = split_into_groups(norm)

    made = 0
    for i, g in enumerate(groups, start=1):
        g = apply_root_overrides(g, idx=i - 1, cfg=cfg)
        links = rows_to_links(g)
        # NEW: derive node→stage mapping (roots default to Collection)
        node_stage_map = node_stage_map_from_links(links, default_stage="Collection")
        fig = links_to_figure(
            links,
            title="",
            cfg=cfg,
            node_stage_map=node_stage_map,
        )

        # Pick explicit title for A, B (fallback for any extra groups)
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
