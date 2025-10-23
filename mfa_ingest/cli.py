import typer
from .core.settings import settings
from .core.db import make_engine, reflect_sanity_check
from .extract.process_sheet_parser import parse_process_sheet
from .transform.process_sheet_builder import build_packets_from_process_dict
from .extract.mfa_sheet_parser import parse_mfa_sheet
from .transform.merge_mfa_with_process import merge_mfa_into_packets
from typing import Optional

app = typer.Typer(no_args_is_help=True)


@app.command()
def env():
    typer.echo(f"APP_ENV={settings.app_env}")
    typer.echo(f"CHUNK_SIZE={settings.chunk_size}")


@app.command()
def ping_db():
    eng = make_engine()
    with eng.connect():
        typer.echo("✅ DB connection OK")


@app.command()
def check_schema():
    eng = make_engine()
    reflect_sanity_check(eng)
    typer.echo("✅ Live schema looks OK (basic check)")


@app.command()
def validate(
    xlsm: str, config: str = "config/default.yaml", check_materials: bool = False
):
    """Validate Process + MFA sheets (no DB) (+ optional Material sheet)."""
    import yaml  # type: ignore[import-untyped]
    from .transform.validators import validate_packets, Issue

    with open(config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Process -> packets
    pdata = parse_process_sheet(xlsm, cfg)
    packets = build_packets_from_process_dict(pdata)

    # MFA -> per-material (with flags), then merge
    mfa = parse_mfa_sheet(xlsm, cfg)
    unmatched = merge_mfa_into_packets(packets, mfa)

    issues = validate_packets(packets)

    # A) Orphan MFA columns with data
    for name in unmatched:
        issues.append(
            Issue(
                "MFA sheet",
                0,
                f"Column header does not match any flow material_name: {name!r}",
            )
        )

    # B) Flags from parser: text rows numeric / stray units / elementary units
    for mat_name, payload in mfa.items():
        flags = payload.get("flags") or {}
        for it in flags.get("text_numeric", []):
            issues.append(
                Issue(
                    "MFA (Generic Data)",
                    0,
                    f"{mat_name!r}: '{it['field']}' value looks numeric ({it['value']}). Expected text.",
                )
            )
        for it in flags.get("text_unit_present", []):
            issues.append(
                Issue(
                    "MFA (Generic Data)",
                    0,
                    f"{mat_name!r}: '{it['field']}' has a unit '{it['unit']}' but units are not allowed.",
                )
            )
        for it in flags.get("elementary_unit_present", []):
            issues.append(
                Issue(
                    "MFA (Elementary)",
                    0,
                    f"{mat_name!r}: '{it['field']}' has a unit '{it['unit']}' but units are not allowed.",
                )
            )

    # NEW: optional material sheet checks + component→material suggestions
    if check_materials:
        from .extract.material_sheet_parser import parse_material_sheet
        from .transform.material_matcher import match_components_to_materials

        mats = parse_material_sheet(xlsm, cfg)
        # basic sanity: at least one field must be non-empty; already enforced by parser

        # add suggestions to components; collect low-confidence items
        low = match_components_to_materials(packets, mats, cfg)
        for flow_name, items in low.items():
            for it in items:
                issues.append(
                    Issue(
                        "Material match",
                        0,
                        f"{flow_name!r}: component {it['component']!r} has low/none match (score={it['score']}); suggestion={it['suggestion']!r}",
                    )
                )

    if issues:
        typer.echo("❌ Validation issues found:")
        for i in issues:
            typer.echo(f"  - {i}")
        raise typer.Exit(code=1)

    typer.echo("✅ Validation passed for Process + MFA sheets.")


@app.command()
def plan(
    xlsm: str,
    config: str = "config/default.yaml",
    json_out: bool = False,
    show_components: bool = True,
    show_rownums: bool = False,  # <- NEW: show internal row numbers if you really want them
    materials: bool = False,
):
    """
    Dry plan with table-by-table preview. Uses placeholder IDs to show FK links:

      P#  -> process
      F#  -> process_material_flow
      K#  -> collection_flow_kpi
      S#  -> flow_sample
      C#  -> flow_sample_component
    """
    import yaml  # type: ignore[import-untyped]
    import json

    def compact(d: dict) -> dict:
        # Remove empty values; hide 'rownum' unless explicitly requested
        return {
            k: v
            for k, v in d.items()
            if v not in (None, "", []) and (show_rownums or k != "rownum")
        }

    with open(config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Build packets: Process sheet + MFA sheet merged
    pdata = parse_process_sheet(xlsm, cfg)
    packets = build_packets_from_process_dict(pdata)
    mfa = parse_mfa_sheet(xlsm, cfg)
    merge_mfa_into_packets(packets, mfa)

    if not packets:
        print("No process found.")
        raise typer.Exit(code=1)

    P_ID = "P1"
    process_row = compact(
        {
            "process_name": pdata["process"].get("process_name"),
            "process_type": pdata["process"].get("process_type"),
        }
    )

    print("\n=== INSERT PLAN ===")

    print("\nTable: process")
    print(f"  id: P1 -> {process_row}")

    # Counters for pseudo-IDs
    k_counter = 0  # collection_flow_kpi
    s_counter = 0  # flow_sample
    c_counter = 0  # flow_sample_component

    print("\nTable: process_material_flow")
    flow_ids = []
    for i, fp in enumerate(packets[0].flows, start=1):
        F_ID = f"F{i}"
        flow_ids.append(F_ID)
        flow_row = compact(
            {
                "process_id": P_ID,
                "direction": fp.flow.direction,
                "material_name": fp.flow.material_name,
                "amount_value": fp.flow.amount_value,
                "amount_unit": fp.flow.amount_unit,
                "reference_text": fp.flow.reference_text,
            }
        )
        print(f"  id: {F_ID} -> {flow_row}")

        K_ID = None
        if fp.collection_kpi:
            k_counter += 1
            K_ID = f"K{k_counter}"
            krow = compact(fp.collection_kpi.model_dump(exclude_none=True))
            print("    ↳ Table: collection_flow_kpi")
            print(f"       id: {K_ID} -> {krow}")

        if fp.sample:
            s_counter += 1
            S_ID = f"S{s_counter}"
            # drop internal 'rownum' from preview
            srow = compact(fp.sample.model_dump(exclude_none=True))
            srow = {"material_flow_id": F_ID, "collection_flow_kpi_id": K_ID} | srow
            print("    ↳ Table: flow_sample")
            print(f"       id: {S_ID} -> {srow}")

            if fp.components:
                print("       ↳ Table: flow_sample_component")
                for comp in fp.components:
                    c_counter += 1
                    C_ID = f"C{c_counter}"
                    crow = compact(comp.model_dump(exclude_none=True))
                    crow = {"sample_id": S_ID, "material_id": None} | crow
                    if show_components:
                        print(f"          id: {C_ID} -> {crow}")
                if not show_components:
                    print(f"          (total components hidden: {len(fp.components)})")

    # Counts summary
    result = {
        "process": 1,
        "process_material_flow": len(flow_ids),
        "collection_flow_kpi": k_counter,
        "flow_sample": s_counter,
        "flow_sample_component": c_counter,
    }

    if json_out:
        print("\nCounts JSON:")
        print(json.dumps(result, indent=2))
    else:
        print("\n=== COUNTS ===")
        for k, v in result.items():
            print(f"  {k}: {v}")

    if materials:
        from .extract.material_sheet_parser import parse_material_sheet
        from .transform.material_matcher import match_components_to_materials

        mats = parse_material_sheet(xlsm, cfg)
        print("\nTable: material (preview; inserts/updates happen in Step 4)")
        for i, m in enumerate(mats[:20], start=1):
            print(
                f"  id?: M{i} -> ",
                {k: v for k, v in m.model_dump(exclude_none=True).items()},
            )

        low = match_components_to_materials(packets, mats, cfg)
        any_suggestions = False
        for p in packets:
            for fp in p.flows:
                comps = [c for c in fp.components if c.material_name_suggested]
                if comps:
                    any_suggestions = True
                    print(
                        f"\nSuggested component→material matches for flow '{fp.flow.material_name}':"
                    )
                    for c in comps:
                        print(
                            f"  • {c.polymer_name or c.description} -> {c.material_name_suggested} (score={c.material_match_score})"
                        )
        if not any_suggestions:
            print("\nNo component→material suggestions.")

        if low:
            print("\n⚠️  Components with low/none matches:")
            for flow_name, items in low.items():
                for it in items:
                    print(
                        f"  - {flow_name}: {it['component']} (score={it['score']}, suggestion={it['suggestion']})"
                    )


@app.command()
def load(
    xlsm: str,
    config: str = "config/default.yaml",
    replace_process_by_name: bool = False,
    materials: bool = False,
    auto_create_materials: bool = False,
    dry_run: bool = False,  # <- NEW
    database_url: Optional[str] = None,  # <- NEW (override)
    echo_sql: bool = False,  # <- NEW (debug)
):
    """
    Load the given workbook into MariaDB.

    - If --materials: upsert the Material_Table first (insert/update).
    - If --replace-process-by-name: delete any existing process with same name before inserting (cascade).
    - If --auto-create-materials: create a bare material(row) when a component match is missing.
    - If --dry-run: execute everything but roll back the transaction at the end (no writes).
    - If --database-url: override .env connection string for this run.
    - If --echo-sql: print SQL emitted by SQLAlchemy (debug).
    """
    import yaml  # type: ignore[import-untyped]
    from .db.session import get_engine, get_session
    from .extract.process_sheet_parser import parse_process_sheet
    from .transform.process_sheet_builder import build_packets_from_process_dict
    from .extract.mfa_sheet_parser import parse_mfa_sheet
    from .transform.merge_mfa_with_process import merge_mfa_into_packets
    from .extract.material_sheet_parser import parse_material_sheet
    from .load.loader import load_packets, LoadOptions

    with open(config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Build packets (Process + MFA)
    pdata = parse_process_sheet(xlsm, cfg)
    packets = build_packets_from_process_dict(pdata)
    mfa = parse_mfa_sheet(xlsm, cfg)
    _unmatched = merge_mfa_into_packets(packets, mfa)  # validation should catch these

    mats = parse_material_sheet(xlsm, cfg) if materials else []

    # DB session
    engine = get_engine(database_url_override=database_url, echo=echo_sql)
    with get_session(engine) as session:
        session.begin()
        opts = LoadOptions(
            replace_process_by_name=replace_process_by_name,
            materials=mats,
            auto_create_materials=auto_create_materials,
        )
        result = load_packets(session, packets, opts)

        if dry_run:
            # Don't persist anything; this mimics everything except the final commit
            session.rollback()
        else:
            session.commit()

    # Pretty summary
    print("\n=== LOAD SUMMARY ===")
    if dry_run:
        print("  (DRY RUN: no changes were committed)")

    for k in (
        "material_inserted",
        "material_updated",
        "collection_process_kpi",
        "sorting_process_kpi",
        "recycling_process_kpi",
        "process",
        "process_material_flow",
        "collection_flow_kpi",
        "flow_sample",
        "flow_sample_component",
    ):
        print(f"  {k}: {result.counts[k]}")

    if result.components_without_material:
        print("\n⚠ Components without material_id (kept NULL):")
        for flow_name, cmp_name in result.components_without_material[:50]:
            print(f"  - flow {flow_name!r}: component {cmp_name!r}")
        if len(result.components_without_material) > 50:
            print(f"  ... and {len(result.components_without_material) - 50} more")


if __name__ == "__main__":
    app()
