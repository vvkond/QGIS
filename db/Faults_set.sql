SELECT
    msp.TIG_MAP_SET_PARAMETER_NO,
    ms.TIG_MAP_SET_NAME
    || '/'
    || msp.TIG_PARAM_LONG_NAME
FROM
    TIG_MAP_SET ms,
    TIG_MAP_SET_PARAM msp
WHERE
    ms.TIG_MAP_SET_NO = msp.TIG_MAP_SET_NO
    AND ms.TIG_MAP_SET_TYPE = 2
    AND(ms.TIG_MAP_SET_NO = :group_id
    OR :group_id IS NULL)