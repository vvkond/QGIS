SELECT
    wh.TIG_LATEST_WELL_NAME AS "well_name",
    TRIM(z.TIG_DESCRIPTION) AS "zonation_name",
    TRIM(i.TIG_INTERVAL_NAME) AS "zone_name",
    v.TIG_VARIABLE_SHORT_NAME AS "parameter_name",
    vi.TIG_TOP_POINT_DEPTH AS "top_depth",
    vi.TIG_BOT_POINT_DEPTH AS "bottom_depth",
    wh.DB_SLDNID AS "well_id",
    z.DB_SLDNID AS "zonation_id",
    vi.DB_SLDNID AS "zone_id",
    v.DB_SLDNID AS "parameter_id",
    wh.TIG_LONGITUDE,
    wh.TIG_LATITUDE,
    cd.TIG_DELTA_X_ORDINATE AS "cd_x",
    cd.TIG_DELTA_Y_ORDINATE AS "cd_y",
    cd.TIG_INDEX_TRACK_DATA AS "cd_md",
    cd.TIG_Z_ORDINATE AS "cd_tvd",
    z.TIG_ZONATION_PARAMS,
    v.TIG_VARIABLE_SHORT_NAME,
    v.TIG_VARIABLE_REAL_DFLT,
    v.TIG_VARIABLE_REAL_MIN,
    v.TIG_VARIABLE_REAL_MAX,
    v.TIG_VARIABLE_REAL_NULL
FROM
    tig_well_interval vi,
    tig_well_history wh,
    tig_interval i,
    tig_zonation z,
    tig_computed_deviation cd,
    tig_variable v
WHERE
    wh.DB_SLDNID = vi.TIG_WELL_SLDNID
    AND vi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
    AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    AND v.TIG_VARIABLE_SHORT_NAME = 'TopTVD'
    AND(z.DB_SLDNID = :zonation_id
    OR :zonation_id IS NULL)
    AND(i.DB_SLDNID = :zone_id
    OR :zone_id IS NULL)
    AND v.TIG_VARIABLE_TYPE = 2
    AND cd.DB_SLDNID IN
    (SELECT
        MAX(cd2.DB_SLDNID)
    FROM
        tig_computed_deviation cd2
    WHERE
        cd2.TIG_WELL_SLDNID = wh.DB_SLDNID
    )
