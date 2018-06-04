SELECT
    t.DB_SLDNID,
    t.TIG_TEMPLATE_DESCRIP,
    t.TIG_APPLICATION_NAME,
    i.LOGIN_NAME,
    t.DB_INSTANCE_TIME_STAMP / 86400 "Created"
FROM
    (select TIG_USER_ID, max(TIG_LOGIN_NAME) as login_name from tig_interpreter group by TIG_USER_ID) i
    left join tig_template t on t.TIG_INTERPRETER_SLDNID = i.TIG_USER_ID
WHERE
    t.TIG_APPLICATION_NAME = :app_name
