from __future__ import division

import struct

from pyproj import Proj

from tig_loader.utils import StrictInit, cached_property


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


def _get_default_proj_id(db):
    sql = '''
SELECT
    cpd.DB_SLDNID
FROM
    db_carto_projection_defs cpd
WHERE
    cpd.DB_CARTO_TYPE <> 0
'''
    return db.fetch_scalar(sql)


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
