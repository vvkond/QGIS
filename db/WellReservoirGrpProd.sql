--- Read production for selected reservoir groups.
--- WARNING!!!! if reservoir A in GRP1 and GRP2,then in result we have 2 identical records for GRP1 and GRP2
--- @param {GRP_CODE_LIST}: list of reservoir groups
with grps as (
    select distinct 
        w.WELL_ID               WELL_ID
        ,RP.RESERVOIR_PART_CODE RP_CODE
        ,RP.RESERVOIR_PART_S    RP_ID
        ,GRP.RESERVOIR_PART_CODE GRP_CODE
        ,GRP.RESERVOIR_PART_S   GRP_ID
        ,wbi.WELLBORE_INTV_S
    from 
        WELL w
        ,WELLBORE wb
        ,RESERVOIR_PART rp
        ,WELLBORE_INTV wbi
        ---get WELLBORE_INTERVAL(SEC_TOPLG_OBJ)->is topological in RESERVOIR_PART(PRIM_TOPLG_OBJ) 
        LEFT JOIN TOPOLOGICAL_REL 
            ON 
                TOPOLOGICAL_REL.SEC_TOPLG_OBJ_S = wbi.WELLBORE_INTV_S
                AND 
                TOPOLOGICAL_REL.SEC_TOPLG_OBJ_T = 'WELLBORE_INTV'
                AND
                TOPOLOGICAL_REL.PRIM_TOPLG_OBJ_T='EARTH_POS_RGN'
        LEFT JOIN EARTH_POS_RGN 
            ON 
                TOPOLOGICAL_REL.PRIM_TOPLG_OBJ_S =EARTH_POS_RGN.EARTH_POS_RGN_S
                AND
                EARTH_POS_RGN.GEOLOGIC_FTR_T='RESERVOIR_PART'
        INNER JOIN RESERVOIR_PART GRP 
            ON 
                EARTH_POS_RGN.GEOLOGIC_FTR_S=GRP.RESERVOIR_PART_S
    ----            
    where 
        wbi.WELLBORE_S=wb.WELLBORE_S
        ---get RESERVOIR_PART of WELLBORE_INTERVAL
        and wbi.GEOLOGIC_FTR_T='RESERVOIR_PART'
        and rp.RESERVOIR_PART_S=wbi.GEOLOGIC_FTR_S
        and w.WELL_S=wb.WELL_S
)
select * 
from V_PROD_RESPART_M2 vpr
left join grps
    on vpr.WELLBORE_INTV_S=grps.WELLBORE_INTV_S
where 1=1
where 1=1 
    {FILTER_GRP}          ---- FILTER RESERVOIR GROUPS  (grps.GRP_CODE)
    {FILTER_WELLS}        ----FILTER WELLS              (vpr.WELL_ID)
     
    