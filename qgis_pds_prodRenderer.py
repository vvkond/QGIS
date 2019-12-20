# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QgisPDS
                                 A QGIS plugin
 PDS link
                              -------------------
        begin                : 2016-11-05
        git sha              : $Format:%H$
        copyright            : (C) 2016 by SoyuzGeoService
        email                :
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis import utils
from bblInit import *
import random
import os,sys
import xml.etree.cElementTree as ET
import ast
import re
from datetime import datetime
import traceback
import inspect
import json

IS_DEBUG=False

try:
    from PyQt4.QtCore import QString
except ImportError:
    # we are using Python3 so QString is not defined
    QString = type("")
#===============================================================================
# CONSTANTS
#===============================================================================
P_LEADER_LINE_WIDTH='leaderLineWidth'        # width value of leader line
P_LEADER_LINE_COLOR='leaderLineColor'        # color name for leader line. use QColor(name)
P_LEADER_LINE_FIELD_TXT='leaderLineFieldTxt' # current layer field for calculate LL length
P_TXT_FONT_NAME='txtFontName'                # Name of font for prodution text. For example "Perpetua titling MT"
P_SHOW_LINEOUTS='showLineouts'               # is show leader line on symbol
P_SHOW_LABELS='showLabels'                   # is show production labels on symbol
P_SHOW_DIAGRAMMS='show_Diagramms'            # is show bubbles on symbol
P_LABELS_SIZE='labelSize'                    # size for production labels
P_DIAGRAMMS_CONFIGS_STR='diagrammStr'        # diagram config string values
P_LABELS_TEMPLATE_STR='templateStr'          # template for production labeling

DEFAULT_CFG={}  # default config values for QgsMarkerSymbolLayerV2
DEFAULT_CFG[P_LEADER_LINE_WIDTH]=0.2
DEFAULT_CFG[P_LEADER_LINE_COLOR]=Qt.black
DEFAULT_CFG[P_LEADER_LINE_FIELD_TXT]=u'well_id'
DEFAULT_CFG[P_TXT_FONT_NAME]=None
DEFAULT_CFG[P_SHOW_LINEOUTS]=True
DEFAULT_CFG[P_SHOW_LABELS]=True
DEFAULT_CFG[P_SHOW_DIAGRAMMS]=True
DEFAULT_CFG[P_LABELS_SIZE]=7.0
DEFAULT_CFG[P_DIAGRAMMS_CONFIGS_STR]=u''
DEFAULT_CFG[P_LABELS_TEMPLATE_STR]=u''


#===============================================================================
# GUI WIDGET CONFIGURATION
#===============================================================================
def on_colorWChanged(obj, cfg_name, color):
    '''
        @info: function on color widget change
        @param obj: object of QgsSymbolLayerV2Widget with renderlayer parametr (object QgsMarkerSymbolLayerV2)
        @param cfg_name: name of config value. @see: DEFAULT_CFG
    '''
    obj.renderlayer.cfg[cfg_name]=color.name()
    QgsMessageLog.logMessage(u"self.renderlayer.{}".format(cfg_name), 'BabbleSymbolLayer')
    obj.emit(SIGNAL("changed()"))   
    pass
def on_valChanged(obj, cfg_name, v):
    '''
        @info: function on direct value change. where result=value
        @param obj: object of QgsSymbolLayerV2Widget with renderlayer parametr (object QgsMarkerSymbolLayerV2)
        @param cfg_name: name of config value. @see: DEFAULT_CFG
    '''
    
    obj.renderlayer.cfg[cfg_name]=v
    QgsMessageLog.logMessage(u"self.renderlayer.{}".format(cfg_name), 'BabbleSymbolLayer')
    obj.emit(SIGNAL("changed()"))   
    pass

CONFIG_WIDGET_INFO = namedtuple('CONFIG_WIDGET_INFO',
                                 [
                                    'group_name'            # name of tools group
                                  , 'name'                  # display name. Just translated string
                                  , 'widget'                # store created widget. Default None, for replace with created widget use: w=w._replace(widget = w.widget_creator(self)) 
                                  , 'widget_creator'        # function for create widget. Best variant declaration: lambda obj:WidgetCreator(). Where obj- object of QgsSymbolLayerV2Widget with obj.layer-map layer
                                  , 'signal_func_connector' # func,used to connect widget signal to action,defined in 'signal_func' . Example use:  w.signal_func_connector( w.widget ,lambda v ,obj=self ,f=w.signal_func : f(obj,v) )
                                  , 'signal_func'           # func, that must be executed on widget signal. If define many input argument, then when connect using 'signal_func_connector', we must set all arguments!!!!
                                  , 'val_setter'            # func, for set widget value. Input arg current 'widget'
                                  ]
                                 )

CFG_TOOLBOOX={} # store widget configures for display in GUI config window 
CFG_TOOLBOOX[P_LEADER_LINE_COLOR]=      CONFIG_WIDGET_INFO(   group_name=          'Leader line'
                                                              ,name=               'Leader line color'        
                                                              ,widget=             None  
                                                              ,widget_creator=     lambda obj:QgsColorButtonV2()                                                  
                                                              ,signal_func_connector= lambda widget,f: widget.colorChanged.connect(f)
                                                              ,signal_func=        lambda obj,clr:on_colorWChanged(obj,P_LEADER_LINE_COLOR,clr)
                                                              ,val_setter=         lambda widget,v:widget.setColor(QColor(v)) 
                                                              )#colorChanged (const QColor &color)
