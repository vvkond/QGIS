SELECT distinct
    wh.TIG_LATEST_WELL_NAME AS "well_name",
    wh.DB_SLDNID AS "well_id"
FROM
    tig_well_interval vi,
    tig_well_history wh,
    tig_interval i,
    tig_zonation z,
    tig_variable v
WHERE
    wh.DB_SLDNID = vi.TIG_WELL_SLDNID
    AND vi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
    AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    AND(z.DB_SLDNID = :zonation_id
    OR :zonation_id IS NULL)
    AND(i.DB_SLDNID = :zone_id
    OR :zone_id IS NULL)
    AND v.TIG_VARIABLE_TYPE = 2

