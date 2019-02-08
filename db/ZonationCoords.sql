--- INTERVAL POSITION(ORDER) FOR EACH WELL
with well_interval_pos as
(
    SELECT
        wh.TIG_LATEST_WELL_NAME AS well_name
        , min(i.tig_interval_order) AS well_interval_order
        , wh.DB_SLDNID AS tig_well_id
    FROM tig_interval I 
        , TIG_ZONATION z
        , tig_well_interval wi
        , tig_well_history wh
    WHERE
        I.tig_zonation_sldnid = z.DB_SLDNID  --------SET ZONATION ID
        AND wh.DB_SLDNID = wi.TIG_WELL_SLDNID   
        AND wi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
        ---VARIABLES
        AND wh.TIG_LATEST_WELL_NAME = :well_id
        AND z.DB_SLDNID = :zonation_id
        ------if set ZONE ORDER
        AND (:interval_order IS NULL OR i.tig_interval_order>= :interval_order )
        ------if set ZONE ID
        AND (:zone_id        IS NULL OR i.tig_interval_order>= ( SELECT I_TMP.tig_interval_order 
                                                                from tig_interval I_TMP 
                                                                where I_TMP.DB_SLDNID=:zone_id 
                                                                )
            )
    group by 
        wh.TIG_LATEST_WELL_NAME, wh.DB_SLDNID
)
---ALL INTERVALS FOR EACH WELL
,well_zon_intervals as       
(
    SELECT
        wh.TIG_LATEST_WELL_NAME AS well_name
        , TRIM(z.TIG_DESCRIPTION) AS zonation_name
        , TRIM(i.TIG_INTERVAL_NAME) AS zone_name
        , wi.TIG_TOP_POINT_DEPTH AS top_depth
        , wi.TIG_BOT_POINT_DEPTH AS bottom_depth
        , wh.DB_SLDNID AS tig_well_id
        , z.DB_SLDNID AS zonation_id
        , wi.DB_SLDNID AS well_zone_id
        , i.DB_SLDNID AS zone_id
        , wh.TIG_LONGITUDE
        , wh.TIG_LATITUDE
        , i.TIG_INTERVAL_NAME 
        , i.tig_interval_order
        , i.tig_level
        ,z.TIG_ZONATION_PARAMS
    FROM
        tig_well_interval wi,
        tig_well_history wh,
        tig_interval i,
        tig_zonation z
    WHERE
        wh.DB_SLDNID = wi.TIG_WELL_SLDNID
        AND wi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
        AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
        ---VARIABLES
        AND wh.TIG_LATEST_WELL_NAME = :well_id        
        AND z.DB_SLDNID = :zonation_id 
)
--- WELL COMPUTE DEVIATION. ONLY PUBLIC RECORDS!!!
,well_cd as
( 
    select 
        wh.DB_SLDNID AS tig_well_id
        , cd.DB_SLDNID as cd_id            
        , cd.TIG_DELTA_X_ORDINATE AS cd_x
        , cd.TIG_DELTA_Y_ORDINATE AS cd_y
        , cd.TIG_INDEX_TRACK_DATA AS cd_md
        , cd.TIG_Z_ORDINATE AS cd_tvd
    
    from 
        tig_computed_deviation cd 
        , tig_well_history wh
    where 
        wh.TIG_LATEST_WELL_NAME = :well_id
        AND
        cd.DB_SLDNID IN
        (
        SELECT
            MAX(cd2.DB_SLDNID)
        FROM
            tig_computed_deviation cd2
        WHERE
            cd2.TIG_WELL_SLDNID = wh.DB_SLDNID
			AND(cd2.TIG_GLOBAL_DATA_FLAG = 1   OR :only_pub_devi IS NULL)            
        )
),
---INFO ABOUT VARIABLE 
var_info as
(
    select 
        v.TIG_VARIABLE_SHORT_NAME AS parameter_name
        , v.DB_SLDNID AS parameter_id
        , v.TIG_VARIABLE_SHORT_NAME
        , v.TIG_VARIABLE_REAL_DFLT
        , v.TIG_VARIABLE_REAL_MIN
        , v.TIG_VARIABLE_REAL_MAX
        , v.TIG_VARIABLE_REAL_NULL
    from tig_variable v
    where 
        v.TIG_VARIABLE_SHORT_NAME = 'TopTVD'
        AND v.TIG_VARIABLE_TYPE = 2
    
)              

---GET 1 INTERVAL FOR EACH WELL  WITH ORDER >=selected interval order. If no deviation than  cd.cd_id is Null 
SELECT 
		wzi.well_name
        , wzi.zonation_name
        , wzi.zone_name
        , wzi.top_depth
        , wzi.bottom_depth
        , wzi.tig_well_id
        , wzi.zonation_id
        , wzi.well_zone_id
        , wzi.zone_id
        , wzi.TIG_LONGITUDE
        , wzi.TIG_LATITUDE
        , wzi.TIG_INTERVAL_NAME 
        , wzi.tig_interval_order
        , wzi.tig_level
        , wzi.TIG_ZONATION_PARAMS
        , cd.cd_id
        , cd.cd_x
        , cd.cd_y
        , cd.cd_md
        , cd.cd_tvd
        , vi.parameter_name
        , vi.parameter_id
        , vi.TIG_VARIABLE_SHORT_NAME
        , vi.TIG_VARIABLE_REAL_DFLT
        , vi.TIG_VARIABLE_REAL_MIN
        , vi.TIG_VARIABLE_REAL_MAX
        , vi.TIG_VARIABLE_REAL_NULL
FROM 
    well_interval_pos wip
    , well_zon_intervals wzi
    left join     
        well_cd cd
        on cd.tig_well_id= wzi.tig_well_id
    , var_info vi
WHERE 
    wip.tig_well_id= wzi.tig_well_id
    AND
    wip.well_interval_order=wzi.tig_interval_order