CFG_TOOLBOOX[P_LEADER_LINE_FIELD_TXT]=CONFIG_WIDGET_INFO(     group_name=          'Leader line'
                                                              ,name=               'Leader line length field' 
                                                              ,widget=             None
                                                              ,widget_creator=     lambda obj:map(lambda widget:[widget,widget.setLayer(obj.layer)],[QgsFieldComboBox()])[0][0]  
                                                              ,signal_func_connector=  lambda widget,f: widget.fieldChanged.connect(f)
                                                              ,signal_func=        lambda obj,v:on_valChanged(obj,P_LEADER_LINE_FIELD_TXT,v) 
                                                              ,val_setter=         lambda widget,v:widget.setField(v)
                                                              )#fieldChanged (const QString &fieldName)
CFG_TOOLBOOX[P_LEADER_LINE_WIDTH]=  CONFIG_WIDGET_INFO(       group_name=          'Leader line' 
                                                              ,name=               'Leader line width'        
                                                              ,widget=             None
                                                              ,widget_creator=     lambda obj:map( lambda widget:[widget,widget.setSingleStep(0.05)],[QDoubleSpinBox()])[0][0]                                                      
                                                              ,signal_func_connector=   lambda widget,f: widget.valueChanged.connect(f)
                                                              ,signal_func=        lambda obj,v:on_valChanged(obj,P_LEADER_LINE_WIDTH,v)  
                                                              ,val_setter=         lambda widget,v:widget.setValue(v)
                                                              )#valueChanged(double d)


#===============================================================================
# DiagrammSlice
#===============================================================================
class DiagrammSlice(MyStruct):
    backColor = QColor(Qt.red)
    lineColor = QColor(Qt.black)
    fieldName = ''
    percent = 0.0

#===============================================================================
# DiagrammDesc
#===============================================================================
class DiagrammDesc:
    def __init__(self, diagrammSize, slices,realSize=None):
        self.mDiagrammSize = diagrammSize
        self.mRealSize = realSize
        self.mSlices = slices

    def __repr__(self):
        return repr((self.mRealSize, self.mDiagrammSize, self.mSlices))
    def __str__(self):
        return self.__repr__()


#===============================================================================
# float_t
#===============================================================================
def float_t(val,on_error=0.0):
    if (type(val) is QPyNullVariant and val.isNull()) or val is None:   #PyQt4.QtCore.QPyNullVariant:
        val=0.0
    try:
        return float(val)
    except Exception as e:
        QgsMessageLog.logMessage("incorrect val for float:", 'BubbleSymbolLayer')
        try:
            QgsMessageLog.logMessage("\t{}={}\n{}".format(type(val),val,str(e)), 'BubbleSymbolLayer')
        except:pass
        return on_error
        #raise Exception("incorrect val for float {}={}\n{}".format(type(val),val,str(e)))


