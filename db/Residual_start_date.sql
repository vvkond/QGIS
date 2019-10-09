SELECT
    distinct 
    PROD_START_TIME as "[timestamp]",
    PROD_START_TIME
FROM
        ---- PRODUCTION RECORDS IN P_STD_VOL_LQ,P_STD_VOL_GAS FOR SELECTED PRODUCT 
        (
        SELECT distinct ACTIVITY_S from 
            (
            SELECT
                distinct ACTIVITY_S
            FROM
                P_STD_VOL_LQ
            WHERE DATA_VALUE > 0
                AND ACTIVITY_T='PRODUCTION_ALOC'
                AND BSASC_SOURCE = :bsasc_source
                
            UNION
            SELECT
                distinct ACTIVITY_S
            FROM
                P_STD_VOL_GAS
            WHERE DATA_VALUE > 0
                AND ACTIVITY_T='PRODUCTION_ALOC'
                AND BSASC_SOURCE = :bsasc_source
            ) p1
        ) p
        ---- PRODUCTION ALLOCATION FOR RESERVOIR_PARTS
        INNER JOIN 
            (
            SELECT distinct PFNU_S
                        ,PRODUCTION_ALOC_S
                        ,pa.PROD_START_TIME
                        ,pa.PROD_END_TIME
            FROM PRODUCTION_ALOC pa
            INNER JOIN PFNU_PROD_ACT_X ppax
                ON pa.PRODUCTION_ALOC_S = ppax.PRODUCTION_ACT_S
                AND pa.BSASC_SOURCE = 'Reallocated Production'
                AND ppax.PFNU_T = 'RESERVOIR_PART'
            ) reservoir_prods 
        ON p.ACTIVITY_S = reservoir_prods.PRODUCTION_ALOC_S
        ---- ALL WELL->RESERVOIR_PARTS->RESERVOIR_PART_GROUPS
        INNER JOIN 
            (
               -------------RESERVOIR PART AND GROUP
                select distinct 
                    w.WELL_ID
                    ,rp.RESERVOIR_PART_S
                    ,rp.RESERVOIR_PART_NAME
                    ,GRP.RESERVOIR_PART_S GRP_S
                    ,GRP.RESERVOIR_PART_NAME GRP_NAME
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
                    LEFT JOIN RESERVOIR_PART GRP 
                        ON 
                            EARTH_POS_RGN.GEOLOGIC_FTR_S=GRP.RESERVOIR_PART_S
                ----            
                where 
                    wbi.WELLBORE_S=wb.WELLBORE_S
                    ---get RESERVOIR_PART of WELLBORE_INTERVAL
                    and wbi.GEOLOGIC_FTR_T='RESERVOIR_PART'
                    and rp.RESERVOIR_PART_S=wbi.GEOLOGIC_FTR_S
                    and w.WELL_S=wb.WELL_S
                    and GRP.RESERVOIR_PART_S is not Null   ----ONLY RESERVOIRS WITH GROUPS!!!!!
            ) well_reservoirs_groups
        ON reservoir_prods.PFNU_S = well_reservoirs_groups.RESERVOIR_PART_S
WHERE
    (:reservoir_element_group_id IS NULL  OR GRP_S = :reservoir_element_group_id)        
order by PROD_START_TIME

 
   
