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
        AND (:interval_order IS NULL OR i.tig_interval_order> :interval_order )  ---only interval placed lowwer
        ------if set ZONE ID
        AND (:zone_id        IS NULL OR i.tig_interval_order> ( 
        														SELECT I_TMP.tig_interval_order 
                                                                from tig_interval I_TMP 
                                                                where I_TMP.DB_SLDNID=:zone_id 
                                                                )   ---only interval placed lowwer
            )                                                   
		AND (:skeep_last_n_zone IS NULL  OR i.tig_interval_order< ( 
																SELECT max(I_TMP.tig_interval_order) 
                                                                from tig_interval I_TMP
                                                                	, tig_zonation Z_TMP
                                                                where Z_TMP.DB_SLDNID= :zonation_id
                                                                	AND 
                                                                	I_TMP.tig_zonation_sldnid = Z_TMP.DB_SLDNID  --------SET ZONATION ID
                                                                )-:skeep_last_n_zone+1   ---if skeep last intervals                                                                
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
		AND (:skeep_last_n_zone IS NULL  OR i.tig_interval_order< ( 
																SELECT max(I_TMP.tig_interval_order) 
                                                                from tig_interval I_TMP
                                                                	, tig_zonation Z_TMP
                                                                where Z_TMP.DB_SLDNID= :zonation_id
                                                                	AND 
                                                                	I_TMP.tig_zonation_sldnid = Z_TMP.DB_SLDNID  --------SET ZONATION ID
                                                                )-:skeep_last_n_zone+1   ---if skeep last intervals                                                                
            )
)

---GET 1 INTERVAL FOR EACH WELL  WITH ORDER >=selected interval order. If no deviation than  cd.cd_id is Null 
SELECT 
     wzi.top_depth
     , wzi.well_name
     , wzi.zonation_name
     , wzi.zone_name 
FROM 
    well_interval_pos wip
    , well_zon_intervals wzi
WHERE 
    wip.tig_well_id= wzi.tig_well_id
    AND
    wzi.tig_interval_order>= wip.well_interval_order  

