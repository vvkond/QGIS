# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QgisPDS
                                 A QGIS plugin
 PDS link
                              -------------------
        begin                : 2016-11-05
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Viktor Kondrashov
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
from bblInit import MyStruct
import random
import os
import xml.etree.cElementTree as ET

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

class DiagrammDesc(MyStruct):
    mDiagrammSize = 0.0
    mSlices = []

class BubbleSymbolLayer(QgsMarkerSymbolLayerV2):

    LAYERTYPE="BubbleDiagramm"

    def __init__(self, props):
        QgsMarkerSymbolLayerV2.__init__(self)
        self.radius = 4.0
        self.color = QColor(255,0,0)

        self.showLineouts = props[QString("showLineouts")] == "True" if QString("showLineouts") in props else True
        self.showLabels = props[QString("showLabels")] == "True" if QString("showLabels") in props else True
        self.showDiagramms = props[QString("showDiagramms")] == "True" if QString("showDiagramms") in props else True
        self.labelSize = float(props[QString("labelSize")]) if QString("labelSize") in props else 7.0

        self.mXIndex = -1
        self.mYIndex = -1
        self.mWIndex = -1

    def layerType(self):
        return BubbleSymbolLayer.LAYERTYPE

    def properties(self):
        return { "showLineouts" : 'True' if self.showLineouts else 'False',
                 "showLabels" : 'True' if self.showLabels else 'False',
                 "showDiagramms" : 'True' if self.showDiagramms else 'False',
                 "labelSize" : str(self.labelSize)}


    def startRender(self, context):
        pass

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

    def renderPoint(self, point, context):
        feature = context.feature()
        p = context.renderContext().painter()

        if not feature:
            labelSize = QgsSymbolLayerV2Utils.convertToPainterUnits(context.renderContext(), self.size(), self.sizeUnit())
            self.drawPreview(p, QPointF(point.x() - labelSize / 2, point.y() - labelSize / 2), QSizeF(labelSize, labelSize))
            return

        xmlString = feature['BubbleFields']
        if not xmlString:
            return

        ctx = context.renderContext()

        labelTemplate = ''
        diagramms = []
        root = ET.fromstring(xmlString)
        for diag in root.findall('diagramm'):
            size = str(diag.attrib['size'])
            diagrammSize = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, float(size), QgsSymbolV2.MM)

            if diagrammSize > 0:
                slices = []
                for values in diag.findall('value'):
                    bc = QgsSymbolLayerV2Utils.decodeColor(values.attrib['backColor'])
                    lc = QgsSymbolLayerV2Utils.decodeColor(values.attrib["lineColor"])
                    prnc = float(values.text)
                    fn = values.attrib["fieldName"]
                    slice = DiagrammSlice(backColor=bc, lineColor=lc, percent=prnc, fieldName=fn)
                    slices.append(slice)

                diagramm = DiagrammDesc(mDiagrammSize = diagrammSize, mSlices = slices)
                diagramms.append(diagramm)

        for label in root.findall('label'):
            labelTemplate = label.attrib['labelText']

        sorted(diagramms, key=lambda diagramm: diagramm.mDiagrammSize)

        if self.showDiagramms:
            for desc in diagramms:
                rect = QRectF(point, QSizeF(desc.mDiagrammSize, desc.mDiagrammSize))
                rect.translate(-diagrammSize / 2, -diagrammSize / 2)
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

        labelSize = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, self.labelSize, QgsSymbolV2.Pixel)

        font = QFont()
        font.setPointSizeF(labelSize);
        p.setFont(font)

        if self.mXIndex >= 0 and self.mYIndex >= 0:
            xVal = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, float(feature['LablOffX']), QgsSymbolV2.MM)
            yVal = QgsSymbolLayerV2Utils.convertToPainterUnits(ctx, float(feature['LablOffY']), QgsSymbolV2.MM)
            widthVal = 10

            if xVal != 0 or yVal != 0:
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
                    if labelTemplate and self.showLabels:
                        p.drawStaticText(pt1.x(), pt1.y(), st)
                else:
                    if self.showLineouts:
                        p.drawLine(point, pt2)
                        p.drawLine(pt2, pt1)
                    if labelTemplate and self.showLabels:
                        p.drawStaticText(pt1.x(), pt1.y(), st)


    def startRender(self, context):
        fields = context.fields()
        if fields:
            self.mXIndex = fields.fieldNameIndex("LablOffX")
            self.mYIndex = fields.fieldNameIndex("LablOffY")
            self.mWIndex = fields.fieldNameIndex("LablWidth")
        else:
            self.mXIndex = -1
            self.mYIndex = -1
            self.mWIndex = -1

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

    def symbolLayer(self):
        return self.layer

    def on_showLineouts_toggled(self, value):
        self.layer.showLineouts = value
        self.emit(SIGNAL("changed()"))

    def on_showLabels_toggled(self, value):
        self.layer.showLabels = value
        self.emit(SIGNAL("changed()"))

    def on_showDiagramms_toggled(self, value):
        self.layer.showDiagramms = value
        self.emit(SIGNAL("changed()"))

    @pyqtSlot(float)
    def on_mLabelSizeSpinBox_valueChanged(self, value):
        self.layer.labelSize = value
        self.emit(SIGNAL("changed()"))


class BabbleSymbolLayerMetadata(QgsSymbolLayerV2AbstractMetadata):

    def __init__(self):
        QgsSymbolLayerV2AbstractMetadata.__init__(self, BubbleSymbolLayer.LAYERTYPE, u"Круговые диаграммы PDS", QgsSymbolV2.Marker)

    def createSymbolLayer(self, props):
        return BubbleSymbolLayer(props)

    def createSymbolLayerWidget(self, vectorLayer):
        return BabbleSymbolLayerWidget(None, vectorLayer)




