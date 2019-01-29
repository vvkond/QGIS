from __future__ import division

import struct

#from pyproj import Proj
WGS84='EPSG:4326'
WGS84_UTM_ZONE9N='EPSG:32639'
PULKOVO='EPSG:4284'
PULKOVO_GK_ZONE9N='EPSG:28409'
DEFAULT_LATLON_PRJ=WGS84  # default projection for lat/lon
DEFAULT_LAYER_PRJ=WGS84     # default projection if no default config in base
#CRS_FIX_IDX=0     #index of type fix crs conversion

AUTO_LOAD_DEFAULT_PROJ_NAME='_qgis_' # in projection comment use format: "fix_id:0:SomeText" "fix_id:1:SomeText"

from QgisPDS.utils import StrictInit, cached_property


'''
Interational Metres
Common Feet
International Feet = Indian Feet (1959 legal)
Imperial Feet
Indian Feet (curent Burma & Thailand)
Indian Feet (1963, current India & Pakistan)
Indian Feet (1896, West Malaysia & Singapore)
Indian Feet (East Malaysia)
Indian Chains
Indian Yards
'''

'''
Radians
Degrees of Arc
Minutes of Arc
Packed Degrees|Minutes|Seconds
Grads of Arc
Mils of Arc
'''
#===============================================================================
# 
#===============================================================================
class QgisProjectionConfig():
    @classmethod
    def get_default_latlon_prj_epsg(cls):
        return DEFAULT_LATLON_PRJ
    @classmethod
    def get_default_layer_prj_epsg(cls):
        return DEFAULT_LAYER_PRJ
#===============================================================================
# 
#===============================================================================
def get_qgis_crs_transform(sourceCrs,destSrc,CRS_FIX_IDX=0):
    """
        @info: function for fix stored in incorrect projection data.  
    """
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMessageLog
    #QgsMessageLog.logMessage(u"CRS_FIX_IDX {0}".format(CRS_FIX_IDX), tag="QgisPDS.debug")
    if CRS_FIX_IDX==0:
        return QgsCoordinateTransform(sourceCrs ,destSrc)
    elif CRS_FIX_IDX==1: #lat/lon entered in Pulkovo_GKZone9N as WGS84_Zone9N and converrted to WGS84. Need convert WGS84->WGS84_Zone9N and read as Pulkovo_GKZone9N X without 9
        QgsMessageLog.logMessage(u"source->dest crs {0}: {1}".format(sourceCrs.srsid(),destSrc.srsid()), tag="QgisPDS.debug")
        if sourceCrs.srsid()==QgsCoordinateReferenceSystem(QgisProjectionConfig.get_default_latlon_prj_epsg()).srsid():
            sourceCrs=QgsCoordinateReferenceSystem(WGS84)
            destSrc=QgsCoordinateReferenceSystem(WGS84_UTM_ZONE9N)
            QgsMessageLog.logMessage(u"changed to source->dest crs {0}: {1}".format(sourceCrs.srsid(),destSrc.srsid()), tag="QgisPDS.debug")
        elif destSrc.srsid()==QgsCoordinateReferenceSystem(QgisProjectionConfig.get_default_latlon_prj_epsg()).srsid():
            sourceCrs=QgsCoordinateReferenceSystem(WGS84_UTM_ZONE9N)
            destSrc=QgsCoordinateReferenceSystem(WGS84)
            QgsMessageLog.logMessage(u"changed to source->dest crs {0}: {1}".format(sourceCrs.srsid(),destSrc.srsid()), tag="QgisPDS.debug")
            
        return QgsCoordinateTransform(sourceCrs ,destSrc)
    

#===============================================================================
# 
#===============================================================================
def get_qgis_prj_default_projection(db):
    
    tig_projections = TigProjections(db=db)
    proj = tig_projections.get_projection(tig_projections.default_projection_id)
    if proj is not None:
        proj4String = 'PROJ4:'+proj.qgis_string

    QgsCoordinateReferenceSystem('EPSG:..')
    
    proj4String = 'PROJ4:'+proj.qgis_string
    destSrc = QgsCoordinateReferenceSystem()
    destSrc.createFromProj4(proj.qgis_string)

    
    pass


#===============================================================================
# 
#===============================================================================
def double_to_degrees(val):
    sign = 1
    if val < 0:
        sign = -1
        val = -val
    seconds = val % 100
    minutes = val // 100 % 100
    degrees = val // 10000
    return sign * (degrees + minutes / 60 + seconds / 3600)




class UnsupportedProjection(Exception):
    pass


def prj_assert(cond, *args, **kwargs):
    if not cond:
        raise UnsupportedProjection(*args, **kwargs)


class Proj4Args(dict):
    def __init__(self, **kw):
        dict.__init__(self, **kw)
        self.__dict__.update(kw)


