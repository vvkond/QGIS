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
import random
import os

try:
    from PyQt4.QtCore import QString
except ImportError:
    # we are using Python3 so QString is not defined
    QString = type("")

class BubbleSymbolLayer(QgsMarkerSymbolLayerV2):

    LAYERTYPE="BubbleDiagramm"

    def __init__(self, radius=4.0):
        QgsMarkerSymbolLayerV2.__init__(self)
        self.radius = radius
        self.color = QColor(255,0,0)

    def layerType(self):
        return BubbleSymbolLayer.LAYERTYPE

    def properties(self):
        return { "radius" : str(self.radius) }

    def startRender(self, context):
        pass

    def stopRender(self, context):
        pass

    def renderPoint(self, point, context):
        # Отрисовка зависит от того выделен символ или нет (Qgis >= 1.5)
        color = context.selectionColor() if context.selected() else self.color
        p = context.renderContext().painter()
        p.setPen(color)
        p.drawEllipse(point, self.radius, self.radius)

    def clone(self):
        return BubbleSymbolLayer(self.radius)

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
        # self.spinRadius.setValue(layer.radius)

    def symbolLayer(self):
        return self.layer

    def radiusChanged(self, value):
        self.layer.radius = value
        self.emit(SIGNAL("changed()"))

    @pyqtSlot()
    def on_addAttributePushButton_clicked(self):
        if not self.layer:
            return

        frame = QFrame(self)
        objectName = 'expression' + str(self.expressionIndex)
        frame.setObjectName(objectName)
        self.expressionIndex = self.expressionIndex + 1

        lay = QHBoxLayout(frame)
        frame.setLayout(lay)
        lay.setContentsMargins(0, 0, 0, 0)

        fieldBtn = QToolButton(frame)
        fieldBtn.setIcon(QIcon(u':/plugins/QgisPDS/symbologyRemove.png'))
        fieldBtn.clicked.connect(lambda: self.deleteExpressionButtonClicked(frame))
        lay.addWidget(fieldBtn)

        #Field expression
        fieldEx = QgsFieldExpressionWidget(frame)
        lay.addWidget(fieldEx)
        fieldEx.setLayer(self.vectorLayer())

        # field color
        fieldColor = QgsColorButtonV2(frame)
        lay.addWidget(fieldColor)

        fieldText = QLineEdit(frame)
        lay.addWidget(fieldText)

        fieldEx.fieldChanged.connect(lambda: self.exprFieldChanged(fieldEx, fieldText))

        lay.setStretch(1, 1)

        self.attributesContiner.addWidget(frame)

    def deleteExpressionButtonClicked(self, parentFrame):
        if parentFrame:
            parentFrame.deleteLater()

    def exprFieldChanged(self, fieldEx, fieldText):
        if fieldEx and fieldText and not fieldText.text():
            fieldText.setText(fieldEx.currentText())


class BabbleSymbolLayerMetadata(QgsSymbolLayerV2AbstractMetadata):

    def __init__(self):
        QgsSymbolLayerV2AbstractMetadata.__init__(self, BubbleSymbolLayer.LAYERTYPE, u"Круговые диаграммы PDS", QgsSymbolV2.Marker)

    def createSymbolLayer(self, props):
        radius = float(props[QString("radius")]) if QString("radius") in props else 4.0
        return BubbleSymbolLayer(radius)

    def createSymbolLayerWidget(self, vectorLayer):
        return BabbleSymbolLayerWidget(None, vectorLayer)




