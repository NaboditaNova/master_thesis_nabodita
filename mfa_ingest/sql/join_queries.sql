/* ============================================================
   1) COLLECTION: process → flow → sample → KPIs → components → material
   - Includes:    collection_process_kpi, collection_flow_kpi
   - Excludes:    sorting/recycling process+flow KPI tables
   - Column rules:
       * process:              process_name, process_type
       * process_material_flow: direction, material_name, amount_value, amount_unit
       * flow_sample:          NO moisture_condition, density, density_unit,
                               carbon_content_pct, nitrogen_content_pct,
                               hydrogen_content_pct, phosphorus_content_pct,
                               oxygen_content_pct, color
       * flow_sample_component: polymer_name, amount_value, amount_unit
       * material:             polymer_type, sorting_guidelines
   ============================================================ */

SELECT
    -- Process
    p.process_name,
    p.process_type,

    -- Process-level KPI (Collection)
    cpk.collection_rate_amount,
    cpk.amount_unit AS collection_rate_unit,

    -- Flow (process_material_flow)
    f.direction,
    f.material_name,
    f.amount_value AS flow_amount_value,
    f.amount_unit AS flow_amount_unit,

    -- Flow sample (flow_sample)
    fs.stakeholder_name,
    fs.sample_date,
    fs.contamination,
    fs.contamination_unit,
    fs.amount_value AS sample_amount_value,
    fs.amount_unit AS sample_amount_unit,

    -- Flow-level KPI (Collection)
    cfk.purity_amount,
    cfk.purity_unit,
    cfk.npp_share_amount_value,
    cfk.npp_share_amount_unit,
    cfk.residual_waste_share_amount_value,
    cfk.residual_waste_share_amount_unit,

    -- Components (flow_sample_component)
    fsc.polymer_name,
    fsc.amount_value AS component_amount_value,
    fsc.amount_unit AS component_amount_unit,

    -- Material lookup
    m.polymer_type,
    m.sorting_guidelines
FROM process AS p
LEFT JOIN collection_process_kpi AS cpk
       ON p.collection_process_kpi_id = cpk.process_kpi_id
LEFT JOIN process_material_flow AS f
       ON f.process_id = p.process_id
LEFT JOIN flow_sample AS fs
       ON fs.material_flow_id = f.material_flow_id
LEFT JOIN collection_flow_kpi AS cfk
       ON fs.collection_flow_kpi_id = cfk.flow_kpi_id
LEFT JOIN flow_sample_component AS fsc
       ON fsc.sample_id = fs.sample_id
LEFT JOIN material AS m
       ON m.material_id = fsc.material_id
WHERE p.process_type = 'Collection'
ORDER BY
    p.process_name,
    f.direction,
    f.material_name,
    fs.sample_id,
    fsc.polymer_name;



/* ============================================================
   2) SORTING: process → flow → sample → KPIs → components → material
   - Includes:    sorting_process_kpi, sorting_flow_kpi
   - Excludes:    collection_process_kpi, collection_flow_kpi,
                  recycling_process_kpi, recycling_flow_kpi
   - Same column rules as above for each table.
   ============================================================ */

SELECT
    -- Process
    p.process_name,
    p.process_type,

    -- Process-level KPI (Sorting)
    spk.sorting_yield_amount,
    spk.amount_unit AS sorting_yield_unit,

    -- Flow (process_material_flow)
    f.direction,
    f.material_name,
    f.amount_value AS flow_amount_value,
    f.amount_unit AS flow_amount_unit,

    -- Flow sample (flow_sample)
    fs.stakeholder_name,
    fs.sample_date,
    fs.amount_value AS sample_amount_value,
    fs.amount_unit AS sample_amount_unit,

    -- Flow-level KPI (Sorting)
    sfk.purity_amount,
    sfk.purity_unit,
    sfk.maximum_total_amount_of_impurities_amount,
    sfk.maximum_total_amount_of_impurities_unit,
    sfk.yield_of_ds_from_input_amount,
    sfk.yield_of_ds_from_input_unit,

    -- Components (flow_sample_component)
    fsc.polymer_name,
    fsc.amount_value AS component_amount_value,
    fsc.amount_unit AS component_amount_unit,

    -- Material lookup
    m.polymer_type,
    m.sorting_guidelines
FROM process AS p
LEFT JOIN sorting_process_kpi AS spk
       ON p.sorting_process_kpi_id = spk.process_kpi_id
LEFT JOIN process_material_flow AS f
       ON f.process_id = p.process_id
LEFT JOIN flow_sample AS fs
       ON fs.material_flow_id = f.material_flow_id
LEFT JOIN sorting_flow_kpi AS sfk
       ON fs.sorting_flow_kpi_id = sfk.flow_kpi_id
LEFT JOIN flow_sample_component AS fsc
       ON fsc.sample_id = fs.sample_id
LEFT JOIN material AS m
       ON m.material_id = fsc.material_id
WHERE p.process_type = 'Sorting'
ORDER BY
    p.process_name,
    f.direction,
    f.material_name,
    fs.sample_id,
    fsc.polymer_name;



