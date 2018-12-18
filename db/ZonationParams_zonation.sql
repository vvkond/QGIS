SELECT
    z.DB_SLDNID,
    trim(z.TIG_DESCRIPTION)
    || ' ('
    || zt.TIG_DESCRIPTION
    || ')'
    || ' owner='    
    || ti.TIG_LOGIN_NAME
    || ' visibility='    
    || case when z.TIG_GLOBAL_DATA_FLAG=1 then ' Public' else ' Private' end 
    
FROM
    tig_zonation z
    left join GLOBAL.tig_interpreter ti
        on ti.TIG_USER_ID=z.TIG_INTERPRETER_SLDNID
    ,tig_zonation_type zt
WHERE
    z.TIG_ZONATION_TYPE_ID = zt.DB_SLDNID

ORDER BY
    z.TIG_DESCRIPTION,
    zt.TIG_DESCRIPTION,
    z.DB_SLDNID