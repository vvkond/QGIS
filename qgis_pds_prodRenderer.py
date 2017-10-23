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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import random

try:
    from PyQt4.QtCore import QString
except ImportError:
    # we are using Python3 so QString is not defined
    QString = type("")

class FooSymbolLayer(QgsSvgMarkerSymbolLayerV2):
    LAYER_TYPE="Bubbles"

    def __init__(self, radius=4.0):
        super(FooSymbolLayer, self).__init__(name = QString("Bubbles"),
                                            color = QColor(255, 0, 0),
                                            borderColor = QColor(0,0,0),
                                            size = 2,
                                            angle = 0,
                                            scaleMethod = QgsSymbolV2.ScaleDiameter)
        self.radius = radius

#    def layerType(self):
#        return QString("Bubbles")

    def clone(self):
        return FooSymbolLayer(self.radius)



class FooSymbolLayerWidget(QgsSymbolLayerV2Widget):
    def __init__(self, parent=None):
        super(FooSymbolLayerWidget, self).__init__(parent)

        qDebug("create production layer")
        self.layer = None

        # setup a simple UI
        self.label = QLabel("Radius:")
        self.spinRadius = QDoubleSpinBox()
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.label)
        self.hbox.addWidget(self.spinRadius)
        self.setLayout(self.hbox)
        self.connect(self.spinRadius, SIGNAL("valueChanged(double)"), \
            self.radiusChanged)

    def setSymbolLayer(self, layer):
        if layer.layerType() != "Bubbles":
            return
        self.layer = layer
        self.spinRadius.setValue(layer.radius)

    def symbolLayer(self):
        return self.layer

    def radiusChanged(self, value):
        self.layer.radius = value
        self.emit(SIGNAL("changed()"))


class FooSymbolLayerMetadata(QgsSymbolLayerV2AbstractMetadata):

    def __init__(self):
        qDebug("create production")
        QgsSymbolLayerV2AbstractMetadata.__init__(self, QString("Bubbles"),
                                        QString("Production bubbles"),
                                        QgsSymbolV2.Marker)

    def createSymbolLayer(self, props):
        qDebug("createSymbolLayer called");
        radius = float(props[QString("radius")]) if QString("radius") in props else 4.0
        return FooSymbolLayer(radius)

#    def createSymbolLayerWidget(self, layer):
#        return None
#        qDebug("About to create layer widget")
#        return FooSymbolLayerWidget()