/* ============================================================
   3) RECYCLING: process → flow → sample → KPIs → components → material
   - Includes:    recycling_process_kpi, recycling_flow_kpi
   - Excludes:    collection_process_kpi, collection_flow_kpi,
                  sorting_process_kpi, sorting_flow_kpi
   - Same column rules as above for each table.
   ============================================================ */

SELECT
    -- Process
    p.process_name,
    p.process_type,

    -- Process-level KPI (Recycling)
    rpk.recycling_yield_amount,
    rpk.amount_unit AS recycling_yield_unit,

    -- Flow (process_material_flow)
    f.direction,
    f.material_name,
    f.amount_value AS flow_amount_value,
    f.amount_unit AS flow_amount_unit,

    -- Flow sample (flow_sample)
    fs.stakeholder_name,
    fs.sample_date,
    fs.amount_value AS sample_amount_value,
    fs.amount_unit AS sample_amount_unit,

    -- Flow-level KPI (Recycling)
    rfk.yield_flow_sample_amount,
    rfk.yield_flow_sample_unit,

    -- Components (flow_sample_component)
    fsc.polymer_name,
    fsc.amount_value AS component_amount_value,
    fsc.amount_unit AS component_amount_unit,

    -- Material lookup
    m.polymer_type,
    m.sorting_guidelines
FROM process AS p
LEFT JOIN recycling_process_kpi AS rpk
       ON p.recycling_process_kpi_id = rpk.process_kpi_id
LEFT JOIN process_material_flow AS f
       ON f.process_id = p.process_id
LEFT JOIN flow_sample AS fs
       ON fs.material_flow_id = f.material_flow_id
LEFT JOIN recycling_flow_kpi AS rfk
       ON fs.recycling_flow_kpi_id = rfk.flow_kpi_id
LEFT JOIN flow_sample_component AS fsc
       ON fsc.sample_id = fs.sample_id
LEFT JOIN material AS m
       ON m.material_id = fsc.material_id
WHERE p.process_type = 'Recycling'
ORDER BY
    p.process_name,
    f.direction,
    f.material_name,
    fs.sample_id,
    fsc.polymer_name;



/* All non-ID columns from all tables, joined together
   and sorted by process_id (plus flow/sample/component for stability). */