#===============================================================================
# BubbleSymbolLayer
#===============================================================================
class BubbleSymbolLayer(QgsMarkerSymbolLayerV2):

    LAYERTYPE="BubbleDiagramm"
    DIAGRAMM_FIELDS = 'DIAGRAMM_FIELDS'
    LABEL_OFFSETX = 'labloffx'
    LABEL_OFFSETY = 'labloffy'
    BUBBLE_SIZE = 'bubblesize'
    DIAGRAMM_LABELS = 'bbllabels'
    #===========================================================================
    # 
    #===========================================================================
    def load_old_structure_config(self,props):
        self.cfg[P_SHOW_LINEOUTS]  = props[QString("showLineouts")]  == "True" if QString("showLineouts")  in props else True
        self.cfg[P_SHOW_LABELS]    = props[QString("showLabels")]    == "True" if QString("showLabels")    in props else True
        self.cfg[P_SHOW_DIAGRAMMS] = props[QString("showDiagramms")] == "True" if QString("showDiagramms") in props else True
        self.cfg[P_LABELS_SIZE]    = float(props[QString("labelSize")]) if QString("labelSize")   in props else 7.0
        self.cfg[P_DIAGRAMMS_CONFIGS_STR]= props[QString("diagrammStr")]      if QString("diagrammStr") in props else u'';
        self.cfg[P_LABELS_TEMPLATE_STR]= props[QString("templateStr")]      if QString("templateStr") in props else u'';
        
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, props):
        '''
            @info: use props for get variables
        '''

        ts=datetime.now()
        QgsMarkerSymbolLayerV2.__init__(self)
        self.radius = 4.0
        self.color = QColor(255,0,0)

        # self.labelDataSums = None
        '''
            GENERATE CONFIG DICT WITH DEFAULT VALUES
        '''
        self.cfg=DEFAULT_CFG.copy() #dict of config parametrs. Use only JSON-serialized types
        try:
            self.load_old_structure_config(props) # @TODO: REMOVE IT AFTER ALL CLIENTS UPDATED !!!!
            self.cfg.update( json.loads(props.get("cfg","{}")) )
            # self.labelDataSums = props[QString("labelDataSums")] if QString("labelDataSums") in props else None;
        except Exception as e:
            QgsMessageLog.logMessage('SET PROPERTY ERROR: ' +  traceback.format_exc(), 'BubbleSymbolLayer')
        '''
            Set property from feature values
        '''
        self.setDataDefinedProperty(BubbleSymbolLayer.DIAGRAMM_FIELDS, QgsDataDefined(OLD_NEW_FIELDNAMES[1])            )
        self.setDataDefinedProperty(BubbleSymbolLayer.LABEL_OFFSETX,   QgsDataDefined(BubbleSymbolLayer.LABEL_OFFSETX)  )
        self.setDataDefinedProperty(BubbleSymbolLayer.LABEL_OFFSETY,   QgsDataDefined(BubbleSymbolLayer.LABEL_OFFSETY)  )
        self.setDataDefinedProperty(BubbleSymbolLayer.BUBBLE_SIZE,     QgsDataDefined(BubbleSymbolLayer.BUBBLE_SIZE)    )
        self.setDataDefinedProperty(BubbleSymbolLayer.DIAGRAMM_LABELS, QgsDataDefined(BubbleSymbolLayer.DIAGRAMM_LABELS))
        if self.cfg[P_LABELS_TEMPLATE_STR]:
            self.setDataDefinedProperty('DDF_Days', QgsDataDefined('days'))
        # if self.labelDataSums:
        #     self.setDataDefinedProperty('labelDataSums', QgsDataDefined(self.labelDataSums))
        self.diagrammProps = None
        # self.labelsProps = None

        idx = 1
        try:
            if len(self.cfg[P_DIAGRAMMS_CONFIGS_STR]) > 1:
                self.diagrammProps = ast.literal_eval(self.cfg[P_DIAGRAMMS_CONFIGS_STR])
                for d in self.diagrammProps:
                    slices = d['slices']
                    if slices:
                        for slice in slices:
                            expName = str(idx) + '_expression'
                            exp = slice['expression']
                            slice['expName'] = expName
                            self.setDataDefinedProperty(expName, QgsDataDefined(exp))
                            if not self.hasDataDefinedProperty(expName):
                                self.setDataDefinedProperty(expName, QgsDataDefined('"{0}" + 0.0'.format(exp)))
                            idx = idx+1
                    if 'labels' in d:
                        labels = d['labels']
                        if labels:
                            for label in labels:
                                expName = label['expName']
                                exp = label['expression']
                                self.setDataDefinedProperty(expName, QgsDataDefined(exp))
                                if not self.hasDataDefinedProperty(expName):
                                    self.setDataDefinedProperty(expName, QgsDataDefined('"{0}" + 0.0'.format(exp)))
                                    
        except Exception as e:
            QgsMessageLog.logMessage('Evaluate diagram props: ' + str(e), 'BubbleSymbolLayer')
        IS_DEBUG and QgsMessageLog.logMessage('BubbleSymbolLayer rendered init in : {}'.format(str(datetime.now()-ts)), 'BubbleSymbolLayer')

        # try:
        #     if len(self.labelsStr) > 1:
        #         self.labelsProps = ast.literal_eval(self.labelsStr)
        #         for label in self.labelsProps:
        #             expName = str(idx) + '_labexpression'
        #             exp = label['expression']
        #             label['expName'] = expName
        #             self.setDataDefinedProperty(expName, QgsDataDefined('"{0}" + 0.0'.format(exp)))
        #             idx = idx+1
        # except Exception as e:
        #     QgsMessageLog.logMessage('Evaluate label props: ' + str(e), 'BubbleSymbolLayer')

        self.mXIndex = -1
        self.mYIndex = -1
        self.mDiagrammIndex = -1

        self.fields = None
        self.renderContext=None #current render context

    #===========================================================================
    # layerType
    #===========================================================================
    def layerType(self):
        return BubbleSymbolLayer.LAYERTYPE

    #===========================================================================
    # properties
    #===========================================================================
    def properties(self):
        '''
            @info: in this block must be defined all properties, passed from Widget to Renderer.
                    It used to clone renderer(multiprocess draw) or copy styles xml . So all values must be str
        '''
        props = {
                 "cfg"           :  json.dumps(self.cfg)
                 }
                # "labelDataSums": str(self.labelDataSums)}

        return props

    #===============================================================================
    # 
    #===============================================================================
    def resetVariables(self):
        self._zoomLvl=None
        self._labelFontSize=None
        return True
    #===========================================================================
    # stopRender
    #===========================================================================
    def stopRender(self, context):
        IS_DEBUG and QgsMessageLog.logMessage('stopRender:', 'BubbleSymbolLayer')
        self.resetVariables()
        pass

    #===========================================================================
    # drawPreview
    #===========================================================================
    def drawPreview(self, painter, point, size):
        rect = QRectF(point, size)

        if self.cfg[P_SHOW_DIAGRAMMS]:
            painter.setPen(Qt.black)
            painter.setBrush(QBrush(Qt.red))
            painter.drawPie(rect, 90 * 16, 180 * 16)
            painter.setBrush(QBrush(Qt.blue))
            painter.drawPie(rect, 270 * 16, 90 * 16)
            painter.setBrush(QBrush(Qt.green))
            painter.drawPie(rect, 360 * 16, 90 * 16)

        pt1 = QPointF(rect.center())
        pt2 = QPointF(pt1)
        pt3 = QPointF(rect.right(), pt1.y())

        if self.cfg[P_SHOW_LINEOUTS]:
            pen = QPen(Qt.black)
            pen.setWidth(1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            
            pt3 = QPointF(rect.topRight())
            pt2 = QPointF((pt1.x()+pt3.x())/2, (pt1.y()+pt3.y())/2)
            pt3.setY(pt2.y())
            painter.drawLine(pt1, pt2)
            painter.drawLine(pt2, pt3)
            
            font = QFont("arial")
            font.setPointSizeF(qAbs(rect.top()-pt2.y()))
            painter.setFont(font)
            painter.drawText(pt2, u"1P")

    #===========================================================================
    # addLabels
    #===========================================================================
    def addLabels(self, context, labelsProps):
        templateStr = u''
        if not labelsProps:
            return templateStr

        sum = 0.0
        for label in labelsProps:
            expName = label['expName']
            val = None
            if self.hasDataDefinedProperty(expName):
                (val, ok) = self.evaluateDataDefinedProperty(expName, context, 0.0)
                if type(val) is float:
                    sum = sum + float(val)

        for label in labelsProps:
            expName = label['expName']
            valStr = ''

            if self.hasDataDefinedProperty(expName):
                (val, ok) = self.evaluateDataDefinedProperty(expName, context, 0.0)
                if val is None or val == NULL:
                    break
                colorStr = label['color']
                showZero = label['showZero']
                isNewLine = label['isNewLine']

                if type(val) is float:
                    formatString = "{:." + str(label['decimals']) + "f}"
                    if val != 0.0 or showZero:
                        if label['percent'] and sum != 0.0:
                            valStr = formatString.format(100.0 * float(val)/sum) + '%'
                        else:
                            valStr = formatString.format(float(val))
                else:
                    valStr = str(val)
            else:
                QgsMessageLog.logMessage('No DDF label ' + expName, 'BubbleSymbolLayer')

            if len(valStr):
                if isNewLine:
                    templateStr += '<div><span><font color="{0}">{1}</font></span></div>'.format(colorStr, valStr)
                else:
                    templateStr += '<span><font color="{0}">{1}</font></span>'.format(colorStr, valStr)

        templateStr = re.sub('^[\,\:\;\.\-/\\_ ]+|[\,\:\;\.\-/\\_ ]+$', '', templateStr)
        return templateStr

    #===========================================================================
    # compileLabels
    #===========================================================================
    def compileLabels(self, templateStr, sum, d, feature):
        IS_DEBUG and QgsMessageLog.logMessage('compileLabels:', 'BubbleSymbolLayer') #DEBUG
        showZero = False
        decimals = d['decimals']
        formatString = "{:."+str(decimals)+"f}"

        days = feature["days"]
        if days:
            days = 1.0 / days

        slices = d['slices']
        multiplier = d['multiplier']
        dailyProduction = d['dailyProduction']
        for slice in slices:
            attr = slice['expression']
            colorStr = slice['labelColor']
            inPercent = slice['inPercent']
            strVal = '0'
            val = 0.0
            percentStr = ''
            if attr in templateStr:
                val = feature[attr]
                if val is not None and val != NULL:
                    if not inPercent:
                        val *= multiplier
                else:
                    val = 0
                if inPercent and sum != 0:
                    val = val / sum * 100
                    percentStr = '%'
                elif dailyProduction and days:
                    val *= days
                IS_DEBUG and QgsMessageLog.logMessage('slice val={} :{}'.format(str(val),str(type(val))), 'BubbleSymbolLayer') #DEBUG
                strVal = formatString.format(val) + percentStr
            code = '"{0}"'.format(attr)
            if float(formatString.format(val)) != float(0) or showZero:
                templateStr = templateStr.replace(code, '<span><font color="{0}">{1}</font></span>'.format(colorStr,
                                                                                                           strVal))
            else:
                templateStr = templateStr.replace(code, '')

        templateStr = re.sub('^[\,\:\;\.\-/\\_ ]+|[\,\:\;\.\-/\\_ ]+$', '', templateStr)
        return templateStr

    #===========================================================================
    # toPainterUnits
    #===========================================================================
    def toPainterUnits(self,val,outputUnit=QgsSymbolV2.MM):
        return QgsSymbolLayerV2Utils.convertToPainterUnits( self.renderContext, val , outputUnit )
    #===============================================================================
    # 
    #===============================================================================
    @property
    def labelFontSize(self):
        '''
            @info: calculate label size for current Zoom and dpi. use default DPI=96
        '''
        if not getattr(self, '_labelFontSize',None):
            pd=self.renderContext.painter().device()
            
            IS_DEBUG and QgsMessageLog.logMessage('pd.logicalDpiX():{}'.format(str(pd.logicalDpiX())), 'BubbleSymbolLayer') #DEBUG
            IS_DEBUG and QgsMessageLog.logMessage('pd.logicalDpiY():{}'.format(str(pd.logicalDpiY())), 'BubbleSymbolLayer') #DEBUG
            IS_DEBUG and QgsMessageLog.logMessage('pd.physicalDpiX():{}'.format(str(pd.physicalDpiX())), 'BubbleSymbolLayer') #DEBUG
            IS_DEBUG and QgsMessageLog.logMessage('pd.physicalDpiY():{}'.format(str(pd.physicalDpiY())), 'BubbleSymbolLayer') #DEBUG
            
            #self._labelFontSize=self.toPainterUnits(self.cfg[P_LABELS_SIZE])*96/pd.logicalDpiX() 
            self._labelFontSize=self.cfg[P_LABELS_SIZE]*96.0/pd.logicalDpiX()*self.zoomLvl #96-default windows dpi. With Qt 5 it must be easy...
             
        return self._labelFontSize
    #===========================================================================
    # 
    #===========================================================================
    @property    
    def zoomLvl(self):
        '''
            @info: get zoom level value 
        '''
        if not getattr(self,'_zoomLvl',None):
            self._zoomLvl=self.renderContext.scaleFactor()/3.77952755906
        return self._zoomLvl
    
    #===========================================================================
    # renderPoint
    #===========================================================================
    def renderPoint(self, point, context):
        feature = context.feature()
        p = context.renderContext().painter()
#         canvas=utils.iface.mapCanvas()
#         QgsMessageLog.logMessage('\n{}'.format(str(canvas.scale())), 'BubbleSymbolLayer') #DEBUG
#         QgsMessageLog.logMessage('{}'.format(str(canvas.mapUnitsPerPixel())), 'BubbleSymbolLayer') #DEBUG
#         dpi=utils.iface.mainWindow().physicalDpiX()
#         QgsMessageLog.logMessage('{}'.format(str(dpi)), 'BubbleSymbolLayer') #DEBUG
#         
#         scale=canvas.scale()
#         zoomlevel=scale/1000.0*0.264583333603/canvas.mapUnitsPerPixel()
#         QgsMessageLog.logMessage('{}'.format(str(zoomlevel)), 'BubbleSymbolLayer') #DEBUG
        IS_DEBUG and QgsMessageLog.logMessage('renderPoint:{}'.format(str(point)), 'BubbleSymbolLayer') #DEBUG
        IS_DEBUG and QgsMessageLog.logMessage('\nself.ctx.scaleFactor():{}'.format(str(self.renderContext.scaleFactor())), 'BubbleSymbolLayer') #DEBUG
        IS_DEBUG and QgsMessageLog.logMessage('self.ctx.rendererScale():{}'.format(str(self.renderContext.rendererScale())), 'BubbleSymbolLayer') #DEBUG

        #QgsMessageLog.logMessage('self.ctx.mapToPixel().showParameters():{}'.format(str(self.renderContext.mapToPixel().showParameters())), 'BubbleSymbolLayer') #DEBUG
        
        
        if not feature: 
            '''
            If item not feature, then draw preview (symbol in legend or in style dock)
            '''
            labelSize = self.toPainterUnits(self.size()) 
            self.drawPreview(p, QPointF(point.x() - labelSize / 2, point.y() - labelSize / 2), QSizeF(labelSize, labelSize))
            return

        attrs = feature.attributes()
        
        IS_DEBUG and QgsMessageLog.logMessage('line_width:{}->{}'.format(str(self.cfg[P_LEADER_LINE_WIDTH]) ,str(self.toPainterUnits(self.cfg[P_LEADER_LINE_WIDTH]) )), 'BubbleSymbolLayer') #DEBUG
        
        labelTemplate = ''
        diagramms = []

        try:
            if self.diagrammProps > 0:
                '''
                 Get feature diagram size. New variant: from layer properties 
                '''
                size = float_t(feature.attribute(BubbleSymbolLayer.BUBBLE_SIZE))
                diagrammSize = self.toPainterUnits(size)

                templateStr = self.cfg[P_LABELS_TEMPLATE_STR]
                IS_DEBUG and QgsMessageLog.logMessage('#'*30, 'BubbleSymbolLayer') #DEBUG
                for d in self.diagrammProps:
                    IS_DEBUG and QgsMessageLog.logMessage('*'*10, 'BubbleSymbolLayer') #DEBUG
                    slices = d['slices']
                    scaleType = int(d['scaleType'])
                    scaleMaxRadius = float_t(d['scaleMaxRadius'])
                    scaleMinRadius = float_t(d['scaleMinRadius'])
                    scale = float_t(d['scale'])
                    fixedSize = float_t(d['fixedSize'])
                    if slices and scale != 0.0:
                        koef = (scaleMaxRadius - scaleMinRadius) / scale
                        sum = 0.0
                        newSlices = []
                        for slice in slices:
                            expName = slice['expName']
                            if self.hasDataDefinedProperty(expName):
                                (val, ok) = self.evaluateDataDefinedProperty(expName, context, 0.0 )
                                if val != NULL:
                                    IS_DEBUG and QgsMessageLog.logMessage('val={},koef={},scale={} '.format(val, koef, scale), 'BubbleSymbolLayer') #DEBUG                                   
                                    sum = sum + val
                                    bc = QgsSymbolLayerV2Utils.decodeColor(slice['backColor'])
                                    lc = QgsSymbolLayerV2Utils.decodeColor(slice['lineColor'])
                                    newSlice = DiagrammSlice(backColor=bc, lineColor=lc, percent=val)
                                    newSlices.append(newSlice)
                            else:
                                QgsMessageLog.logMessage('No DDF ' + expName, 'BubbleSymbolLayer')

                        if sum != 0.0:
                            ds = 0.0
                            if scaleType == 0:
                                ds = fixedSize
                            else:
                                ds = scaleMinRadius + sum * koef
                                IS_DEBUG and QgsMessageLog.logMessage('ds={} '.format(ds), 'BubbleSymbolLayer') #DEBUG
                                if ds > scaleMaxRadius:
                                    ds = scaleMaxRadius
                                elif ds < scaleMinRadius:
                                    ds = scaleMinRadius
                            for slice in newSlices:
                                slice.percent = slice.percent / sum

                            ds = self.toPainterUnits( ds)
                            IS_DEBUG and QgsMessageLog.logMessage('ds={} '.format(ds), 'BubbleSymbolLayer') #DEBUG
                            diagramm = DiagrammDesc(ds, newSlices, sum * koef )
                            diagramms.append(diagramm)

                    if 'labels' in d:
                        labels = d['labels']
                        IS_DEBUG and QgsMessageLog.logMessage('labels: {}'.format(labels), 'BubbleSymbolLayer') #DEBUG
                        labelTemplate = labelTemplate + self.addLabels(context, labels)
                        templateStr = None
                    elif templateStr:
                        templateStr = self.compileLabels(templateStr, sum, d, feature)

                # QgsMessageLog.logMessage(templateStr, 'BubbleSymbolLayer')
                #
                # labelTemplate = feature.attribute(BubbleSymbolLayer.DIAGRAMM_LABELS)
                # if labelTemplate == NULL:
                #     labelTemplate = ''
                # labelTemplate = self.addLabels(context)
                if templateStr:
                    labelTemplate = templateStr


            elif self.mDiagrammIndex >= 0:
                '''
                 Get feature diagram size. Old variant: from Field with XML
                '''

                xmlString = attrs[self.mDiagrammIndex]
                if not xmlString:
                    QgsMessageLog.logMessage('No diagramm ' + ','.join([str(attr) for attr in attrs]),
                                             'BubbleSymbolLayer')
                    return

                root = ET.fromstring(xmlString)

                for diag in root.findall('diagramm'):
                    size = str(diag.attrib['size'])
                    diagrammSize = self.toPainterUnits(float_t(size))

                    if diagrammSize > 0:
                        slices = []
                        for values in diag.findall('value'):
                            bc = QgsSymbolLayerV2Utils.decodeColor(values.attrib['backColor'])
                            lc = QgsSymbolLayerV2Utils.decodeColor(values.attrib["lineColor"])
                            prnc = float_t(values.text)
                            # fn = values.attrib["fieldName"]
                            # slice = DiagrammSlice(backColor=bc, lineColor=lc, percent=prnc, fieldName=fn)
                     
                            slice = DiagrammSlice(backColor=bc, lineColor=lc, percent=prnc)
                            slices.append(slice)

                        diagramm = DiagrammDesc(diagrammSize, slices)
                        diagramms.append(diagramm)

                for label in root.findall('label'):
                    labelTemplate = label.attrib['labelText']
            '''
            Draw diagram for current feature
            '''
            diagramms = sorted(diagramms, key=lambda diagramm: [diagramm.mDiagrammSize,diagramm.mRealSize], reverse=True)
            IS_DEBUG and QgsMessageLog.logMessage("\n".join(map(str,diagramms)), 'BubbleSymbolLayer') #DEBUG
            if self.cfg[P_SHOW_DIAGRAMMS]:
                for idx,desc in enumerate(diagramms):
                    #--- Fix for diagramms with identicaly size
                    if diagramms[idx-1].mDiagrammSize==desc.mDiagrammSize or (idx>0 and diagramms[idx-1].mDiagrammSize<desc.mDiagrammSize):
                        desc.mDiagrammSize=desc.mDiagrammSize*0.8
                        if desc.mDiagrammSize<=0:desc.mDiagrammSize=1
                    IS_DEBUG and QgsMessageLog.logMessage("diagram {} size:{}".format(str(idx),str(desc.mDiagrammSize)), 'BubbleSymbolLayer') #DEBUG
                    rect = QRectF(point, QSizeF(desc.mDiagrammSize , desc.mDiagrammSize ))
                    rect.translate(-desc.mDiagrammSize / 2, -desc.mDiagrammSize / 2)
                    startAngle = 90.0
                    count = len(desc.mSlices)
                    for slice in desc.mSlices:
                        color = QColor(slice.backColor)
                        p.setBrush(QBrush(color))

                        color = QColor(slice.lineColor)
                        p.setPen(color)

                        spanAngle = 360 * slice.percent
                        if count > 1:
                            p.drawPie(rect, startAngle * 16, spanAngle * 16)
                        else:
                            p.drawEllipse(rect)

                        startAngle = startAngle + spanAngle

            '''
            Draw diagram label for current feature
            '''
            font = QFont(self.cfg[P_TXT_FONT_NAME])  
            font.setPointSizeF( self.labelFontSize )
            p.setFont(font)

            if self.mXIndex >= 0 and self.mYIndex >= 0:
                xVal = 0.0
                yVal = 0.0
                if attrs[self.mXIndex]:
                    xVal = self.toPainterUnits(float_t(attrs[self.mXIndex]))
                if attrs[self.mYIndex]:
                    yVal = self.toPainterUnits(float_t(attrs[self.mYIndex]))

                #if xVal != 0 or yVal != 0:
                pt1 = point + QPointF(xVal, yVal)
                
                st = QStaticText(labelTemplate);
                opt = st.textOption()
                opt.setWrapMode(QTextOption.NoWrap)
                st.setTextOption(opt)
                st.prepare(p.transform(), p.font())
                
                IS_DEBUG and QgsMessageLog.logMessage('self.zoomLvl:{}'.format(str(self.zoomLvl) )                             , 'BubbleSymbolLayer') #DEBUG
                IS_DEBUG and QgsMessageLog.logMessage('self.cfg[P_LABELS_SIZE]*self.zoomLvl:{}'.format(str(self.cfg[P_LABELS_SIZE]*self.zoomLvl) ), 'BubbleSymbolLayer') #DEBUG
                IS_DEBUG and QgsMessageLog.logMessage('p.font().pointSizeF()):{}'.format(str(p.font().pointSizeF()) )           , 'BubbleSymbolLayer') #DEBUG
                
                widthVal = st.size().width()
                if widthVal==0 and self.leaderLineField>=0: #set default size for label without production text
                    widthVal=self.toPainterUnits(len(str(attrs[self.leaderLineField])))*2
                
                pt2 = point + QPointF(xVal + widthVal, yVal)

                pen_ll = QPen(QColor(self.cfg[P_LEADER_LINE_COLOR]))
                pen_ll.setWidth(self.toPainterUnits(self.cfg[P_LEADER_LINE_WIDTH]) )
                p.setPen(pen_ll)
                if point.x() < (pt1.x() + pt2.x()) / 2 :
                    if self.cfg[P_SHOW_LINEOUTS]:
                        p.drawLine(point, pt1)
                        p.drawLine(pt1, pt2)
                    if labelTemplate and labelTemplate != NULL and self.cfg[P_SHOW_LABELS]:
                        p.drawStaticText(pt1.x(), pt1.y(), st)
                else:
                    if self.cfg[P_SHOW_LINEOUTS]:
                        p.drawLine(point, pt2)
                        p.drawLine(pt2, pt1)
                    if labelTemplate and labelTemplate != NULL and self.cfg[P_SHOW_LABELS]:
                        p.drawStaticText(pt1.x(), pt1.y(), st)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            #QgsMessageLog.logMessage('renderPoint: ' + str(e), 'BubbleSymbolLayer')
            QgsMessageLog.logMessage('renderPoint: {} {} {} {}'.format(str(e),exc_type, fname, exc_tb.tb_lineno), 'BubbleSymbolLayer')


    #===========================================================================
    # startRender
    #===========================================================================
    def startRender(self, context):
        '''
            @info: Start render group of features
        '''
        IS_DEBUG and QgsMessageLog.logMessage('startRender:', 'BubbleSymbolLayer')

        self.renderContext=context.renderContext()
                
        self.fields = context.fields()
        if self.fields:
            self.mXIndex = self.fields.fieldNameIndex("labloffx")    #LablOffX
            self.mYIndex = self.fields.fieldNameIndex("labloffy")    #LablOffY
            self.leaderLineField = self.fields.fieldNameIndex(self.cfg[P_LEADER_LINE_FIELD_TXT])
            self.leaderLineField=0 if self.leaderLineField <0 else self.leaderLineField
            self.mDiagrammIndex = self.fields.fieldNameIndex(OLD_NEW_FIELDNAMES[0])
            if self.mDiagrammIndex < 0:
                self.mDiagrammIndex = self.fields.fieldNameIndex(OLD_NEW_FIELDNAMES[1])
        else:
            self.mXIndex = -1
            self.mYIndex = -1
            self.mDiagrammIndex= -1

        self.prepareExpressions(context)
        
        QgsMarkerSymbolLayerV2.startRender(self, context)


    #===========================================================================
    # clone
    #===========================================================================
    def clone(self):
        return BubbleSymbolLayer(self.properties())


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_renderer_base.ui'))

#===============================================================================
# BabbleSymbolLayerWidget
#===============================================================================
class BabbleSymbolLayerWidget(QgsSymbolLayerV2Widget, FORM_CLASS):
    
    #===========================================================================
    # makeToolBox
    #===========================================================================
    def makeToolBox(self,vectorLayer):
        self.layer=vectorLayer

        # Add toolbar and items
        layout = QVBoxLayout()
        self.configGrpBox.setLayout(layout)
        tBx = QToolBox()
        layout.addWidget(tBx)
        tBxItems={}        # dict of created toolbox items  
        tBxItemsLayouts={}  # dict of layouts for toolbox items
        self.cfgToolBox=CFG_TOOLBOOX.copy()
        ## create widget toolboxes
        for group_name in list(sorted(set(w.group_name for key,w in self.cfgToolBox.items()))):
            '''
                if toolbox group not present,then create it and layout 
            '''
            tBxItem=QWidget()
            wLayout  =QVBoxLayout()
            tBxItem.setLayout(wLayout)
            tBxItems[group_name]=tBxItem
            tBxItemsLayouts[group_name]=wLayout
            tBx.addItem(tBxItem, group_name)
        # create widgets
        for key,w in self.cfgToolBox.items():
            self.cfgToolBox[key]=w._replace(widget = w.widget_creator(self))
        # connect widgets to form and actions
        for key,w in self.cfgToolBox.items():
            iLayout=QHBoxLayout()
            iLayout.addWidget(QLabel(w.name))
            iLayout.addWidget(w.widget)
            tBxItemsLayouts[w.group_name].addLayout(iLayout)
            w.signal_func_connector( w.widget
                                     ,lambda v ,obj=self ,f=w.signal_func : f(obj,v) 
                                     )
        
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, parent=None, vectorLayer = None):
        try:
            QgsSymbolLayerV2Widget.__init__(self, parent, vectorLayer)
            self.setupUi(self)
            self.makeToolBox(vectorLayer)
    
            self.renderlayer = None #object of QgsMarkerSymbolLayerV2
            self.expressionIndex = 0
        except:
            QgsMessageLog.logMessage(u"{}".format(traceback.format_exc()), tag="BubbleSymbolLayer.error")
    
    #===========================================================================
    # setSymbolLayer
    #===========================================================================
    def setSymbolLayer(self, layer):
        '''
            @info: Set render layer. Read config from render layer
            @param layer: object of QgsMarkerSymbolLayerV2
        '''

        try:
            if layer.layerType() != BubbleSymbolLayer.LAYERTYPE:
                return
    
            self.renderlayer = layer
            self.showLineouts.setChecked(      self.renderlayer.cfg[P_SHOW_LINEOUTS] )
            self.showLabels.setChecked(        self.renderlayer.cfg[P_SHOW_LABELS]   )
            self.showDiagramms.setChecked(     self.renderlayer.cfg[P_SHOW_DIAGRAMMS])
            self.mLabelSizeSpinBox.setValue(   self.renderlayer.cfg[P_LABELS_SIZE])
            self.editTemplateStr.setText(      self.renderlayer.cfg[P_LABELS_TEMPLATE_STR])
            self.editDiagrammStr.setPlainText( self.renderlayer.cfg[P_DIAGRAMMS_CONFIGS_STR])
            for name in [ P_LEADER_LINE_COLOR,P_LEADER_LINE_FIELD_TXT,P_LEADER_LINE_WIDTH ]:
                self.cfgToolBox[name].val_setter(self.cfgToolBox[name].widget,self.renderlayer.cfg[name]) 
        except:
            QgsMessageLog.logMessage(u"{}".format(traceback.format_exc()), tag="BubbleSymbolLayer.error")
        
    #===========================================================================
    # symbolLayer
    #===========================================================================
    def symbolLayer(self):
        return self.renderlayer
    
    #===========================================================================
    # on_editTemplateStr_txt_changed
    #===========================================================================
    def on_editTemplateStr_txt_changed(self,val):
        IS_DEBUG and QgsMessageLog.logMessage('on_editTemplateStr_txt_changed', 'BabbleSymbolLayerWidget')
        self.renderlayer.cfg[P_LABELS_TEMPLATE_STR]=val
        self.emit(SIGNAL("changed()"))
        pass

    #===========================================================================
    # on_editDiagrammStr_txt_changed
    #===========================================================================
    def on_editDiagrammStr_txt_changed(self):
        IS_DEBUG and QgsMessageLog.logMessage('on_editDiagrammStr_txt_changed', 'BabbleSymbolLayerWidget')
        self.renderlayer.cfg[P_DIAGRAMMS_CONFIGS_STR]=self.editDiagrammStr.toPlainText()
        self.emit(SIGNAL("changed()"))
        pass

    #===========================================================================
    # on_showLineouts_toggled
    #===========================================================================
    def on_showLineouts_toggled(self, value):
        IS_DEBUG and QgsMessageLog.logMessage('on_showLineouts_toggled', 'BabbleSymbolLayerWidget')
        self.renderlayer.cfg[P_SHOW_LINEOUTS] = value
        self.emit(SIGNAL("changed()"))

    #===========================================================================
    # on_showLabels_toggled
    #===========================================================================
    def on_showLabels_toggled(self, value):
        IS_DEBUG and QgsMessageLog.logMessage('on_showLabels_toggled', 'BabbleSymbolLayerWidget')
        self.renderlayer.cfg[P_SHOW_LABELS]= value
        self.emit(SIGNAL("changed()"))

    #===========================================================================
    # on_showDiagramms_toggled
    #===========================================================================
    def on_showDiagramms_toggled(self, value):
        IS_DEBUG and QgsMessageLog.logMessage('on_showDiagramms_toggled', 'BabbleSymbolLayerWidget')
        self.renderlayer.cfg[P_SHOW_DIAGRAMMS] = value
        self.emit(SIGNAL("changed()"))

    @pyqtSlot(float)
    def on_mLabelSizeSpinBox_valueChanged(self, value):
        IS_DEBUG and QgsMessageLog.logMessage('on_mLabelSizeSpinBox_valueChanged', 'BabbleSymbolLayerWidget')
        self.renderlayer.cfg[P_LABELS_SIZE] = value
        self.emit(SIGNAL("changed()"))


