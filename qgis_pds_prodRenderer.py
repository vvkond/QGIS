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
from bblInit import *
import random
import os,sys
import xml.etree.cElementTree as ET
import ast
import re
from datetime import datetime

try:
    from PyQt4.QtCore import QString
except ImportError:
    # we are using Python3 so QString is not defined
    QString = type("")

class DiagrammSlice(MyStruct):
    backColor = QColor(Qt.red)
    lineColor = QColor(Qt.black)
    fieldName = ''
    percent = 0.0

class DiagrammDesc:
    def __init__(self, diagrammSize, slices,realSize=None):
        self.mDiagrammSize = diagrammSize
        self.mRealSize = realSize
        self.mSlices = slices

    def __repr__(self):
        return repr((self.mRealSize, self.mDiagrammSize, self.mSlices))
    def __str__(self):
        return self.__repr__()


def float_t(val):
    if (type(val) is QPyNullVariant and val.isNull()) or val is None:   #PyQt4.QtCore.QPyNullVariant:
        val=0.0
    try:
        return float(val)
    except Exception as e:
        QgsMessageLog.logMessage("incorrect val for float {}={}\n{}".format(type(val),val,str(e)), 'BubbleSymbolLayer')
        #raise Exception("incorrect val for float {}={}\n{}".format(type(val),val,str(e)))