class TigProjection(StrictInit):

    @cached_property
    def proj4_args(self):
        raise NotImplementedError()

    @cached_property
    def proj4_string(self):
        if self.proj4_args is None:
            return None
        return ' '.join('+' + k + '=' + str(v) for k, v in self.proj4_args.iteritems())

    @cached_property
    def proj4_object(self):
        if self.proj4_string is None:
            return None
        return Proj(self.proj4_string)

    @cached_property
    def esri_string(self):
        return None

    @cached_property
    def qgis_string(self):
        return None


class Geodetic(TigProjection):

    @classmethod
    def from_row(cls, p_type, units, **_kw):
        prj_assert(p_type == 0, 'P_TYPE')
        prj_assert(units == 1002, 'UNITS')
        return cls()

    @cached_property
    def proj4_args(self):
        return Proj4Args(
            #units='m',
            proj='lonlat',
            ellps='WGS84',
            datum='WGS84',
            no_defs=True,
        )

    @cached_property
    def esri_string(self):
        return '''
GEOGCS["GCS_WGS_1984",
    DATUM["D_WGS_1984",
        SPHEROID["WGS_1984",6378137,298.257223563]],
    PRIMEM["Greenwich",0],
    UNIT["Degree",0.017453292519943295]]
'''

    @cached_property
    def qgis_string(self):
        return '''
+proj=longlat +datum=WGS84 +no_defs
'''


class Utm(TigProjection):
    params = None
    '''
    db_carto_projection_defs.DB_CARTO_DEF_PARAMETERS
        struct.unpack('>dddI' 01000001000110110111011101000000 - northern
                               11000001000110110111011101000000 - southern)
        (semi-major axis, semi-minor axis, lon_0 / 10000 degrees)
    '''
    @classmethod
    def from_row(cls, p_type, units, p, **_kw):
        prj_assert(p_type == 1, 'P_TYPE')
        prj_assert(units == 1, 'UNITS')
        if type(p) is buffer:
            prj_assert(len(p) >= 8 * 3 + 4, 'len(p)')
            s = p[:8 * 3 + 4]
        else:
            prj_assert(p.size() >= 8 * 3 + 4, 'len(p)')
            s = p.read(1, 8 * 3 + 4)
        return cls(params=struct.unpack('>dddI', s))

    @cached_property
    def proj4_args(self):
        params = self.params
        return Proj4Args(
            proj='utm',
            a=params[0],
            b=params[1],
            lon_0=double_to_degrees(params[2]),
            south=(params[3] >> 31) != 0,
            to_meter=1,
        )

    _north = '''
PROJCS["UTM_Zone_0_Northern_Hemisphere",
    GEOGCS["GCS_unnamed ellipse",
        DATUM["D_unknown",
            SPHEROID["Unknown",{a},{flattening}]],
        PRIMEM["Greenwich",0],
        UNIT["Degree",0.017453292519943295]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["latitude_of_origin",0],
    PARAMETER["central_meridian",{lon_0}],
    PARAMETER["scale_factor",0.9996],
    PARAMETER["false_easting",500000],
    PARAMETER["false_northing",0],
    UNIT["Meter",1]]
'''.strip()

    @cached_property
    def esri_string(self):
        p = self.proj4_args
        if p.south:
            return
        if p.a < 0 or p.a - p.b <= 0:
            return
        return self._north.format(flattening=p.a / (p.a - p.b), **p)

    _qgis = '''
+proj=tmerc +lat_0=0 +lon_0={lon_0} +k=0.9996 +x_0=500000 +y_0=0 +datum=WGS84 +units=m +no_defs
'''.strip()

    @cached_property
    def qgis_string(self):
        p = self.proj4_args
        if p.south:
            return
        if p.a < 0 or p.a - p.b <= 0:
            return
        return self._qgis.format(**p)


class Tm(TigProjection):
    params = None
    '''
    >dddddddd
    (
    semi-major,
    semi-minor,
    scale factor at central meridian,
    0 ???
    long of central meridian / 10000 degrees
    lat of north-south origin / 10000 degrees
    false easting (in ext units)
    false northing (in ext units)
    '''
    @classmethod
    def from_row(cls, p_type, p, **_kw):
        prj_assert(p_type == 1, 'P_TYPE')
        if type(p) is buffer:
            prj_assert(len(p) >= 64, 'len(p)')
            s = p[:64]
        else:
            prj_assert(p.size() >= 64, 'len(p)')
            s = p.read(1, 64)
        params = struct.unpack('>dddddddd', s)
        prj_assert(params[3] == 0, 'params[3]')
        return cls(params=params)

    @cached_property
    def proj4_args(self):
        params = self.params
        return Proj4Args(
            proj='tmerc',
            a=params[0],
            b=params[1],
            k=params[2],
            lon_0=double_to_degrees(params[4]),
            lat_0=double_to_degrees(params[5]),
            x_0=params[6],
            y_0=params[7],
            to_meter=1,
        )

    _esri = '''
PROJCS["Transverse_Mercator",
    GEOGCS["GCS_unnamed ellipse",
        DATUM["D_unknown",
            SPHEROID["Unknown",{a},{flattening}]],
        PRIMEM["Greenwich",0],
        UNIT["Degree",0.017453292519943295]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["latitude_of_origin",{lat_0}],
    PARAMETER["central_meridian",{lon_0}],
    PARAMETER["scale_factor",{k}],
    PARAMETER["false_easting",{x_0}],
    PARAMETER["false_northing",{y_0}],
    UNIT["Meter",1]]
'''.strip()

    @cached_property
    def esri_string(self):
        p = self.proj4_args
        if p.a < 0 or p.a - p.b <= 0:
            return
        return self._esri.format(flattening=p.a / (p.a - p.b), **p)


