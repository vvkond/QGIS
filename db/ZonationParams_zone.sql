SELECT
    i.DB_SLDNID,
    TRIM(z.TIG_DESCRIPTION)
    || ' -> '
    || TRIM(i.TIG_INTERVAL_NAME)
    , i.TIG_INTERVAL_NAME 
    , i.tig_interval_order
    , i.tig_level
    
FROM
    tig_interval i,
    tig_zonation z
WHERE
    i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    AND(:zonation_id IS NULL
    OR i.TIG_ZONATION_SLDNID = :zonation_id)
ORDER BY
    z.TIG_DESCRIPTION
    , i.tig_interval_order
    , i.tig_level    