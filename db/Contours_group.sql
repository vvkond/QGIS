SELECT
    ms.TIG_MAP_SET_NO,
    ms.TIG_MAP_SET_NAME
FROM
    TIG_MAP_SET ms
WHERE
    EXISTS
    (SELECT
        *
    FROM
        TIG_MAP_SET_PARAM msp
    WHERE
        ms.TIG_MAP_SET_NO = msp.TIG_MAP_SET_NO
        AND msp.TIG_MAP_SET_CP_SOURCE = 4
    )
    AND ms.TIG_MAP_SET_TYPE = 1
ORDER BY
    ms.TIG_MAP_SET_NAME,
    ms.TIG_MAP_SET_NO