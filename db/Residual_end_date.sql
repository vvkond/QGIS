SELECT
    PROD_END_TIME as "[timestamp]",
    PROD_END_TIME
--    TO_CHAR(PROD_END_TIME, 'DD.MM.YYYY')
FROM
    (SELECT
        PROD_END_TIME
    FROM
        (SELECT
            pa.PROD_START_TIME,
            pa.PROD_END_TIME,
            w.WELL_ID,
            grp.RESERVOIR_PART_CODE,
            rp.RESERVOIR_PART_CODE RESERVOIR_PART_CODE2,
            p.DATA_VALUE LiquidVolume
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
            RESERVOIR_PART grp,
            TIG_WELL_HISTORY twh
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
            AND w.WELL_ID = twh.TIG_LATEST_WELL_NAME
            AND p.DATA_VALUE > 0
            AND pa.BSASC_SOURCE = 'Reallocated Production'
            AND p.BSASC_SOURCE = :bsasc_source
            AND(NOT twh.TIG_LONGITUDE = 0
            OR NOT twh.TIG_LATITUDE = 0)
            AND(:reservoir_element_group_id IS NULL
            OR grp.RESERVOIR_PART_S = :reservoir_element_group_id)
        )
    WHERE
        PROD_END_TIME >= :start_date
    GROUP BY
        PROD_END_TIME
    )
ORDER BY
    PROD_END_TIME