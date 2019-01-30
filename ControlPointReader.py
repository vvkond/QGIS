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


class ControlPointReader(ReaderBase):
    def __init__(self,iface):
        super(ControlPointReader, self).__init__()

        self.db = None
        self.layer = None
        self.iface=iface
        self.plugin_dir = os.path.dirname(__file__)

        self.setNoAttr = u'set_no'
        self.parameterNoAttr = u'param_no'
        self.subsetNoAttr = u'subset_no'
        self.setNameAttr = u'set_name'
        self.paramNameAttr = u'param_name'
        self.subsetNameAttr = u'subsetname'
        self.parameterAttr = u'parameter'

    @cached_property
    def windowTitle(self):
        return self.tr('Control points')        



    def createLayer(self, layerName, pdsProject, groupSetId, defaultValue):
        self.proj4String = QgisProjectionConfig.get_default_layer_prj_epsg()
        try:
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj is not None:
                self.proj4String = 'PROJ4:'+proj.qgis_string
                destSrc = QgsCoordinateReferenceSystem()
                destSrc.createFromProj4(proj.qgis_string)
                sourceCrs = None
                self.xform=get_qgis_crs_transform(sourceCrs,destSrc,self.tig_projections.fix_id)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr('Error'),
                                                self.tr(u'Project projection read error {0}').format(
                                                str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return


        self.uri = "Point?crs={}".format(self.proj4String)
        self.uri += '&field={}:{}'.format(self.setNoAttr, "double")
        self.uri += '&field={}:{}'.format(self.parameterNoAttr, "double")
        self.uri += '&field={}:{}'.format(self.subsetNoAttr, "double")
        self.uri += '&field={}:{}'.format(self.setNameAttr, "string")
        self.uri += '&field={}:{}'.format(self.paramNameAttr, "string")
        self.uri += '&field={}:{}'.format(self.subsetNameAttr, "string")
        self.uri += '&field={}:{}'.format(self.parameterAttr, 'double')
        self.uri += '&field={}:{}'.format("LablX", "double")
        self.uri += '&field={}:{}'.format("LablY", "double")
        layer = QgsVectorLayer(self.uri, layerName, "memory")

        self.readData(layer, groupSetId)

        layer = self.memoryToShp(layer, pdsProject['project'], layerName)

        layer.setCustomProperty("pds_project", str(pdsProject))
        layer.setCustomProperty("qgis_pds_type", "pds_controlpoints")

        palyr = QgsPalLayerSettings()
        palyr.readFromLayer(layer)
        palyr.enabled = True
        palyr.fieldName = 'parameter'
        palyr.placement = QgsPalLayerSettings.OverPoint
        palyr.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
        palyr.labelOffsetInMapUnits = True
        # palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionX, True, False, '', 'LablX')
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionY, True, False, '', 'LablY')
        palyr.writeToLayer(layer)

        layer.commitChanges()

        return layer

    def readData(self, layer, groupSetId):

        # self.tig_projections = TigProjections(db=self.db)
        # proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
        # if proj is not None:
        #     sourceCrs = QgsCoordinateReferenceSystem()
        #     sourceCrs.createFromProj4(proj.qgis_string)
        #     destSrc = QgsCoordinateReferenceSystem('epsg:4326')

        #     xform = QgsCoordinateTransform(sourceCrs, destSrc)
        # else:
        #     self.iface.messageBar().pushMessage(self.tr("Error"),
        #         self.tr(u'Project projection read error'), level=QgsMessageBar.CRITICAL)

        sqlFile = os.path.join(self.plugin_dir, 'db', 'ControlPoints.sql')
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read()
            f.close()

            groups = self.db.execute(sql, group_id=groupSetId[0], set_id=groupSetId[1])

            layer.startEditing()
            for setNo, paramNo, subsetNo, setName, paramName, subsetName, param, mapX, mapY in groups:
                xCoords = numpy.fromstring(self.db.blobToString(mapX), '>d').astype('d')
                yCoords = numpy.fromstring(self.db.blobToString(mapY), '>d').astype('d')
                mapParams = numpy.fromstring(self.db.blobToString(param), '>d').astype('d')

                if len(xCoords) != len(yCoords):
                    self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Coordinate count missmatch'), level=QgsMessageBar.CRITICAL)
                    continue

                i = 0
                for x in xCoords:
                    y = yCoords[i]
                    val = mapParams[i]
                    i = i + 1
                    cPoint = QgsFeature(layer.fields())

                    pt = QgsPoint(x, y)
                    if self.xform:
                        pt = self.xform.transform(pt)
                    
                    # if sourceCrs is not None:
                    #     geom = QgsGeometry.fromPoint(xform.transform(pt))
                    # else:
                    geom = QgsGeometry.fromPoint(pt)
                    cPoint.setGeometry(geom)

                    cPoint.setAttribute(self.setNoAttr, setNo)
                    cPoint.setAttribute(self.parameterNoAttr, paramNo)
                    cPoint.setAttribute(self.subsetNoAttr, subsetNo)
                    cPoint.setAttribute(self.setNameAttr, setName)
                    cPoint.setAttribute(self.paramNameAttr, paramName)
                    cPoint.setAttribute(self.subsetNameAttr, subsetName)
                    if val < 1.0e+20:
                        cPoint.setAttribute(self.parameterAttr, float(val))

                    layer.addFeatures([cPoint])

            layer.commitChanges()

        return
