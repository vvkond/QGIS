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
    ii.TIG_LOGIN_NAME "Owner",
    TO_CHAR((TO_DATE('01-01-1970', 'DD-MM-YYYY') +(wh.DB_INSTANCE_TIME_STAMP / 86400)), 'DD-MM-YYYY HH24:MI:SS') AS "Created"
FROM
    tig_well_history wh,
    (select TIG_USER_ID, max(TIG_LOGIN_NAME) as TIG_LOGIN_NAME from tig_interpreter group by TIG_USER_ID) ii
WHERE
    wh.DB_SLDNID = :well_id
    AND wh.TIG_INTERPRETER_SLDNID = ii.TIG_USER_ID(+)

