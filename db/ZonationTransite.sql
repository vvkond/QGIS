SELECT distinct
    vi.TIG_TOP_POINT_DEPTH,
    zz.well_name,
    TRIM(z.TIG_DESCRIPTION),
    TRIM(i.TIG_INTERVAL_NAME)
FROM
    tig_well_interval vi,
    tig_interval i,
    tig_zonation z,
    tig_variable v,
    (SELECT distinct
        vi.TIG_TOP_POINT_DEPTH base_depth,
        wh.TIG_LATEST_WELL_NAME well_name,
        wh.DB_SLDNID well_id
    FROM
        tig_well_interval vi,
        tig_well_history wh,
        tig_interval i,
        tig_zonation z,
        tig_variable v
    WHERE
        wh.TIG_LATEST_WELL_NAME = :well_id
        AND wh.DB_SLDNID = vi.TIG_WELL_SLDNID
        AND vi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
        AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
        AND(z.DB_SLDNID = :zonation_id
        OR :zonation_id IS NULL)
        AND(i.DB_SLDNID = :zone_id
        OR :zone_id IS NULL)
        AND v.TIG_VARIABLE_SHORT_NAME = 'TopTVD'
        AND v.TIG_VARIABLE_TYPE = 2) zz
WHERE
    vi.TIG_WELL_SLDNID = zz.well_id
    AND vi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
    AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    AND(z.DB_SLDNID = :zonation_id
        OR :zonation_id IS NULL)
    AND v.TIG_VARIABLE_TYPE = 2
    AND v.TIG_VARIABLE_SHORT_NAME = 'TopTVD'
    AND vi.TIG_TOP_POINT_DEPTH > zz.base_depth
ORDER BY
    vi.TIG_TOP_POINT_DEPTH