#===============================================================================
# BabbleSymbolLayerMetadata
#===============================================================================
class BabbleSymbolLayerMetadata(QgsSymbolLayerV2AbstractMetadata):

    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self):
        try:
            QgsSymbolLayerV2AbstractMetadata.__init__(self, BubbleSymbolLayer.LAYERTYPE, u"Круговые диаграммы PDS", QgsSymbolV2.Marker)
        except:
            QgsMessageLog.logMessage(u"{}".format(traceback.format_exc()), tag="BabbleSymbolLayerMetadata.error")
        

    #===========================================================================
    # createSymbolLayer
    #===========================================================================
    def createSymbolLayer(self, props):
        '''
            @info: function for create layer renderer. Can set default values from prop
                    for example:
                        if 'key' in props:props[key]
        '''
        try:
            return BubbleSymbolLayer(props)
        except:
            QgsMessageLog.logMessage(u"{}".format(traceback.format_exc()), tag="BabbleSymbolLayerMetadata.error")
        

    #===========================================================================
    # createSymbolLayerWidget
    #===========================================================================
    def createSymbolLayerWidget(self, vectorLayer):
        try:
            return BabbleSymbolLayerWidget(None, vectorLayer)
        except:
            QgsMessageLog.logMessage(u"{}".format(traceback.format_exc()), tag="BabbleSymbolLayerMetadata.error")




