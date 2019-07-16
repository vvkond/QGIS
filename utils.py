# -*- coding: utf-8 -*-

from qgis.core import *
from qgis.utils import iface
from qgis.PyQt.QtGui  import QProgressBar
from qgis.PyQt.QtCore import *

import numpy
import time
from processing.tools.vector import VectorWriter
import os
import json
import sys


MAX_FILE_NAME_SIZE=224- 24- 50# -24 in some clients can't copy 224 named files


class StrictInit(object):
    def __init__(self, **kw):
        assert not set(kw).difference(dir(self.__class__)), u'{0} does not declare fields {1}'.format(self.__class__, list(set(kw).difference(dir(self.__class__))))
        self.__dict__.update(kw)


class WithSql(object):
    def get_sql(self, value):
        plugin_dir = os.path.dirname(__file__)
        sql_file_path = os.path.join(plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')    

class Args(StrictInit):
    args = None


class Exc(Exception):
    pass

class LayersHider():
    def __init__(self,iface):
        self.iface=iface
        self.viz_layers=[]
    def hide(self):
        self.viz_layers=[]
        for layer in self.iface.legendInterface().layers():
            if self.iface.legendInterface().isLayerVisible(layer):
                self.viz_layers.append(layer)
                self.iface.legendInterface().setLayerVisible(layer, False)
        self.iface.mapCanvas().refresh() #Repaints the canvas map/ Not work.BUG????
        self.refresh_layers()
        # self.iface.mapCanvas().refreshAllLayers() #Reload all layers, clear the cache and refresh the canvas 
    def show(self):
        for layer in self.viz_layers:
            self.iface.legendInterface().setLayerVisible(layer, True)
        self.iface.mapCanvas().refresh()#Repaints the canvas map/ Not work.BUG????
        self.refresh_layers()
    def refresh_layers(self):
        for layer in self.iface.mapCanvas().layers():
            layer.triggerRepaint()
        

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
        

def set_layer_variable(layer,var,val):
    """
        @info: set variable for registered in MapLayerRegistry layer. Variable stored in current layer style!!!!
    """
    QgsExpressionContextUtils.setLayerVariable(layer,var,val)
    pass
def set_layer_property(layer,var,val):
    """
        @info: set property for layer. Layer can be not registered...
    """
    layer.setCustomProperty(var, str(val) )    
    pass
def read_layer_property(layer,var):
    """
        @info: read layer property
    """
    return layer.customProperty(var)    
def read_layer_variable(layer,var):
    """
        @info: read layer variable
    """
    res=QgsExpressionContextUtils.layerScope(layer).variable(var)
    if not res:
        res=read_layer_property(layer, var)
    return res

class WithQtProgressBar():
    """
        @info: in base class must be self.iface
        @example:
                # update progress bar
                self.showProgressBar(msg="Progress bar message", maximum=100.0) 
                # iterate over some elements
                now=time.time()
                for idx,(wl,max_dt) in enumerate(result):
                    # change progress bar value
                    self.progress.setValue(idx)
                    # redraw GUI each 1 second          
                    if time.time()-now>1 :  QCoreApplication.processEvents();time.sleep(0.02);now=time.time() #refresh GUI
                    # run other operations
                    ... 
        
    """
    def showProgressBar(self,msg,maximum):
        self.iface.messageBar().clearWidgets()
        self.progressMessageBar = self.iface.messageBar().createMessage(msg)
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        self.progress.setMaximum(maximum)
        self.progressMessageBar.layout().addWidget(self.progress)
        self.iface.messageBar().pushWidget(self.progressMessageBar, self.iface.messageBar().INFO)
        QCoreApplication.processEvents();time.sleep(0.02)        
        return self.progress
    def __del__(self):
        self.iface.messageBar().clearWidgets()

def to_unicode(s,codding='utf-8'):
    if s is None:
        return None
    elif isinstance(s, unicode):
        return s
    return s.decode(codding)

def start_edit_layer(layer):
    if not layer.isEditable():
        filter_str=layer.subsetString()   
        layer.setCustomProperty("subsetStringBckp", filter_str)
        layer.setSubsetString(None)  #If use it in qtdialog.exec_() block on QGIS 2.18 can't add new feature to layer. Only if remove layer.subsetString() before qtdialog.exec_()
        #layer.reload()
        #layer.endEditCommand()
        #layer.commitChanges()
        layer.startEditing()

def stop_edit_layer(layer):
    layer.commitChanges()  
    filter_str=layer.customProperty("subsetStringBckp")
    #layer.removeCustomProperty("subsetStringBckp")
    layer.setSubsetString(filter_str)
    
class edit_layer:
    """
        @info: contruction for use edit layer in implemention: 
            with edit_layer(layer):
                Do something with layer
        @warning: If use it in qtdialog.exec_() block on QGIS 2.18 can't add new feature to exist layer. Only if remove layer.subsetString() before qtdialog.exec_() 
    """
    def __init__(self,layer):
        self.layer=layer
        self.isVisible=False
    def __enter__(self):
        self.isVisible= iface.legendInterface().isLayerVisible(self.layer)
        iface.legendInterface().setLayerVisible(self.layer, False)
        start_edit_layer(self.layer)
    def __exit__(self, type, value, traceback):
        stop_edit_layer(self.layer)
        iface.legendInterface().setLayerVisible(self.layer, self.isVisible)        


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

    
#===============================================================================
# ---not used
#===============================================================================
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

    ln = layerName.replace('/', '-').replace('\\', '-').replace('>', '-').replace('<', '-').replace(' ', '')[:MAX_FILE_NAME_SIZE-26]
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

def qgs_get_all_rules(rule):
    childrenRules=rule.children()
    res=[rule]
    if len(childrenRules)>0:
        for childrenRule in childrenRules:
            res.extend(qgs_get_all_rules(childrenRule))
    else:
        pass
    return res

def qgs_get_last_child_rules(rule):
    childrenRules=rule.children()
    res=[]
    if len(childrenRules)>0:
        for childrenRule in childrenRules:
            res.extend(qgs_get_last_child_rules(childrenRule))
    else:
        res=[rule]
    return res
def qgs_set_symbol_render_level(symbol,level):
    for symbollayer in symbol.symbolLayers():
        symbollayer.setRenderingPass(level)



#===============================================================================
# 
#===============================================================================
import platform   # For getting the operating system name
import subprocess  # For executing a shell command

def ping(host,hidden=True):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Ping command count option as function of OS
    param = '-n' if platform.system()=='Windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]
    
    startupinfo = None
    if hidden:
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW#subprocess.STARTF_USESHOWWINDOW
    #proc = subprocess.Popen(command, startupinfo=startupinfo)    
    return subprocess.call(command, startupinfo=startupinfo) == 0


#===============================================================================
# This function is like the linux which command
#===============================================================================
def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        #for path in os.environ["PATH"].split(os.pathsep):
        for path in getenv_system("PATH").split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None
#===============================================================================
# 
#===============================================================================
def getenv_system(varname, default=''):
    '''
        return system environment variable
    '''
    import os
    import win32api
    import win32con
    import platform   # For getting the operating system name
    
    if platform.system()!='Windows':
        return os.environ(varname)
    else:
        v = default
        try:
            rkey = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment')
            try:
                v = str(win32api.RegQueryValueEx(rkey, varname)[0])
                v = win32api.ExpandEnvironmentStrings(v)
            except:
                pass
        finally:
            win32api.RegCloseKey(rkey)
        return v

