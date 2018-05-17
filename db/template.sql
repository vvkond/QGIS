SELECT
    t.DB_SLDNID,
    t.TIG_TEMPLATE_DESCRIP,
    t.TIG_APPLICATION_NAME,
    i.LOGIN_NAME,
    TO_CHAR((TO_DATE('01-01-1970', 'DD-MM-YYYY') + (t.DB_INSTANCE_TIME_STAMP / 86400)), 'DD-MM-YYYY HH24:MI:SS') "Created"
FROM
    (select TIG_USER_ID, max(TIG_LOGIN_NAME) as login_name from tig_interpreter group by TIG_USER_ID) i,
    tig_template t
WHERE
    t.TIG_INTERPRETER_SLDNID = i.TIG_USER_ID(+)
    AND t.TIG_APPLICATION_NAME = :app_name