#     _qgis = '''
# +proj=tmerc +lat_0={lat_0} +lon_0={lon_0} +k={k} +x_0={x_0} +y_0={y_0} +ellps=krass +towgs84=24.47,-130.89,-81.56,-0,-0,0.13,-0.22 +units=m +no_defs
# '''.strip()
    _qgis = '''
    +a={a} +lon_0={lon_0} +to_meter={to_meter} +k={k} +y_0={y_0} +b={b} +proj={proj} +x_0={x_0} +lat_0={lat_0} +no_defs
'''.strip()

    @cached_property
    def qgis_string(self):
        p = self.proj4_args
        if p.a < 0 or p.a - p.b <= 0:
            return
        return self._qgis.format(**p)


class TigProjections(StrictInit):
    db = None

    @cached_property
    def cache(self):
        return {}

    def get_projection(self, proj_id):
        try:
            return self.cache[proj_id]
        except KeyError:
            proj4 = self._get_projection(proj_id)
            self.cache[proj_id] = proj4
            return proj4

    def _get_projection(self, proj_id):
        return _get_tig_projection(self.db, proj_id)

    @cached_property
    def default_projection_id(self):
        return _get_default_proj_id(self.db)
    @cached_property
    def default_projection_comment(self):
        return _get_default_proj_id(self.db,return_col='db_comment')
    @cached_property
    def fix_id(self):
        result=None
        try:
            result=self.default_projection_comment.split("fix_id:")[1].split(":")[0]
            result=int(result)
        except:pass
        return result
#===============================================================================
# 
#===============================================================================
def _get_default_proj_id(db,return_col='db_sldnid'):
    """
        @info: if have projection with specifiying name then return it else return project default projection id
    """
    sql = '''
SELECT 
    ---*
    {return_col}
FROM (
    SELECT
        *
    FROM
        db_carto_projection_defs cpd
    WHERE
        cpd.DB_CARTO_USER_NAME='{tig_proj_name}' ---by default _qgis_
    union all     
    SELECT
        *
    FROM
        db_carto_projection_defs cpd
    WHERE
        cpd.DB_CARTO_TYPE <> 0
    )
where ROWNUM=1            
'''.format(tig_proj_name=AUTO_LOAD_DEFAULT_PROJ_NAME
           ,return_col=return_col
           )
    return db.fetch_scalar(sql)

#===============================================================================
# 
#===============================================================================
def _get_tig_projection(db, proj_id):
    sql = '''
SELECT
    cpd.DB_SLDNID AS "id",
    pj.DB_CARTO_REFERENCE_CODE AS "pj_ref",
    cpd.DB_CARTO_DEF_PARAMS_TYPE AS "p_type",
    cpd.DB_CARTO_DEF_PARAMETERS AS "p",
    cpd.DB_CARTO_PROJECTN_SLDNID AS "pr_id",
    cpd.DB_CARTO_DATUM_SLDNID AS "datum_id",
    cpd.DB_CARTO_EXTERNAL_UNITS AS "units",
    cpd.DB_CARTO_TYPE AS "is_default"
FROM
    db_carto_projection_defs cpd,
    (SELECT
        cp.DB_SLDNID,
        cp.DB_CARTO_REFERENCE_CODE
    FROM
        db_carto_projections cp
    UNION
    SELECT
        pj.DB_SLDNID,
        pj.DB_CARTO_REFERENCE_CODE
    FROM
        GLOBAL.db_carto_projections pj
    ) pj
WHERE
    pj.DB_SLDNID = cpd.DB_CARTO_PROJECTN_SLDNID
    AND(cpd.DB_CARTO_TYPE <> 0
    AND :pid = 0
    OR cpd.DB_SLDNID = :pid)
'''
    row = db.fetch_assoc(sql, pid=proj_id)

    if row is None:
        return None

    return get_tig_projection(**row)

#===============================================================================
# 
#===============================================================================
def get_tig_projection(pj_ref, **kw):
    try:
        constructor = _proj_by_ref_code[pj_ref]
    except KeyError:
        return None
    try:
        return constructor.from_row(pr_ref=pj_ref, **kw)
    except UnsupportedProjection:
        return None


_proj_by_ref_code = {
    2: Geodetic,
    3: Utm,
    11: Tm,
}
