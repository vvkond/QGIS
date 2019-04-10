prod_sql=u"""SELECT
    well_completion.well_id, well_completion.well_completion_id,
    PRODUCTION_ALOC.PROD_START_TIME,
    PRODUCTION_ALOC.PROD_END_TIME,
    oil_mass.DATA_VALUE oil_mass,
    oil_vol.data_value oil_vol,
    con_vol.data_value condensate_vol,
    cond_mass.DATA_VALUE condensate_mass,
    water_mass.data_value water_mass,
    wat_vol.data_value water_vol,
    water_inj_vol.DATA_VALUE water_inj_vol,
    t_nat_gas.nat_gas gas_vol,
    t_free_gas.free_gas free_gas_vol,
    t_dis_gas.dis_gas dis_gas_vol,
    P_FLUID_CMPN_RTO.DATA_VALUE gor,
    plfact.DATA_VALUE plfactor,
    inj_water.DATA_VALUE inj_water,
    inj_gas.DATA_VALUE inj_gas,
    crude_oil.DATA_VALUE crude_oil,
    produced_water.DATA_VALUE produced_water,
    WELL_CMPL_STA.R_CMPL_STA_NAME sta_name,
    CASE WHEN PROD_PORT_TIME.data_value  = -999 THEN -999 ELSE  PROD_PORT_TIME.data_value/3600/24 END time_prod,
    CASE WHEN INJ_PORT_TIME.data_value  = -999 THEN -999 ELSE  INJ_PORT_TIME.data_value/3600/24 END time_inj,
	  p_equipment_fcl.quantity_value choke,
    p_well_cmpl_dntm.data_value uschdo,
    p_well_cmpl_dntm_1.data_value schdo,
	 -- nat_gas.DATA_VALUE nat_gas,
    P_TRPR.DATA_VALUE/100000 thflpr,
    natural_gas.DATA_VALUE rfgspd
FROM
    well,
    well_completion
--
      inner join pfnu_prod_act_x on PFNU_PROD_ACT_X.PFNU_S = WELL_COMPLETION.WELL_COMPLETION_S
      inner join production_aloc on PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S
      inner join P_FLUID_CMPN_RTO on PRODUCTION_ALOC.PRODUCTION_ALOC_S = P_FLUID_CMPN_RTO.ACTIVITY_S and P_FLUID_CMPN_RTO.BSASC_SOURCE='gas-oil ratio' and P_FLUID_CMPN_RTO.DATA_VALUE IN (1,2,3,4,5)
--
      left join p_std_vol_lq oil_mass on PRODUCTION_ALOC.PRODUCTION_ALOC_S = OIL_MASS.ACTIVITY_S and oil_mass.BSASC_SOURCE = 'crude oil'
      left join p_std_vol_lq water_mass on PRODUCTION_ALOC.PRODUCTION_ALOC_S = WATER_MASS.ACTIVITY_S and water_mass.BSASC_SOURCE = 'produced water'
      left join p_std_vol_lq cond_mass on PRODUCTION_ALOC.PRODUCTION_ALOC_S = cond_mass.ACTIVITY_S and cond_mass.BSASC_SOURCE = 'condensate'
      --left join p_std_vol_gas gas_vol on PRODUCTION_ALOC.PRODUCTION_ALOC_S = GAS_VOL.ACTIVITY_S and gas_vol.BSASC_SOURCE = 'natural gas' and gas_vol.DATA_VALUE <> '-999'
      LEFT JOIN
(
select distinct
       pfnu_port.pfnu_s WELL_COMPLETION_S,
       p_std_vol_gas.start_time start_time,
       p_std_vol_gas.data_value free_gas
from
     pfnu_port
     INNER JOIN aloc_flw_strm ON pfnu_port.pfnu_port_s = aloc_flw_strm.pfnu_port_s
     INNER JOIN p_std_vol_gas ON aloc_flw_strm.aloc_flw_strm_s = p_std_vol_gas.object_s
WHERE p_std_vol_gas.bsasc_source = 'free gas'
) t_free_gas ON WELL_COMPLETION.WELL_COMPLETION_S = t_free_gas.WELL_COMPLETION_S AND PRODUCTION_ALOC.start_time = t_free_gas.start_time
 LEFT JOIN
(
select distinct
       pfnu_port.pfnu_s WELL_COMPLETION_S,
       p_std_vol_gas.start_time start_time,
       p_std_vol_gas.data_value nat_gas
from
     pfnu_port
     INNER JOIN aloc_flw_strm ON pfnu_port.pfnu_port_s = aloc_flw_strm.pfnu_port_s
     INNER JOIN p_std_vol_gas ON aloc_flw_strm.aloc_flw_strm_s = p_std_vol_gas.object_s
WHERE p_std_vol_gas.bsasc_source = 'natural gas'
) t_nat_gas ON WELL_COMPLETION.WELL_COMPLETION_S = t_nat_gas.WELL_COMPLETION_S AND PRODUCTION_ALOC.start_time = t_nat_gas.start_time
LEFT JOIN
(
select distinct
       pfnu_port.pfnu_s WELL_COMPLETION_S,
       p_std_vol_gas.start_time start_time,
       p_std_vol_gas.data_value dis_gas
from
     pfnu_port
     INNER JOIN aloc_flw_strm ON pfnu_port.pfnu_port_s = aloc_flw_strm.pfnu_port_s
     INNER JOIN p_std_vol_gas ON aloc_flw_strm.aloc_flw_strm_s = p_std_vol_gas.object_s
WHERE p_std_vol_gas.bsasc_source = 'dissolved gas'
) t_dis_gas ON WELL_COMPLETION.WELL_COMPLETION_S = t_dis_gas.WELL_COMPLETION_S AND PRODUCTION_ALOC.start_time = t_dis_gas.start_time
      --left join p_std_vol_gas gas_vol_2 on PRODUCTION_ALOC.PRODUCTION_ALOC_S = GAS_VOL_2.ACTIVITY_S and gas_vol_2.BSASC_SOURCE = 'dissolved gas' and gas_vol_2.DATA_VALUE <> '-999'
      left join p_std_vol_lq water_inj_vol on PRODUCTION_ALOC.PRODUCTION_ALOC_S = water_inj_vol.ACTIVITY_S and water_inj_vol.BSASC_SOURCE = 'injected water'
--
      left join
        ( select pfnu_port.pfnu_s, liquid_vol.start_time, liquid_vol.data_value
          from pfnu_port, aloc_flw_strm, p_std_vol_lq liquid_vol
          where
          aloc_flw_strm.pfnu_port_s = pfnu_port.pfnu_port_s and
          liquid_vol.object_s = aloc_flw_strm.aloc_flw_strm_s and liquid_vol.bsasc_source = 'oilvol') oil_vol
        on oil_vol.pfnu_s = well_completion.well_completion_s and oil_vol.START_TIME = PRODUCTION_ALOC.START_TIME
      left join
        ( select pfnu_port.pfnu_s, liquid_vol.start_time, liquid_vol.data_value
          from pfnu_port, aloc_flw_strm, p_std_vol_lq liquid_vol
          where
          aloc_flw_strm.pfnu_port_s = pfnu_port.pfnu_port_s and
          liquid_vol.object_s = aloc_flw_strm.aloc_flw_strm_s and liquid_vol.bsasc_source = 'watvol') wat_vol
        on wat_vol.pfnu_s = well_completion.well_completion_s and wat_vol.START_TIME = PRODUCTION_ALOC.START_TIME
      left join
        ( select pfnu_port.pfnu_s, liquid_vol.start_time, liquid_vol.data_value
          from pfnu_port, aloc_flw_strm, p_std_vol_lq liquid_vol
          where
          aloc_flw_strm.pfnu_port_s = pfnu_port.pfnu_port_s and
          liquid_vol.object_s = aloc_flw_strm.aloc_flw_strm_s and liquid_vol.bsasc_source = 'convol') con_vol
        on con_vol.pfnu_s = well_completion.well_completion_s and con_vol.START_TIME = PRODUCTION_ALOC.START_TIME
     left join 
      (select P_ALLOC_FACTOR.DATA_VALUE,P_ALLOC_FACTOR.ACTIVITY_S, ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID from
      P_ALLOC_FACTOR,FLW_STRM_ALOC_FCT,ALOC_FLW_STRM
      where P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S
        AND ALOC_FLW_STRM.ALOC_FLW_STRM_S = FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S AND P_ALLOC_FACTOR.DATA_VALUE <> -999 AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID = 'pipeline') plfact on PRODUCTION_ALOC.PRODUCTION_ALOC_S = plfact.ACTIVITY_S
     left join
      (select P_ALLOC_FACTOR.DATA_VALUE,P_ALLOC_FACTOR.ACTIVITY_S, ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID from
      P_ALLOC_FACTOR,FLW_STRM_ALOC_FCT,ALOC_FLW_STRM
      where P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S
        AND ALOC_FLW_STRM.ALOC_FLW_STRM_S = FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S AND P_ALLOC_FACTOR.DATA_VALUE <> -999 AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID = 'injected water') inj_water on PRODUCTION_ALOC.PRODUCTION_ALOC_S = inj_water.ACTIVITY_S
     left join
      (select P_ALLOC_FACTOR.DATA_VALUE,P_ALLOC_FACTOR.ACTIVITY_S, ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID from
      P_ALLOC_FACTOR,FLW_STRM_ALOC_FCT,ALOC_FLW_STRM
      where P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S
        AND ALOC_FLW_STRM.ALOC_FLW_STRM_S = FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S AND P_ALLOC_FACTOR.DATA_VALUE <> -999 AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID = 'injected gas') inj_gas on PRODUCTION_ALOC.PRODUCTION_ALOC_S = inj_gas.ACTIVITY_S
     left join
      (select P_ALLOC_FACTOR.DATA_VALUE,P_ALLOC_FACTOR.ACTIVITY_S, ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID from
      P_ALLOC_FACTOR,FLW_STRM_ALOC_FCT,ALOC_FLW_STRM
      where P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S
        AND ALOC_FLW_STRM.ALOC_FLW_STRM_S = FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S AND P_ALLOC_FACTOR.DATA_VALUE <> -999 AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID = 'crude oil') crude_oil on PRODUCTION_ALOC.PRODUCTION_ALOC_S = crude_oil.ACTIVITY_S
     left join
      (select P_ALLOC_FACTOR.DATA_VALUE,P_ALLOC_FACTOR.ACTIVITY_S, ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID from
      P_ALLOC_FACTOR,FLW_STRM_ALOC_FCT,ALOC_FLW_STRM
      where P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S
        AND ALOC_FLW_STRM.ALOC_FLW_STRM_S = FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S AND P_ALLOC_FACTOR.DATA_VALUE <> -999 AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID = 'produced water') produced_water on PRODUCTION_ALOC.PRODUCTION_ALOC_S = produced_water.ACTIVITY_S
     left join
      (select P_ALLOC_FACTOR.DATA_VALUE,P_ALLOC_FACTOR.ACTIVITY_S, ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID from
      P_ALLOC_FACTOR,FLW_STRM_ALOC_FCT,ALOC_FLW_STRM
      where P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S
        AND ALOC_FLW_STRM.ALOC_FLW_STRM_S = FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S AND P_ALLOC_FACTOR.DATA_VALUE <> -999 AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID = 'natural gas') natural_gas on PRODUCTION_ALOC.PRODUCTION_ALOC_S = natural_gas.ACTIVITY_S
     left join WELL_CMPL_STA on WELL_CMPL_STA.CAUSED_BY_S = PRODUCTION_ALOC.PRODUCTION_ALOC_S
     left join 
        p_pfnu_port_time prod_port_time on PRODUCTION_ALOC.PRODUCTION_ALOC_S = prod_port_time.ACTIVITY_S and prod_port_time.BSASC_SOURCE = 'production'
     left join 
        p_pfnu_port_time inj_port_time on PRODUCTION_ALOC.PRODUCTION_ALOC_S = inj_port_time.ACTIVITY_S and inj_port_time.BSASC_SOURCE = 'water injection'
     left join p_equipment_fcl on production_aloc.production_aloc_s = p_equipment_fcl.activity_s
     left join p_well_cmpl_dntm on production_aloc.production_aloc_s = p_well_cmpl_dntm.activity_s and well_completion.well_completion_s = p_well_cmpl_dntm.object_s and p_well_cmpl_dntm.r_downtime_rsn_nm = 'unscheduled'
     left join p_well_cmpl_dntm p_well_cmpl_dntm_1 on production_aloc.production_aloc_s = p_well_cmpl_dntm_1.activity_s and well_completion.well_completion_s = p_well_cmpl_dntm_1.object_s and p_well_cmpl_dntm_1.r_downtime_rsn_nm = 'scheduled'
    /* left join
      (select P_ALLOC_FACTOR.DATA_VALUE,P_ALLOC_FACTOR.ACTIVITY_S, ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID from
      P_ALLOC_FACTOR,FLW_STRM_ALOC_FCT,ALOC_FLW_STRM
      where P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S
        AND ALOC_FLW_STRM.ALOC_FLW_STRM_S = FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S AND P_ALLOC_FACTOR.DATA_VALUE <> -999 AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID = 'natural gas') nat_gas on PRODUCTION_ALOC.PRODUCTION_ALOC_S = nat_gas.ACTIVITY_S*/
     left join P_TRPR on P_TRPR.ACTIVITY_S = PRODUCTION_ALOC.PRODUCTION_ALOC_S and P_TRPR.DATA_VALUE <> '-999'
WHERE WELL.WELL_S = WELL_COMPLETION.WELL_S
  AND (oil_mass.DATA_VALUE is null or oil_mass.DATA_VALUE<>-999) --null event filter
  AND (water_mass.DATA_VALUE is null or water_mass.DATA_VALUE<>-999) --null event filter
  AND (water_inj_vol.DATA_VALUE is null or water_inj_vol.DATA_VALUE<>-999)
  --and well_completion.well_id = 'chi_024_ST1' 
  --and ((t_nat_gas.nat_gas is not null and t_free_gas.free_gas is not null) or (t_nat_gas.nat_gas is not null and t_dis_gas.dis_gas is not null) or (t_nat_gas.nat_gas is null and t_free_gas.free_gas is null and t_dis_gas.dis_gas is null))
 and (  (t_nat_gas.nat_gas is not null))
    {FILTER_WELLS} 
order by
    well_completion.well_id, PRODUCTION_ALOC.START_TIME, well_completion.well_completion_id"""
