SELECT distinct
    vi.TIG_TOP_POINT_DEPTH,
    zz.well_name,
    i.tig_interval_order
FROM
    tig_well_interval vi,
    tig_interval i,
    tig_zonation z,
    tig_variable v,
    (SELECT distinct
        i.tig_interval_order base_order,
        wh.TIG_LATEST_WELL_NAME well_name,
        wh.DB_SLDNID well_id
    FROM
        tig_well_interval vi,
        tig_well_history wh,
        tig_interval i,
        tig_zonation z,
        tig_variable v
    WHERE
        wh.DB_SLDNID = :well_id
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
    AND i.tig_interval_order > zz.base_order
ORDER BY
    i.tig_interval_order
