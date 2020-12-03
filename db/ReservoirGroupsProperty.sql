-- Get table of propery reservoir groups
select
    pef.QUANTITY_VALUE 
    ,pef.STRING_VALUE
    ,pef.BSASC_SOURCE PROPERY_NAME 
    ,ei.INVENTORY_OBJ_ID
    ,RP.RESERVOIR_PART_NAME 
    ,RP.RESERVOIR_PART_CODE
    ,RP.RESERVOIR_PART_S
    ,RP.ENTITY_TYPE_NM

from P_EQUIPMENT_FCL pef
    left join EQUIPMENT_ITEM ei
        on ei.EQUIPMENT_ITEM_S=pef.OBJECT_S
        and pef.OBJECT_T='EQUIPMENT_ITEM'
    left join reservoir_part rp
        on rp.RESERVOIR_PART_S=(regexp_substr(ei.INVENTORY_OBJ_ID, '[^ ]+$', 1, 1))       
where 
    ---pef.BSASC_SOURCE='GOR'
    ---RP.RESERVOIR_PART_NAME is not NULL
    1=1
        {GRP_FILTER}
