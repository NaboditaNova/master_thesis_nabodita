from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List, Tuple
import pandas as pd
from sqlalchemy import text
import plotly.graph_objects as go

from mfa_ingest.db.session import get_engine


def _smart_title(s: str) -> str:
    """
    Capitalize only the first letter of each space-separated token.
    - Tokens containing '_' are left unchanged (e.g., 'S1_Urban_bin').
    - We do NOT lower-case the rest, so 'PET' stays 'PET'.
    """
    parts = s.split(" ")
    out = []
    for t in parts:
        if not t or "_" in t:
            out.append(t)
        else:
            out.append(t[0].upper() + t[1:])
    return " ".join(out)


def _fetch_flows_df():
    """
    Returns columns:
      process_id, process_name, process_type, direction, material_name, amount_value
    """
    sql = text(
        """
        SELECT
            p.process_id,
            p.process_name,
            p.process_type,
            f.direction,
            f.material_name,
            f.amount_value
        FROM process_material_flow f
        JOIN process p ON p.process_id = f.process_id
        ORDER BY p.process_id, f.material_flow_id
    """
    )
    eng = get_engine()
    df = pd.read_sql(sql, eng)
    df["material_name"] = df["material_name"].astype(str).apply(_smart_title)
    return df


def _process_label_map(df: pd.DataFrame) -> Tuple[Dict[int, str], Dict[str, str]]:
    """
    Build a label for each process node.
    For Recycling we suffix with the single input material if unique,
    e.g., "Recycling (PET bottles)".
    Returns:
      - process_labels: {process_id -> process_node_label}
      - label_types: {process_node_label -> process_type}
    """
    inputs = df[df["direction"] == "Input"]
    in_by_pid = inputs.groupby("process_id")["material_name"].agg(list).to_dict()

    process_labels: Dict[int, str] = {}
    label_types: Dict[str, str] = {}

    for pid, grp in df.groupby("process_id"):
        ptype = grp["process_type"].iloc[0]
        # pname = grp["process_name"].iloc[0]

        if ptype == "Recycling":
            in_list = in_by_pid.get(pid, [])
            if len(in_list) == 1:
                # Slightly shorter material label for readability in node
                mat_short = _smart_title(
                    in_list[0].replace("S1_Urban_bin — ", "")
                )  # NEW
                label = f"Recycling ({mat_short})"
            else:
                label = ptype  # or pname if you prefer the full process name
        else:
            label = ptype

        process_labels[pid] = label
        label_types[label] = ptype

    return process_labels, label_types


def _map_input_name(material_name: str, process_type: str) -> str:
    """
    Special rule: the very first/primary source node should be named 'Household Collection LVP'.
    We apply this rename for inputs to the Collection stage that contain 'Potential'.
    """
    if process_type == "Collection" and "Potential" in material_name:
        return "Household Collection LVP"
    return material_name


def build_sankey(
    out_html: Path | str = "outputs/sankey.html",
    out_png: Optional[Path | str] = None,
) -> go.Figure:
    df = _fetch_flows_df()

    # Build process node labels
    process_labels, label_types = _process_label_map(df)

    # Split inputs/outputs
    df_in = df[df["direction"] == "Input"].copy()
    df_out = df[df["direction"] == "Output"].copy()

    # Build edges as (source_label, target_label, value, process_type, via)
    # where via ∈ {"input","output"} to help color edges.
    links: List[Dict] = []
    nodes: set[str] = set()

    # Input edges: material -> process
    for _, row in df_in.iterrows():
        src = _map_input_name(row["material_name"], row["process_type"])
        dst = process_labels[row["process_id"]]
        val = float(row["amount_value"] or 0.0)
        links.append(
            {
                "source": src,
                "target": dst,
                "value": val,
                "ptype": row["process_type"],
                "via": "input",
            }
        )
        nodes.add(src)
        nodes.add(dst)

    # Output edges: process -> material
    for _, row in df_out.iterrows():
        src = process_labels[row["process_id"]]
        dst = row["material_name"]
        val = float(row["amount_value"] or 0.0)
        links.append(
            {
                "source": src,
                "target": dst,
                "value": val,
                "ptype": row["process_type"],
                "via": "output",
            }
        )
        nodes.add(src)
        nodes.add(dst)

    # Index nodes
    node_list = list(nodes)
    node_index = {lab: i for i, lab in enumerate(node_list)}

    link_source = [node_index[ls["source"]] for ls in links]
    link_target = [node_index[lt["target"]] for lt in links]
    link_value = [lv["value"] for lv in links]

    # Colors: process nodes by type, material nodes gray; edges by process type
    process_colors = {
        "Collection": "rgba(31,119,180,0.85)",
        # "Sorting":    "rgba(255,127,14,0.85)",
        "Sorting": "rgba(148,103,189,0.85)",  # NEW: purple instead of orange
        "Recycling": "rgba(44,160,44,0.85)",
    }
    material_color = "rgba(180,180,180,0.55)"

    node_colors: List[str] = []
    for lab in node_list:
        if lab in label_types:
            node_colors.append(process_colors.get(label_types[lab], material_color))
        else:
            node_colors.append(material_color)

    # NEW:
    # def _rand_color(label: str, alpha: float = 0.85) -> str:
    #     # Deterministic "random" color per node, stable across runs
    #     rnd = random.Random(hash(label) & 0xFFFFFFFF)
    #     r = rnd.randrange(50, 206)
    #     g = rnd.randrange(50, 206)
    #     b = rnd.randrange(50, 206)
    #     return f"rgba({r},{g},{b},{alpha})"

    # node_colors = [_rand_color(lab) for lab in node_list]

    link_colors = [process_colors.get(lp["ptype"], material_color) for lp in links]

    fig = go.Figure(
        data=[
            go.Sankey(
                # was: arrangement="snap" (or "fixed")
                arrangement="freeform",  # allows dragging in the HTML
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="rgba(0,0,0,0.2)", width=0.5),
                    label=node_list,
                    color=node_colors,
                    # optional: give starting positions (0–1). Users can still drag.
                    x=[0.01, 0.20, 0.50, 0.80],
                    y=[0.10, 0.30, 0.50, 0.70],
                ),
                link=dict(
                    source=link_source,
                    target=link_target,
                    value=link_value,
                    color=link_colors,
                    label=[f"{ls['source']} → {ls['target']}" for ls in links],
                ),
            )
        ]
    )

    fig.update_layout(
        title="Sankey Diagram for Case Study 1",
        font=dict(size=12),
        margin=dict(l=10, r=10, t=40, b=10),
    )

    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=1.02,
                y=1.15,
                xanchor="left",
                yanchor="top",
                buttons=[
                    dict(
                        label="Thin",
                        method="restyle",
                        args=[{"node.thickness": [12], "node.pad": [14]}],
                    ),
                    dict(
                        label="Normal",
                        method="restyle",
                        args=[{"node.thickness": [22], "node.pad": [18]}],
                    ),
                    dict(
                        label="Thick",
                        method="restyle",
                        args=[{"node.thickness": [34], "node.pad": [22]}],
                    ),
                ],
                showactive=True,
            )
        ]
    )

    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_html))

    if out_png:
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        # Requires `kaleido` (we added it)
        fig.write_image(str(out_png), scale=2)

    return fig
