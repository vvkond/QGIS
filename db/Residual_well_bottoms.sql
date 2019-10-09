--- READ WELLS AND LAST DEVI( max(DB_SLDNID)), THAT WORK ON SELECTED DATE/RESERVOIRS/CONDUIT
--- WELLS MUST BE WITH LAT/LONG!!!!

SELECT
        t.DB_SLDNID,
        t.TIG_LATEST_WELL_NAME,
        t.TIG_LONGITUDE,
        t.TIG_LATITUDE,
        cd.TIG_DELTA_X_ORDINATE,
        cd.TIG_DELTA_Y_ORDINATE

    FROM
    (    
    SELECT 
        distinct
        well_info.DB_SLDNID,
        well_info.TIG_LATEST_WELL_NAME,
        well_info.TIG_LONGITUDE,
        well_info.TIG_LATITUDE
        ---well_info.TIG_DELTA_X_ORDINATE,
        ---well_info.TIG_DELTA_Y_ORDINATE
    FROM
            ---- #####  PRODUCTION RECORDS IN P_STD_VOL_LQ,P_STD_VOL_GAS FOR SELECTED PRODUCT 
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
            ---- #####  PRODUCTION ALLOCATION FOR RESERVOIR_PARTS
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
            ---- #####  ALL WELL->RESERVOIR_PARTS->RESERVOIR_PART_GROUPS
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
            ---- #####  WELLS INFO FROM TIG_WELL_HISTORY AND WELL DEVIATION
            INNER JOIN 
            (
                SELECT 
                    twh1.DB_SLDNID,
                    twh1.TIG_LATEST_WELL_NAME,
                    twh1.TIG_LONGITUDE,
                    twh1.TIG_LATITUDE
                FROM
                    TIG_WELL_HISTORY twh1
                WHERE
                    (NOT twh1.TIG_LONGITUDE = 0  AND NOT twh1.TIG_LATITUDE = 0)
             ) well_info
                ON well_info.TIG_LATEST_WELL_NAME=well_reservoirs_groups.WELL_ID
            
    WHERE
        (:reservoir_element_group_id IS NULL  OR GRP_S = :reservoir_element_group_id)
        AND PROD_START_TIME >= :start_date
        AND PROD_END_TIME <= :end_date
    ) t
    ---- #####  ALL DEVI FOR WELLS
    left join TIG_COMPUTED_DEVIATION cd 
        ON cd.TIG_WELL_SLDNID = t.DB_SLDNID
WHERE
    (cd.DB_SLDNID IS NULL OR cd.DB_SLDNID IN
        (
        	---- LAST DEVI FOR WELL
	        SELECT
	            MAX(cd2.DB_SLDNID)
	        FROM
	            TIG_COMPUTED_DEVIATION cd2
	        WHERE
	            cd2.TIG_WELL_SLDNID = t.DB_SLDNID
        )
    )
order by t.TIG_LATEST_WELL_NAME

     
       