class BubbleSymbolLayer(QgsMarkerSymbolLayerV2):

    LAYERTYPE="BubbleDiagramm"
    DIAGRAMM_FIELDS = 'DIAGRAMM_FIELDS'
    LABEL_OFFSETX = 'labloffx'
    LABEL_OFFSETY = 'labloffy'
    BUBBLE_SIZE = 'bubblesize'
    DIAGRAMM_LABELS = 'bbllabels'
    DEBUG=False

    def __init__(self, props):
        ts=datetime.now()
        QgsMarkerSymbolLayerV2.__init__(self)
        self.radius = 4.0
        self.color = QColor(255,0,0)

        self.showLineouts = True
        self.showLabels = True
        self.showDiagramms = True
        self.labelSize = 7.0
        self.diagrammStr = u''
        self.templateStr = None
        # self.labelDataSums = None

        try:
            self.showLineouts  = props[QString("showLineouts")]  == "True" if QString("showLineouts")  in props else True
            self.showLabels    = props[QString("showLabels")]    == "True" if QString("showLabels")    in props else True
            self.showDiagramms = props[QString("showDiagramms")] == "True" if QString("showDiagramms") in props else True
            self.labelSize     = float(props[QString("labelSize")]) if QString("labelSize")   in props else 7.0
            self.diagrammStr   = props[QString("diagrammStr")]      if QString("diagrammStr") in props else u'';
            self.templateStr   = props[QString("templateStr")]      if QString("templateStr") in props else u'';
            # self.labelDataSums = props[QString("labelDataSums")] if QString("labelDataSums") in props else None;
        except Exception as e:
            QgsMessageLog.logMessage('SET PROPERTY ERROR: ' +  str(e), 'BubbleSymbolLayer')

        self.setDataDefinedProperty(BubbleSymbolLayer.DIAGRAMM_FIELDS, QgsDataDefined(OLD_NEW_FIELDNAMES[1]))
        self.setDataDefinedProperty(BubbleSymbolLayer.LABEL_OFFSETX,   QgsDataDefined(BubbleSymbolLayer.LABEL_OFFSETX))
        self.setDataDefinedProperty(BubbleSymbolLayer.LABEL_OFFSETY,   QgsDataDefined(BubbleSymbolLayer.LABEL_OFFSETY))
        self.setDataDefinedProperty(BubbleSymbolLayer.BUBBLE_SIZE,     QgsDataDefined(BubbleSymbolLayer.BUBBLE_SIZE))
        self.setDataDefinedProperty(BubbleSymbolLayer.DIAGRAMM_LABELS, QgsDataDefined(BubbleSymbolLayer.DIAGRAMM_LABELS))
        if self.templateStr:
            self.setDataDefinedProperty('DDF_Days', QgsDataDefined('days'))
        # if self.labelDataSums:
        #     self.setDataDefinedProperty('labelDataSums', QgsDataDefined(self.labelDataSums))

        self.diagrammProps = None
        # self.labelsProps = None

        idx = 1
        try:
            if len(self.diagrammStr) > 1:
                self.diagrammProps = ast.literal_eval(self.diagrammStr)
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
        self.DEBUG and QgsMessageLog.logMessage('BubbleSymbolLayer rendered init in : {}'.format(str(datetime.now()-ts)), 'BubbleSymbolLayer')

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

    def layerType(self):
        return BubbleSymbolLayer.LAYERTYPE

    def properties(self):
        props = { "showLineouts" : 'True' if self.showLineouts else 'False',
                 "showLabels" : 'True' if self.showLabels else 'False',
                 "showDiagramms" : 'True' if self.showDiagramms else 'False',
                 "labelSize" : str(self.labelSize),
                 "diagrammStr" : str(self.diagrammStr),
                 "templateStr": str(self.templateStr)}
                  # "labelDataSums": str(self.labelDataSums)}

        return props


    def stopRender(self, context):
        pass

    def drawPreview(self, painter, point, size):
        rect = QRectF(point, size)

        if self.showDiagramms:
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

        if self.showLineouts:
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

                # QgsMessageLog.logMessage(str(val), 'BubbleSymbolLayer')

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

    def compileLabels(self, templateStr, sum, d, feature):
        self.DEBUG and QgsMessageLog.logMessage('compileLabels:', 'BubbleSymbolLayer') #DEBUG
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
                self.DEBUG and QgsMessageLog.logMessage('slice val={} :{}'.format(str(val),str(type(val))), 'BubbleSymbolLayer') #DEBUG
                strVal = formatString.format(val) + percentStr
            code = '"{0}"'.format(attr)
            if float(formatString.format(val)) != float(0) or showZero:
                templateStr = templateStr.replace(code, '<span><font color="{0}">{1}</font></span>'.format(colorStr,
                                                                                                           strVal))
            else:
                templateStr = templateStr.replace(code, '')

        templateStr = re.sub('^[\,\:\;\.\-/\\_ ]+|[\,\:\;\.\-/\\_ ]+$', '', templateStr)
        return templateStr
    
    

    def renderPoint(self, point, context):
        feature = context.feature()
        p = context.renderContext().painter()

        if not feature: 
            '''
            If item not feature, then draw preview (symbol in legend or in style dock)
            '''
            labelSize = QgsSymbolLayerV2Utils.convertToPainterUnits(context.renderContext(), self.size(), self.sizeUnit())
            self.drawPreview(p, QPointF(point.x() - labelSize / 2, point.y() - labelSize / 2), QSizeF(labelSize, labelSize))
            return

        attrs = feature.attributes()

        ctx = context.renderContext()

        labelTemplate = ''
        diagramms = []

        try:
            if self.diagrammProps > 0:
                '''
                 Get feature diagram size. New variant: from layer properties 
                '''
                size = float_t(feature.attribute(BubbleSymbolLayer.BUBBLE_SIZE))
                diagrammSize = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, size, QgsSymbolV2.MM)

                templateStr = self.templateStr
                self.DEBUG and QgsMessageLog.logMessage('#'*30, 'BubbleSymbolLayer') #DEBUG
                for d in self.diagrammProps:
                    self.DEBUG and QgsMessageLog.logMessage('*'*10, 'BubbleSymbolLayer') #DEBUG
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
                                    self.DEBUG and QgsMessageLog.logMessage('val={},koef={},scale={} '.format(val, koef, scale), 'BubbleSymbolLayer') #DEBUG                                   
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
                                self.DEBUG and QgsMessageLog.logMessage('ds={} '.format(ds), 'BubbleSymbolLayer') #DEBUG
                                if ds > scaleMaxRadius:
                                    ds = scaleMaxRadius
                                if ds < scaleMinRadius:
                                    ds = scaleMinRadius
                            for slice in newSlices:
                                slice.percent = slice.percent / sum

                            ds = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, ds, QgsSymbolV2.MM)
                            self.DEBUG and QgsMessageLog.logMessage('ds={} '.format(ds), 'BubbleSymbolLayer') #DEBUG
                            diagramm = DiagrammDesc(ds, newSlices, sum * koef )
                            diagramms.append(diagramm)

                    if 'labels' in d:
                        labels = d['labels']
                        self.DEBUG and QgsMessageLog.logMessage('labels: {}'.format(labels), 'BubbleSymbolLayer') #DEBUG
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
                    diagrammSize = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, float_t(size), QgsSymbolV2.MM)

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
            self.DEBUG and QgsMessageLog.logMessage("\n".join(map(str,diagramms)), 'BubbleSymbolLayer') #DEBUG
            if self.showDiagramms:
                for idx,desc in enumerate(diagramms):
                    #--- Fix for diagramms with identicaly size
                    if diagramms[idx-1].mDiagrammSize==desc.mDiagrammSize or (idx>0 and diagramms[idx-1].mDiagrammSize<desc.mDiagrammSize):
                        desc.mDiagrammSize=desc.mDiagrammSize*0.8
                        if desc.mDiagrammSize<=0:desc.mDiagrammSize=1
                    self.DEBUG and QgsMessageLog.logMessage("diagram {} size:{}".format(str(idx),str(desc.mDiagrammSize)), 'BubbleSymbolLayer') #DEBUG
                    rect = QRectF(point, QSizeF(desc.mDiagrammSize, desc.mDiagrammSize))
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
            labelSize = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, self.labelSize, QgsSymbolV2.Pixel)

            font = QFont()
            font.setPointSizeF(labelSize);
            p.setFont(font)

            if self.mXIndex >= 0 and self.mYIndex >= 0:
                xVal = 0.0
                yVal = 0.0
                if attrs[self.mXIndex]:
                    xVal = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, float_t(attrs[self.mXIndex]), QgsSymbolV2.MM)
                if attrs[self.mYIndex]:
                    yVal = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, float_t(attrs[self.mYIndex]), QgsSymbolV2.MM)
                widthVal = 10

                #if xVal != 0 or yVal != 0:
                pt1 = point + QPointF(xVal, yVal)
                
                st = QStaticText(labelTemplate);
                opt = st.textOption()
                opt.setWrapMode(QTextOption.NoWrap)
                st.setTextOption(opt)
                st.prepare(p.transform(), p.font())
                widthVal = st.size().width()
                
                pt2 = point + QPointF(xVal + widthVal, yVal)

                pen = QPen(Qt.black)
                pen.setWidth(2)
                p.setPen(pen)
                if point.x() < (pt1.x() + pt2.x()) / 2 :
                    if self.showLineouts:
                        p.drawLine(point, pt1)
                        p.drawLine(pt1, pt2)
                    if labelTemplate and labelTemplate != NULL and self.showLabels:
                        p.drawStaticText(pt1.x(), pt1.y(), st)
                else:
                    if self.showLineouts:
                        p.drawLine(point, pt2)
                        p.drawLine(pt2, pt1)
                    if labelTemplate and labelTemplate != NULL and self.showLabels:
                        p.drawStaticText(pt1.x(), pt1.y(), st)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            #QgsMessageLog.logMessage('renderPoint: ' + str(e), 'BubbleSymbolLayer')
            QgsMessageLog.logMessage('renderPoint: {} {} {} {}'.format(str(e),exc_type, fname, exc_tb.tb_lineno), 'BubbleSymbolLayer')


    def startRender(self, context):
        self.fields = context.fields()
        if self.fields:
            self.mXIndex = self.fields.fieldNameIndex("labloffx")    #LablOffX
            self.mYIndex = self.fields.fieldNameIndex("labloffy")    #LablOffY
            self.mDiagrammIndex = self.fields.fieldNameIndex(OLD_NEW_FIELDNAMES[0])
            if self.mDiagrammIndex < 0:
                self.mDiagrammIndex = self.fields.fieldNameIndex(OLD_NEW_FIELDNAMES[1])
        else:
            self.mXIndex = -1
            self.mYIndex = -1
            self.mDiagrammIndex= -1

        self.prepareExpressions(context)
        QgsMarkerSymbolLayerV2.startRender(self, context)

    def clone(self):
        return BubbleSymbolLayer(self.properties())



FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_renderer_base.ui'))

class BabbleSymbolLayerWidget(QgsSymbolLayerV2Widget, FORM_CLASS):
    def __init__(self, parent=None, vectorLayer = None):
        QgsSymbolLayerV2Widget.__init__(self, parent, vectorLayer)

        self.setupUi(self)

        self.layer = None
        self.expressionIndex = 0


    def setSymbolLayer(self, layer):
        if layer.layerType() != BubbleSymbolLayer.LAYERTYPE:
            return

        self.layer = layer
        self.showLineouts.setChecked(layer.showLineouts)
        self.showLabels.setChecked(layer.showLabels)
        self.showDiagramms.setChecked(layer.showDiagramms)
        self.mLabelSizeSpinBox.setValue(layer.labelSize)
        self.editTemplateStr.setText(layer.templateStr)
        self.editDiagrammStr.setPlainText(layer.diagrammStr)

    def symbolLayer(self):
        return self.layer
    
    def on_editTemplateStr_txt_changed(self,val):
        self.DEBUG and QgsMessageLog.logMessage('on_editTemplateStr_txt_changed', 'BubbleSymbolLayer')
        self.layer.templateStr=val
        self.emit(SIGNAL("changed()"))
        pass

    def on_editDiagrammStr_txt_changed(self):
        self.DEBUG and QgsMessageLog.logMessage('on_editDiagrammStr_txt_changed', 'BubbleSymbolLayer')
        self.layer.diagrammStr=self.editDiagrammStr.toPlainText()
        self.emit(SIGNAL("changed()"))
        
        pass

    def on_showLineouts_toggled(self, value):
        self.DEBUG and QgsMessageLog.logMessage('on_showLineouts_toggled', 'BubbleSymbolLayer')
        self.layer.showLineouts = value
        self.emit(SIGNAL("changed()"))

    def on_showLabels_toggled(self, value):
        self.DEBUG and QgsMessageLog.logMessage('on_showLabels_toggled', 'BubbleSymbolLayer')
        self.layer.showLabels = value
        self.emit(SIGNAL("changed()"))

    def on_showDiagramms_toggled(self, value):
        self.DEBUG and QgsMessageLog.logMessage('on_showDiagramms_toggled', 'BubbleSymbolLayer')
        self.layer.showDiagramms = value
        self.emit(SIGNAL("changed()"))

    @pyqtSlot(float)
    def on_mLabelSizeSpinBox_valueChanged(self, value):
        self.DEBUG and QgsMessageLog.logMessage('on_mLabelSizeSpinBox_valueChanged', 'BubbleSymbolLayer')
        self.layer.labelSize = value
        self.emit(SIGNAL("changed()"))


class BabbleSymbolLayerMetadata(QgsSymbolLayerV2AbstractMetadata):

    def __init__(self):
        QgsSymbolLayerV2AbstractMetadata.__init__(self, BubbleSymbolLayer.LAYERTYPE, u"Круговые диаграммы PDS", QgsSymbolV2.Marker)

    def createSymbolLayer(self, props):
        return BubbleSymbolLayer(props)

    def createSymbolLayerWidget(self, vectorLayer):
        return BabbleSymbolLayerWidget(None, vectorLayer)




