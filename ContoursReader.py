# -*- coding: utf-8 -*-

import os
import numpy
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from tig_projection import *
from ReaderBase import *


class ContoursReader(ReaderBase):
    def __init__(self, _dataType):
        super(ContoursReader, self).__init__()

        self.plugin_dir = os.path.dirname(__file__)

        self.setNoAttr = u'set_no'
        self.parameterNoAttr = u'parameter_no'
        self.subsetNoAttr = u'subset_no'
        self.setNameAttr = u'set_name'
        self.paramNameAttr = u'param_name'
        self.subsetNameAttr = u'subset_name'
        self.paramAttr = u'parameter'
        self.varNameAttr = u'variable_name'

        self.dataType = _dataType
        if self.dataType == 0:      #Contours
            self.groupFile = "Contours_group.sql"
            self.setFile = "Contours_set.sql"
            self.dataFile = "Contours.sql"
            self.geomType = "LineString"
            self.pdsType = "pds_contours"
        elif self.dataType == 1:         #Polygons
            self.groupFile = "Polygons_group.sql"
            self.setFile = "Polygons_set.sql"
            self.dataFile = "Polygons.sql"
            self.geomType = "Polygon"
            self.pdsType = "pds_polygon"
        else:                   #Faults
            self.groupFile = "Faults_group.sql"
            self.setFile = "Faults_set.sql"
            self.dataFile = "Faults.sql"
            self.geomType = "LineString"
            self.pdsType = "pds_faults"


    @cached_property
    def windowTitle(self):
        if self.dataType == 0:
            return self.tr('Contours')
        elif self.dataType == 1:         #Polygons
            return self.tr('Polygons')
        else:
            return self.tr('Faults')

    def setupGui(self, dialog):
        self.dialog = dialog
        if self.dataType > 1:
            super(ContoursReader, self).setupGui(dialog)
        if self.dataType == 1:
            dialog.mLoadAsContourCheckBox.setVisible(True)
        else:
            dialog.mLoadAsContourCheckBox.setVisible(False)


    def createLayer(self, layerName, pdsProject, groupSetId, defaultValue):
        self.defaultParameter = defaultValue

        proj4String = 'epsg:4326'
        try:
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj is not None:
                proj4String = 'PROJ4:'+proj.qgis_string
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr('Error'),
                                                self.tr(u'Project projection read error {0}: {1}').format(
                                                scheme, str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return

        if self.dataType == 1 and self.dialog.mLoadAsContourCheckBox.isChecked():
            self.geomType = "LineString"

        self.uri = self.geomType + "?crs={}".format(proj4String)
        self.uri += '&field={}:{}'.format(self.setNoAttr, "double")
        self.uri += '&field={}:{}'.format(self.parameterNoAttr, "double")
        self.uri += '&field={}:{}'.format(self.subsetNoAttr, "double")
        self.uri += '&field={}:{}'.format(self.setNameAttr, "string")
        self.uri += '&field={}:{}'.format(self.paramNameAttr, "string")
        self.uri += '&field={}:{}'.format(self.subsetNameAttr, "string")
        self.uri += '&field={}:{}'.format(self.paramAttr, "double")
        self.uri += '&field={}:{}'.format(self.varNameAttr, "string")
        layer = QgsVectorLayer(self.uri, layerName, "memory")

        layer.startEditing()
        layer.setCustomProperty("pds_project", str(pdsProject))
        layer.setCustomProperty("qgis_pds_type", self.pdsType)

        self.readData(layer, groupSetId)

        layer.commitChanges()

        return layer

    def readData(self, layer, groupSetId):
        sqlFile = os.path.join(self.plugin_dir, 'db', self.dataFile)
        uniqSymbols = set()
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read()
            f.close()

            groups = self.db.execute(sql, group_id=groupSetId[0], set_id=groupSetId[1])

            layer.startEditing()
            # for setNo, paramNo, subsetNo, setName, paramName, subsetName, mapX, mapY, mapZ, varName in groups:
            for raw in groups:
                xCoords = numpy.fromstring(raw[6].read(), '>d').astype('d')
                yCoords = numpy.fromstring(raw[7].read(), '>d').astype('d')

                param = 0
                # paramLen = 0
                # if self.dataType > 0:   #Faults, #Contours
                zParams = numpy.fromstring(raw[8].read(), '>d').astype('d')
                paramLen = len(zParams)

                if len(xCoords) != len(yCoords):
                    self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Coordinates length unmatched'), level=QgsMessageBar.CRITICAL)
                    continue

                i = 0
                polyLine = []                
                for x in xCoords:
                    y = yCoords[i]
                    # if self.dataType > 0 and i < paramLen:
                    if i < paramLen and self.defaultParameter == -9999:
                        param = zParams[i]
                    else:
                        param = self.defaultParameter

                    cPoint = QgsFeature(layer.fields())

                    pt = QgsPoint(x, y)
                    polyLine.append(pt)

                    i = i + 1

                if len(polyLine):
                    if self.dataType == 1 and not self.dialog.mLoadAsContourCheckBox.isChecked():
                        cPoint.setGeometry(QgsGeometry.fromPolygon([polyLine]))
                    else:
                        cPoint.setGeometry(QgsGeometry.fromPolyline(polyLine))

                    cPoint.setAttribute(self.setNoAttr, raw[0])
                    cPoint.setAttribute(self.parameterNoAttr, raw[1])
                    cPoint.setAttribute(self.subsetNoAttr, raw[2])
                    cPoint.setAttribute(self.setNameAttr, raw[3])
                    cPoint.setAttribute(self.paramNameAttr, raw[4])
                    cPoint.setAttribute(self.subsetNameAttr, raw[5])
                    cPoint.setAttribute(self.paramAttr, float(param))
                    if len(raw) > 9:
                        cPoint.setAttribute(self.varNameAttr, raw[9])

                    uniqSymbols.add(raw[5])

                    layer.addFeatures([cPoint])

        categories = []
        for ss in uniqSymbols:
            symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
            category = QgsRendererCategoryV2(ss, symbol, ss)
            categories.append(category)

        renderer = QgsCategorizedSymbolRendererV2(self.subsetNameAttr, categories)
        layer.setRendererV2(renderer)
        layer.commitChanges()

        return
