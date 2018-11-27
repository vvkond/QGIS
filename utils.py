# -*- coding: utf-8 -*-

from qgis.core import *
from PyQt4.QtCore import *
import numpy
import time
from processing.tools.vector import VectorWriter
import os
import json
import sys

MAX_FILE_NAME_SIZE=224

class StrictInit(object):
    def __init__(self, **kw):
        assert not set(kw).difference(dir(self.__class__)), u'{0} does not declare fields {1}'.format(self.__class__, list(set(kw).difference(dir(self.__class__))))
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
        

def to_unicode(s,codding='utf-8'):
    if isinstance(s, unicode):
        return s
    return s.decode(codding)

def start_edit_layer(layer):
    if not layer.isEditable():
        filter_str=layer.subsetString()
        layer.setCustomProperty("subsetStringBckp", filter_str)
        layer.setSubsetString("")
        layer.startEditing()

def stop_edit_layer(layer):
    layer.commitChanges()  
    filter_str=layer.customProperty("subsetStringBckp")
    layer.removeCustomProperty("subsetStringBckp")
    layer.setSubsetString(filter_str)
          
class edit_layer:
    """
        @info: contruction for use edit layer in implemention: 
            with edit_layer(layer):
                Do something with layer
    """
    def __init__(self,layer):
        self.layer=layer
    def __enter__(self):
        start_edit_layer(self.layer)
    def __exit__(self, type, value, traceback):
        stop_edit_layer(self.layer)

        

def load_styles_from_dir(layer,styles_dir,switchActiveStyle=True):
    editLayerStyles=layer.styleManager()
    currentStyleName=editLayerStyles.currentStyle()
    if os.path.exists(styles_dir):
        for user_style_file in os.listdir(styles_dir):
            if user_style_file.endswith(".qml"):
                user_style_file=to_unicode(user_style_file, codding=sys.getfilesystemencoding() )
                QgsMessageLog.logMessage(u"Loading style:{}".format(os.path.join(styles_dir,user_style_file)), tag="QgisPDS")
                user_style=user_style_file.replace(".qml","").replace(".default","")
                if ".default." in user_style_file:
                    currentStyleName= user_style
                editLayerStyles.addStyle( user_style, editLayerStyles.style(editLayerStyles.styles()[0]) )
                editLayerStyles.setCurrentStyle(user_style)
                layer.loadNamedStyle(os.path.join(styles_dir,user_style_file))
                
        if not switchActiveStyle:
            editLayerStyles.setCurrentStyle(currentStyleName)    
    else:
        QgsMessageLog.logMessage(u"Warning. Default user styles not loaded. Can't open style directory:{}".format(styles_dir), tag="QgisPDS")
    return currentStyleName    

def load_style( layer,style_path,name=None ,rereadOnExist=False ,activeStyleName=None):
    if os.path.exists(style_path):    
        editLayerStyles=layer.styleManager()
        if rereadOnExist or name not in editLayerStyles.styles():
            QgsMessageLog.logMessage(u"Loading style:{}".format(style_path), tag="QgisPDS")
            if name is not None:
                editLayerStyles.addStyle( name, editLayerStyles.style(editLayerStyles.styles()[0]) ) 
                editLayerStyles.setCurrentStyle(name)
            layer.loadNamedStyle(style_path)        
        else:
            if name is not None:
                editLayerStyles.setCurrentStyle(name)
        if activeStyleName is not None:
            editLayerStyles.setCurrentStyle(activeStyleName)
    else:
        QgsMessageLog.logMessage(u"Warning. Default style not loaded. Can't open style :{}".format(style_path), tag="QgisPDS")    

    

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
        layerName = layerName + u'  ' + time.strftime('%d-%m-%Y %H:%M:%S', time.localtime())
    return layerName

def makeShpFileName(scheme='', layerName='', makeUniq = True, ext=".shp"):
    ln = layerName.replace('/', '-').replace('\\', '-')[:MAX_FILE_NAME_SIZE-22-len(ext)]
    if makeUniq:
        layerFile = u'/{0}_{1}_{2}{ext}'.format(scheme, ln, time.strftime('%d_%m_%Y_%H_%M_%S', time.localtime()),ext=ext)
    else:
        layerFile = u'/{0}_{1}{ext}'.format(scheme, ln ,ext=ext)

    (prjPath, prjExt) = os.path.splitext(QgsProject.instance().fileName())
    if not os.path.exists(prjPath):
        os.mkdir(prjPath)

    return prjPath + layerFile

def memoryToShp(layer, scheme, layerName):
    settings = QSettings()
    systemEncoding = settings.value('/UI/encoding', 'System')

    ln = layerName.replace('/', '-').replace('\\', '-')[:MAX_FILE_NAME_SIZE-26]
    layerFile = u'/{0}_{1}_{2}.shp'.format(scheme, ln, time.strftime('%d_%m_%Y_%H_%M_%S', time.localtime()))

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

def plugin_path():
    return os.path.dirname(os.path.abspath(__file__))                
    

def createProjectString(args):
    projectName = args['project']
    options = json.loads(args['options'])
    host = options['host']
    sid = options['sid']

    return u'{0}/{1}/{2}'.format(host, sid, projectName)