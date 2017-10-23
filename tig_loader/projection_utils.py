from pyproj import Proj
import numpy


def _lonlat_add_get_proj(lon):
    assert isinstance(lon, float)
    return Proj('+proj=tmerc +lon_0={} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(lon))


def lonlat_add_list(lon, lat, x, y):
    p_meters = _lonlat_add_get_proj(lon)
    nx, ny = p_meters(lon, lat, errcheck=True)
    x = numpy.add(x, nx)
    y = numpy.add(y, ny)
    x, y = p_meters(x, y, inverse=True, errcheck=True)
    return x, y
