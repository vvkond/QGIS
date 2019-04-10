--VIEW with production records
----- all DATA_VALUE as is
create or replace view V_PROD_RECORDS as
select 
        2.0 as VIEW_VERSION
        ,'P_STD_VOL_LQ' as P_STD_VOL_SOURCE
        ,P_STD_VOL_LQ_S as P_STD_VOL_S
        ,TIG_GLOBAL_DATA_FLAG
        ,TIG_INTERPRETER_SLDNID
        ,DB_INSTANCE_TIME_STAMP
        ,DATA_VALUE
        ,DATA_VALUE_U
        ,START_TIME
        ,END_TIME
        ,R_TRANSIENT_PD_NM
        ,ACTIVITY_S
        ,ACTIVITY_T
        ,BSASC_SOURCE
        ,OBJECT_S
        ,OBJECT_T
    from    P_STD_VOL_LQ prod_lq
union all
select     
        2.0 as VIEW_VERSION
        ,'P_STD_VOL_GAS' as P_STD_VOL_SOURCE
        ,P_STD_VOL_GAS_S as P_STD_VOL_S
        ,TIG_GLOBAL_DATA_FLAG
        ,TIG_INTERPRETER_SLDNID
        ,DB_INSTANCE_TIME_STAMP
        ,DATA_VALUE
        ,DATA_VALUE_U
        ,START_TIME
        ,END_TIME
        ,R_TRANSIENT_PD_NM
        ,ACTIVITY_S
        ,ACTIVITY_T
        ,BSASC_SOURCE
        ,OBJECT_S
        ,OBJECT_T
    from    P_STD_VOL_GAS prod_gas
union all
select     
        2.0 as VIEW_VERSION
        ,'P_Q_MASS_BASIS' as P_STD_VOL_SOURCE
        ,P_Q_MASS_BASIS_S as P_STD_VOL_S
        ,TIG_GLOBAL_DATA_FLAG
        ,TIG_INTERPRETER_SLDNID
        ,DB_INSTANCE_TIME_STAMP
        ,DATA_VALUE
        ,DATA_VALUE_U
        ,START_TIME
        ,END_TIME
        ,R_TRANSIENT_PD_NM
        ,ACTIVITY_S
        ,ACTIVITY_T ----filter
        ,BSASC_SOURCE
        ,OBJECT_S
        ,OBJECT_T   ----filter
    from    P_Q_MASS_BASIS mass_t
union all
select     
        2.0 as VIEW_VERSION
        ,'P_Q_VOLUME_BASIS' as P_STD_VOL_SOURCE
        ,P_Q_VOLUME_BASIS_S as P_STD_VOL_S
        ,TIG_GLOBAL_DATA_FLAG
        ,TIG_INTERPRETER_SLDNID
        ,DB_INSTANCE_TIME_STAMP
        ,DATA_VALUE
        ,DATA_VALUE_U
        ,START_TIME
        ,END_TIME
        ,R_TRANSIENT_PD_NM
        ,ACTIVITY_S
        ,ACTIVITY_T ----filter
        ,BSASC_SOURCE
        ,OBJECT_S
        ,OBJECT_T   ----filter
    from  P_Q_VOLUME_BASIS volume_t
    