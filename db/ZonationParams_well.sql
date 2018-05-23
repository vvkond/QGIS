SELECT distinct
    wh.DB_SLDNID AS "well_id",
    wh.TIG_LATEST_WELL_NAME AS "well_name",
    wh.TIG_CLIENT_WELL_NAME AS "Full name",
    wh.TIG_LATEST_OPERATOR_NAME,
    wh.TIG_API_NUMBER,
    REPLACE(REPLACE(wh.TIG_ON_OR_OFF_SHORE, '1', 'Offshore'), '0', 'Onshore') AS "Location",
    wh.TIG_LATITUDE,
    wh.TIG_LONGITUDE,
    wh.TIG_SLOT_NUMBER,
    ii.login_name "Owner",
    TO_CHAR((TO_DATE('01-01-1970', 'DD-MM-YYYY') +(wh.DB_INSTANCE_TIME_STAMP / 86400)), 'DD-MM-YYYY HH24:MI:SS') AS "Created"
FROM
    tig_well_interval vi,
    tig_well_history wh,
    tig_interval i,
    tig_zonation z,
    tig_variable v,
    (select TIG_USER_ID, max(TIG_LOGIN_NAME) as login_name from tig_interpreter group by TIG_USER_ID) ii
WHERE
    wh.DB_SLDNID = vi.TIG_WELL_SLDNID
    AND vi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
    AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    AND(z.DB_SLDNID = :zonation_id
    OR :zonation_id IS NULL)
    AND(i.DB_SLDNID = :zone_id
    OR :zone_id IS NULL)
    AND v.TIG_VARIABLE_TYPE = 2
    AND wh.TIG_INTERPRETER_SLDNID = ii.TIG_USER_ID(+)