SELECT
    /* ---------- process ---------- */
    p.process_name,
    p.process_type,

    /* ---------- process-level KPIs ---------- */
    -- Collection
    cpk.collection_rate_amount                  AS collection_process_collection_rate_amount,
    cpk.amount_unit                             AS collection_process_collection_rate_unit,
    cpk.reference_text                          AS collection_process_collection_reference,

    -- Sorting
    spk.sorting_yield_amount                    AS sorting_process_sorting_yield_amount,
    spk.amount_unit                             AS sorting_process_sorting_yield_unit,
    spk.reference_text                          AS sorting_process_sorting_reference,

    -- Recycling
    rpk.recycling_yield_amount                  AS recycling_process_recycling_yield_amount,
    rpk.amount_unit                             AS recycling_process_recycling_yield_unit,
    rpk.reference_text                          AS recycling_process_recycling_reference,

    /* ---------- process_material_flow ---------- */
    f.direction,
    f.material_name                             AS flow_material_name,
    f.amount_value                              AS flow_amount_value,
    f.amount_unit                               AS flow_amount_unit,
    f.reference_text                            AS flow_reference_text,

    /* ---------- flow_sample ---------- */
    fs.stakeholder_name,
    fs.sample_date,
    fs.contamination,
    fs.contamination_unit,
    fs.moisture_condition,
    fs.density,
    fs.density_unit,
    fs.carbon_content_pct,
    fs.nitrogen_content_pct,
    fs.hydrogen_content_pct,
    fs.phosphorus_content_pct,
    fs.oxygen_content_pct,
    fs.color                                     AS sample_color,
    fs.amount_value                              AS sample_amount_value,
    fs.amount_unit                               AS sample_amount_unit,

    /* ---------- collection_flow_kpi ---------- */
    cfk.purity_amount                            AS collection_flow_purity_amount,
    cfk.purity_unit                              AS collection_flow_purity_unit,
    cfk.attached_moisture_and_dirt_amount_value  AS collection_flow_attached_moisture_value,
    cfk.attached_moisture_and_dirt_amount_unit   AS collection_flow_attached_moisture_unit,
    cfk.npp_share_amount_value                   AS collection_flow_npp_share_value,
    cfk.npp_share_amount_unit                    AS collection_flow_npp_share_unit,
    cfk.residual_waste_share_amount_value        AS collection_flow_residual_share_value,
    cfk.residual_waste_share_amount_unit         AS collection_flow_residual_share_unit,
    cfk.eps_items_amount_value                   AS collection_flow_eps_items_value,
    cfk.eps_items_amount_unit                    AS collection_flow_eps_items_unit,

    /* ---------- sorting_flow_kpi ---------- */
    sfk.maximum_total_amount_of_impurities_amount AS sorting_flow_max_impurities_amount,
    sfk.maximum_total_amount_of_impurities_unit   AS sorting_flow_max_impurities_unit,
    sfk.purity_amount                             AS sorting_flow_purity_amount,
    sfk.purity_unit                               AS sorting_flow_purity_unit,
    sfk.other_metal_items_amount                  AS sorting_flow_other_metal_amount,
    sfk.other_metal_items_unit                    AS sorting_flow_other_metal_unit,
    sfk.other_plastics_items_amount               AS sorting_flow_other_plastics_amount,
    sfk.other_plastics_items_unit                 AS sorting_flow_other_plastics_unit,
    sfk.ppk_amount                                AS sorting_flow_ppk_amount,
    sfk.ppk_unit                                  AS sorting_flow_ppk_unit,
    sfk.eps_items_amount                          AS sorting_flow_eps_items_amount,
    sfk.eps_items_unit                            AS sorting_flow_eps_items_unit,
    sfk.pvc_items_amount                          AS sorting_flow_pvc_items_amount,
    sfk.pvc_items_unit                            AS sorting_flow_pvc_items_unit,
    sfk.colourless_transparent_foils_amount       AS sorting_flow_ct_foils_amount,
    sfk.colourless_transparent_foils_unit         AS sorting_flow_ct_foils_unit,
    sfk.yield_of_ds_from_input_amount             AS sorting_flow_yield_ds_from_input_amount,
    sfk.yield_of_ds_from_input_unit               AS sorting_flow_yield_ds_from_input_unit,

    /* ---------- recycling_flow_kpi ---------- */
    rfk.filtration_amount                         AS recycling_flow_filtration_amount,
    rfk.filtration_unit                           AS recycling_flow_filtration_unit,
    rfk.recyclate_polymer_purity_amount           AS recycling_flow_polymer_purity_amount,
    rfk.recyclate_polymer_purity_unit             AS recycling_flow_polyler_purity_unit,
    rfk.pcr_content_amount                        AS recycling_flow_pcr_content_amount,
    rfk.pcr_content_unit                          AS recycling_flow_pcr_content_unit,
    rfk.melt_flow_rate_amount                     AS recycling_flow_mfr_amount,
    rfk.melt_flow_rate_unit                       AS recycling_flow_mfr_unit,
    rfk.ash_content_amount                        AS recycling_flow_ash_content_amount,
    rfk.ash_content_unit                          AS recycling_flow_ash_content_unit,
    rfk.tensile_modulus_amount                    AS recycling_flow_tensile_modulus_amount,
    rfk.tensile_modulus_unit                      AS recycling_flow_tensile_modulus_unit,
    rfk.tensile_strength_amount                   AS recycling_flow_tensile_strength_amount,
    rfk.tensile_strength_unit                     AS recycling_flow_tensile_strength_unit,
    rfk.chapry_notch_impact_strength_amount       AS recycling_flow_charpy_notch_amount,
    rfk.chapry_notch_impact_strength_unit         AS recycling_flow_charpy_notch_unit,
    rfk.yield_flow_sample_amount                  AS recycling_flow_yield_sample_amount,
    rfk.yield_flow_sample_unit                    AS recycling_flow_yield_sample_unit,

    /* ---------- flow_sample_component ---------- */
    fsc.polymer_name,
    fsc.description                               AS component_description,
    fsc.amount_value                              AS component_amount_value,
    fsc.amount_unit                               AS component_amount_unit,

    /* ---------- material ---------- */
    m.description                                 AS material_description,
    m.chemical_formula,
    m.polymer_type                                AS material_polymer_type,
    m.common_applications,
    m.carbon_content                              AS material_carbon_content,
    m.standard_density_kg_m3,
    m.density_reference,
    m.cas_number,
    m.color                                       AS material_color,
    m.standardized_sorting_number,
    m.sorting_guidelines,
    m.din_spec_91446_comments

FROM process AS p
LEFT JOIN collection_process_kpi AS cpk
       ON p.collection_process_kpi_id = cpk.process_kpi_id
LEFT JOIN sorting_process_kpi AS spk
       ON p.sorting_process_kpi_id    = spk.process_kpi_id
LEFT JOIN recycling_process_kpi AS rpk
       ON p.recycling_process_kpi_id  = rpk.process_kpi_id
LEFT JOIN process_material_flow AS f
       ON f.process_id                = p.process_id
LEFT JOIN flow_sample AS fs
       ON fs.material_flow_id         = f.material_flow_id
LEFT JOIN collection_flow_kpi AS cfk
       ON fs.collection_flow_kpi_id   = cfk.flow_kpi_id
LEFT JOIN sorting_flow_kpi AS sfk
       ON fs.sorting_flow_kpi_id      = sfk.flow_kpi_id
LEFT JOIN recycling_flow_kpi AS rfk
       ON fs.recycling_flow_kpi_id    = rfk.flow_kpi_id
LEFT JOIN flow_sample_component AS fsc
       ON fsc.sample_id               = fs.sample_id
LEFT JOIN material AS m
       ON m.material_id               = fsc.material_id
ORDER BY
    p.process_id,
    f.material_flow_id,
    fs.sample_id,
    fsc.sample_component_id;
