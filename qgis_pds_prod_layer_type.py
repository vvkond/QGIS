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
        email                : viktor@gmail.com
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

from qgis_pds_prod_layer import *

class QgisPDSProductionLayerType(QgsPluginLayerType):

    def __init__(self, iface, add_callback):
        QgsPluginLayerType.__init__(self, QgisPDSProductionLayer.LAYER_TYPE)

        self.iface = iface
        self.add_callback = add_callback

    def createLayer(self):
        layer = QgisPDSProductionLayer(self.iface)
        self.add_callback(layer)
        return 

    def showLayerProperties(self, layer):

        # indicate that we have shown the properties dialog
        return False