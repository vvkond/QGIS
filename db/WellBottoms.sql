SELECT
    well."Well Name",
    well.Well_ID,
    well."API No.",
    well."Operator",
    well."Country",
    well."Latitude",
    well."Longitude",
    well."Total Depth",
    elev."Measurement",
    elev."Elevation",
    elev."Datum",
    well."On/Offshore",
    well."Status",
    well."Symbol",
    well."Spud Date",
    well."Global/Private",
    well."Owner",
    well."Created",
    well."Project",
    well.TIG_LONGITUDE,
    well.TIG_LATITUDE,
    cd.TIG_DELTA_X_ORDINATE,
    cd.TIG_DELTA_Y_ORDINATE
FROM
    (SELECT DISTINCT
        w.TIG_LATEST_WELL_NAME AS "Well Name",
        w.TIG_API_NUMBER "API No.",
        w.TIG_LATEST_OPERATOR_NAME "Operator",
        w.TIG_COUNTRY "Country",
        TO_CHAR(TRUNC(w.TIG_LATITUDE, 6)) "Latitude",
        TO_CHAR(TRUNC(w.TIG_LONGITUDE, 6)) "Longitude",
        w.TIG_TOTAL_DEPTH "Total Depth",
        REPLACE(REPLACE(w.TIG_ON_OR_OFF_SHORE, '1', 'Offshore'), '0', 'Onshore') "On/Offshore",
        w.TIG_LATEST_WELL_STATE_NO "Status",
        s.TIG_DESCRIPTION "Symbol",
        TO_CHAR(b.SPUD_DATE, 'DD-MM-YYYY') "Spud Date",
        REPLACE(REPLACE(w.TIG_GLOBAL_DATA_FLAG, '1', 'Global'), '0', 'Private') "Global/Private",
        'gg' "Owner",
        TO_CHAR((TO_DATE('01-01-1970', 'DD-MM-YYYY') +(w.DB_INSTANCE_TIME_STAMP / 86400)), 'DD-MM-YYYY') "Created",
        '%2' "Project",
        w.DB_SLDNID Well_ID,
        w.TIG_LONGITUDE,
        w.TIG_LATITUDE
    FROM
        tig_well_history w,
        well b,
        global.tig_well_symbol s
    WHERE
        w.TIG_LATEST_WELL_NAME = b.WELL_ID
        AND w.TIG_WELL_SYMBOL_ID = s.TIG_WELL_SYMBOL_ID(+)
        AND w.TIG_ONLY_PROPOSAL <= 1
    ) well,
    (SELECT
        e.Well_ID,
        e."Measurement",
        e."Elevation",
        e."Datum"
    FROM
        (SELECT
            a.DB_SLDNID Elev_ID,
            a.TIG_WELL_SLDNID Well_ID,
            ed1.TIG_DATUM_NAME "Measurement",
            TRUNC(a.TIG_DATUM_OFFSET, 2) "Elevation",
            ed2.TIG_DATUM_NAME "Datum"
        FROM
            tig_elevation_changes a,
            tig_elevation_datum ed1,
            tig_elevation_datum ed2
        WHERE
            a.TIG_INITIAL_DATUM = ed1.DB_SLDNID
            AND a.TIG_TERMINAL_DATUM = ed2.DB_SLDNID
            AND(a.TIG_DESCRIPTION IS NULL
            OR a.TIG_DESCRIPTION NOT LIKE 'BOL: %')
        ) e,
        (SELECT
            MAX(tig_elevation_changes.DB_SLDNID) max_elev_Id
        FROM
            tig_elevation_changes
        WHERE(tig_elevation_changes.TIG_DESCRIPTION IS NULL)
            OR(tig_elevation_changes.TIG_DESCRIPTION NOT LIKE 'BOL: %')
        GROUP BY
            tig_elevation_changes.TIG_WELL_SLDNID
        ) i
    WHERE
        e.Elev_ID = i.max_elev_Id
    ) elev,
    tig_computed_deviation cd
WHERE
    well.Well_ID = elev.Well_ID(+)
    AND cd.TIG_WELL_SLDNID = well.Well_ID
    AND well.TIG_LONGITUDE != 0
    AND well.TIG_LATITUDE != 0
    AND cd.DB_SLDNID IN
    (SELECT
        MAX(cd2.DB_SLDNID)
    FROM
        tig_computed_deviation cd2
    WHERE
        cd2.TIG_WELL_SLDNID = well.Well_ID
    )
ORDER BY
    well.Well_ID