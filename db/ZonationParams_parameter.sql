SELECT
    v.DB_SLDNID,
    v.TIG_VARIABLE_SHORT_NAME
    ||(
    CASE v.TIG_VARIABLE_LONG_NAME
        WHEN ' '
        THEN ''
        ELSE(' ('
            || v.TIG_VARIABLE_LONG_NAME
            || ')')
    END)
FROM
    tig_variable v
WHERE
    v.TIG_VARIABLE_TYPE = 2
ORDER BY
    v.TIG_VARIABLE_SHORT_NAME,
    v.TIG_VARIABLE_LONG_NAME,
    v.DB_SLDNID