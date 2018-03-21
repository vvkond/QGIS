# -*- coding: utf-8 -*-

from qgis.core import *
from PyQt4.QtCore import *
import numpy
import time
from processing.tools.vector import VectorWriter
import os

class StrictInit(object):
    def __init__(self, **kw):
        assert not set(kw).difference(dir(self.__class__)), '{0} does not declare fields {1}'.format(self.__class__, list(set(kw).difference(dir(self.__class__))))
        self.__dict__.update(kw)


class Args(StrictInit):
    args = None


class Exc(Exception):
    pass


class cached_property(object):

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = self.func(obj)
        setattr(obj, self.__name__, value)
        return value
        

def to_unicode(s):
    if isinstance(s, unicode):
        return s
    return s.decode('utf-8')
    

def lonlat_add_list(lon, lat, x, y):
    meterCrs = QgsCoordinateReferenceSystem()
    meterCrs.createFromProj4('+proj=tmerc +lon_0={} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(lon))
    geoCrs = QgsCoordinateReferenceSystem('epsg:4326')

    toMeters = QgsCoordinateTransform(geoCrs, meterCrs)
    toGeo = QgsCoordinateTransform(meterCrs, geoCrs)

    geoPt = QgsPoint(lon, lat)
    mPt = toMeters.transform(geoPt)

    x = numpy.add(x, mPt.x())
    y = numpy.add(y, mPt.y())
    geoPt = toGeo.transform(QgsPoint(x, y))

    return geoPt.x(), geoPt.y()

def createLayerName(layerName):
    layerList = QgsMapLayerRegistry.instance().mapLayersByName(layerName)
    if len(layerList):
        layerName = layerName + '  ' + time.strftime('%d-%m-%Y %H:%M:%S', time.localtime())
    return layerName

def memoryToShp(layer, scheme, layerName):
    settings = QSettings()
    systemEncoding = settings.value('/UI/encoding', 'System')

    ln = layerName.replace('/', '-').replace('\\', '-')
    layerFile = '/{0}_{1}_{2}.shp'.format(scheme, ln, time.strftime('%d_%m_%Y_%H_%M_%S', time.localtime()))

    (prjPath, prjExt) = os.path.splitext(QgsProject.instance().fileName())
    if not os.path.exists(prjPath):
        os.mkdir(prjPath)

    layerFileName = prjPath + layerFile

    provider = layer.dataProvider()
    fields = provider.fields()
    writer = VectorWriter(layerFileName, systemEncoding,
                          fields,
                          provider.geometryType(), provider.crs())
    features = layer.getFeatures()
    for f in features:
        try:
            l = f.geometry()
            feat = QgsFeature(f)
            feat.setGeometry(l)
            writer.addFeature(feat)
        except:
            pass

    del writer

    layerName = createLayerName(layerName)

    return QgsVectorLayer(layerFileName, layerName, 'ogr')

