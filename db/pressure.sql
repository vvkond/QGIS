SELECT p_trpr.data_value, 
	 reservoir_part.tig_zonation_key, 
	 reservoir_part.tig_top_zone_key, 
	 reservoir_part.tig_base_zone_key, 
	 reservoir_part.reservoir_part_code, 
	 TO_CHAR(surv_meas.start_time, 'DD/MM/YYYY HH24:MI:SS'),
	 TO_CHAR(surv_meas.end_time, 'DD/MM/YYYY HH24:MI:SS')
FROM other_prod_act, 
    pfnu_prod_act_x, 
    reservoir_part, 
    wellbore_intv, 
    wellbore, 
    well, 
    tig_well_history,
	wtst_meas surv_meas, 
    wtst_meas surv_data, 
    p_trpr

WHERE
	 p_trpr.bsasc_source = 'Max Shut In' and
	 p_trpr.activity_s = surv_meas.wtst_meas_s and

	 surv_meas.containing_act_s = surv_data.wtst_meas_s and

	 surv_data.wtst_meas_s = other_prod_act.containing_act_s  and
	 other_prod_act.other_prod_act_s = pfnu_prod_act_x.production_act_s and 
	 other_prod_act.bsasc_source = 'SpecialSurveyData' and reservoir_part.reservoir_part_s=pfnu_prod_act_x.pfnu_s and

	 p_trpr.data_value > 0 and 

	 reservoir_part.reservoir_part_code in ({0}) and
	 wellbore_intv.geologic_ftr_s = reservoir_part.reservoir_part_s and
	 wellbore.wellbore_s=wellbore_intv.wellbore_s and
	 well.well_s=wellbore.well_s and
	 tig_well_history.tig_latest_well_name=well.well_id and
	 tig_well_history.DB_SLDNID = :wellsldnid
ORDER BY surv_meas.start_time, surv_meas.end_time