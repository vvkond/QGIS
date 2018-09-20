select
PRESS.DATA_VALUE v_pressure
,'' as tig_zonation_key
,'' as tig_top_zone_key
,'' as tig_base_zone_key
,'' as reservoir_part_code
,{0} as start_time
---,STUDY.START_TIME as start_time
,{1} as end_time
---,STUDY.END_TIME as end_time
,PL1D.data_frst_ord as v_meas_depth


from
--MEASURE(for RESERVOIR)
wtst_meas MEAS
----only PRESSURE meas
left join p_trpr PRESS
    on PRESS.ACTIVITY_S=MEAS.WTST_MEAS_S
    and upper(PRESS.ACTIVITY_T)='WTST_MEAS'
    and PRESS.BSASC_SOURCE='GaugeDepthReservoirPressure'
left join P_Location_1d PL1D
    on PL1D.ACTIVITY_S=MEAS.WTST_MEAS_S
    and upper(PL1D.ACTIVITY_T)='WTST_MEAS'
    and PL1D.BSASC_SOURCE='MeasureDepthPoint'
    
--STUDY(PARENT)    
,wtst_meas STUDY
inner join pfnu_prod_act_x PPAX
    on upper(PPAX.PRODUCTION_ACT_T)='WTST_MEAS'
    and PPAX.PRODUCTION_ACT_S=STUDY.WTST_MEAS_S
inner join well W
    on upper(PPAX.PFNU_T)='WELL'
    and PPAX.PFNU_S=W.WELL_S
inner join tig_well_history TWH
    on TWH.TIG_LATEST_WELL_NAME=W.WELL_ID
    
where STUDY.BSASC_SOURCE='KVD'
    and MEAS.CONTAINING_ACT_T='WTST_MEAS'
    and MEAS.CONTAINING_ACT_S=STUDY.WTST_MEAS_S
    and MEAS.ACTIVITY_NAME in ({2})
    and TWH.DB_SLDNID = :wellsldnid
    and PRESS.DATA_VALUE>0
    