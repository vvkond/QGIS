--- LAST COMPUTED DEVI FOR EACH WELL
WITH well_cd as
( 
    select 
        wh.DB_SLDNID AS tig_well_id
        , wh.TIG_LONGITUDE
        , wh.TIG_LATITUDE
        , cd.DB_SLDNID as cd_id            
        , cd.TIG_DELTA_X_ORDINATE AS cd_x
        , cd.TIG_DELTA_Y_ORDINATE AS cd_y
        , cd.TIG_INDEX_TRACK_DATA AS cd_md
        , cd.TIG_Z_ORDINATE AS cd_tvd
    
    from 
    	tig_well_history wh
    	LEFT join
        tig_computed_deviation cd
        ON 
        cd.TIG_WELL_SLDNID = wh.DB_SLDNID
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
        
 
)             
---GET 1 INTERVAL FOR EACH WELL  WITH ORDER >=selected interval order. If no deviation than  cd.cd_id is Null 
SELECT 
		cd.tig_well_id
		, cd.TIG_LONGITUDE
		, cd.TIG_LATITUDE
        , cd.cd_id
        , cd.cd_x
        , cd.cd_y
        , cd.cd_md
        , cd.cd_tvd
FROM 
    well_cd cd


