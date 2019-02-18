--- LAST INTERVAL POSITION(ORDER) FOR EACH WELL
with well_max_interval_pos as
(
    SELECT
        wh.TIG_LATEST_WELL_NAME AS well_name
        , max(i.tig_interval_order) AS well_last_interval_order
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

---GET 1 INTERVAL FOR EACH WELL   
SELECT 
     wzi.top_depth
     , wzi.well_name
     , wzi.zonation_name
     , wzi.zone_name   as target_zone
     , wzi.zone_id     AS target_zone_id
FROM 
    well_max_interval_pos wmip
    , well_zon_intervals wzi
WHERE 
    wmip.tig_well_id= wzi.tig_well_id
    AND
    wzi.tig_interval_order=wmip.well_last_interval_order

