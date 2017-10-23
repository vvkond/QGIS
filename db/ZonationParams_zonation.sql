SELECT
    z.DB_SLDNID,
    trim(z.TIG_DESCRIPTION)
    || ' ('
    || zt.TIG_DESCRIPTION
    || ')'
FROM
    tig_zonation z,
    tig_zonation_type zt
WHERE
    z.TIG_ZONATION_TYPE_ID = zt.DB_SLDNID
ORDER BY
    z.TIG_DESCRIPTION,
    zt.TIG_DESCRIPTION,
    z.DB_SLDNID