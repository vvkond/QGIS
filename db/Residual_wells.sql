SELECT
    twh.DB_SLDNID,
    twh.TIG_LATEST_WELL_NAME,
    twh.TIG_LONGITUDE,
    twh.TIG_LATITUDE
FROM
    TIG_WELL_HISTORY twh
WHERE
    EXISTS
    (SELECT
        *
    FROM
        (SELECT
            *
        FROM
            P_STD_VOL_LQ
        UNION
        SELECT
            *
        FROM
            P_STD_VOL_GAS
        ) p,
        PRODUCTION_ALOC pa,
        PFNU_PROD_ACT_X ppax,
        RESERVOIR_PART rp,
        WELLBORE_INTV wbi,
        WELLBORE wb,
        WELL w,
        TOPOLOGICAL_REL tr,
        EARTH_POS_RGN epr,
        RESERVOIR_PART grp
    WHERE
        p.ACTIVITY_S = pa.PRODUCTION_ALOC_S
        AND pa.PRODUCTION_ALOC_S = ppax.PRODUCTION_ACT_S
        AND rp.RESERVOIR_PART_S = ppax.PFNU_S
        AND wbi.GEOLOGIC_FTR_S = rp.RESERVOIR_PART_S
        AND wb.WELLBORE_S = wbi.WELLBORE_S
        AND w.WELL_S = wb.WELL_S
        AND wbi.WELLBORE_INTV_S = tr.SEC_TOPLG_OBJ_S
        AND epr.EARTH_POS_RGN_S = tr.PRIM_TOPLG_OBJ_S
        AND grp.RESERVOIR_PART_S = epr.GEOLOGIC_FTR_S
        AND pa.PROD_END_TIME <= :end_date
        AND w.WELL_ID = twh.TIG_LATEST_WELL_NAME
        AND p.DATA_VALUE > 0
        AND pa.BSASC_SOURCE = 'Reallocated Production'
        AND p.BSASC_SOURCE = :bsasc_source
        AND :start_date <= pa.PROD_START_TIME
        AND(NOT twh.TIG_LONGITUDE = 0
        OR NOT twh.TIG_LATITUDE = 0)
        AND(:reservoir_element_group_id IS NULL
        OR grp.RESERVOIR_PART_S = :reservoir_element_group_id)
    )