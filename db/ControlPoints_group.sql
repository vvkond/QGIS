SELECT
    ms.TIG_MAP_SET_NO,
    ms.TIG_MAP_SET_NAME
FROM
    TIG_MAP_SET ms
WHERE
---    EXISTS
---    (SELECT
---        *
---    FROM
---        TIG_MAP_SET_PARAM msp,
---        TIG_MAP_SUBSET mss,
---        TIG_MAP_SUBSET_PARAM_VAL mssp
---    WHERE
---        mssp.TIG_MAP_SET_PARAMETER_NO = msp.TIG_MAP_SET_PARAMETER_NO
---        AND mssp.TIG_MAP_SUBSET_NO = mss.TIG_MAP_SUBSET_NO
---        AND ms.TIG_MAP_SET_NO = msp.TIG_MAP_SET_NO
---        AND ms.TIG_MAP_SET_NO = mss.TIG_MAP_SET_NO
---        AND ms.TIG_MAP_SET_NO = mssp.TIG_MAP_SET_NO
---    )
---    AND 
	ms.TIG_MAP_SET_TYPE = 1
ORDER BY
    ms.TIG_MAP_SET_NAME,
    ms.TIG_MAP_SET_NO