---view with reservoir part production
create or replace view V_PROD_RESPART_M2 as
select
    2.0            as VIEW_VERSION
    ,well.WELL_ID         as well_id      ----latest name take from TIG_WELL_HISTORY    
    ,wb.WELLBORE_S
    ,wb.WELLBORE_ID
    ,wbi.WELLBORE_INTV_S
    ,p_a.PRODUCTION_ALOC_S
    ,p_a.PROD_START_TIME     as prod_start_time
    ,p_a.PROD_END_TIME     as prod_end_time
    ,extract(year from p_a.PROD_START_TIME) as prod_start_year
    ,extract(month from p_a.PROD_START_TIME) as prod_start_month
    ---###production value###
    ,(case when prod_rec.DATA_VALUE>0 then prod_rec.DATA_VALUE else 0 end) as prod_value
    ,prod_rec.DATA_VALUE_U    as prod_value_unit
    ---,prod_rec.R_TRANSIENT_PD_NM as prod_value_period --monthly->Reconciled gas+tonn,event->General  m3,no gas
    ,prod_rec.BSASC_SOURCE    as prod_value_name
    ,prod_rec.P_STD_VOL_SOURCE    as prod_value_source
    ---###times info###
    ---,times.R_TRANSIENT_PD_NM
    ,times.DATA_VALUE    as prod_time    
    ,p_a.PROD_START_TIME+(case when times.DATA_VALUE_U='s' and times.DATA_VALUE>0 then times.DATA_VALUE/86400.0 else 0 end) as fact_prod_end_time
    ,(case when times.DATA_VALUE_U='s' and times.DATA_VALUE<>-999 then times.DATA_VALUE/86400.0 else 0 end) as prod_days
    ,times.DATA_VALUE_U    as prod_time_unit
    ,times.BSASC_SOURCE    as work_type   --water injection,gas injection,production
    ,times.P_PFNU_PORT_TIME_S as P_PFNU_PORT_TIME_S  --id of time record
from 
    WELL well,
    WELLBORE wb,
    WELLBORE_INTV wbi,
    PFNU_PROD_ACT_X pp_ax,
    PRODUCTION_ALOC p_a,
    V_PROD_RECORDS prod_rec,
    P_PFNU_PORT_TIME times  ---can use V_TIME times. On BIN_N_m2 we have 5s vs 10s
where
    --well->wellbore
    well.WELL_S=wb.WELL_S
    --wellbore->wellbore_intv
    and
    wb.WELLBORE_S=wbi.WELLBORE_S  
    and 
    wbi.GEOLOGIC_FTR_T='RESERVOIR_PART'        ---filter: RESELM only from WELLBORE
    ---reservoir_part->PRODUCTION_ALOC over PFNU_PROD_ACT_X
    and 
    pp_ax.PFNU_T='RESERVOIR_PART'              ---filter: production for RESELM only from PFNU_PROD_ACT_X
    and
    pp_ax.PRODUCTION_ACT_T='PRODUCTION_ALOC'   ---filter:  from PFNU_PROD_ACT_X only PRODUCTION_ALOC 
    and 
    wbi.GEOLOGIC_FTR_S=pp_ax.PFNU_S
    and
    pp_ax.PRODUCTION_ACT_S=p_a.PRODUCTION_ALOC_S
    and     
    p_a.TYPICAL_ACT_NAME='production re-allocation'  ---filter: PRODUCTION_ALOC only for Re-allocation of Production Data
    ---PROD ALOC ->prod record VIEW
    and
    p_a.PRODUCTION_ALOC_S=prod_rec.ACTIVITY_S
    and
    prod_rec.ACTIVITY_T='PRODUCTION_ALOC'              ---filter: prod record view only for PRODUCTION_ALOC
    and 
    prod_rec.DATA_VALUE IS NOT NULL
    ---PROD ALOC ->TIMES
    ---  times for each ACTIVITY_S have:gas injection,water injection,production
    ---  We take only first times where DATA_VALUE>0. It faster but if we have incorrect record with 'time prod' and 'time inj' it will incorrect   
    ---    GENRAL and RECONCILED have different ACTIVITY_S    
    and
    p_a.PRODUCTION_ALOC_S=times.ACTIVITY_S
    and
    times.ACTIVITY_T='PRODUCTION_ALOC'
    and
    times.DATA_VALUE IS NOT NULL ---only 1 record from 3 times varian can be with data

