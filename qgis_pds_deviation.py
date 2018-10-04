# -*- coding: utf-8 -*-

from qgis.core import *
from qgis.gui import *
from PyQt4 import QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from processing.tools.vector import VectorWriter
from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from tig_projection import *
import numpy
import ast
import os
import time

from bblInit import STYLE_DIR, USER_DEVI_STYLE,DEVI_STYLE
from utils import load_styles_from_dir, load_style, plugin_path

class QgisPDSDeviation(QObject):
    def __init__(self, iface, project):
        super(QgisPDSDeviation, self).__init__()

        self.plugin_dir = os.path.dirname(__file__)
        self.iface = iface
        self.project = project
        self.dateFormat = u'dd-MM-yyyy'

        self.attrWellId = u'well_id'
        self.attrLatitude = u'latitude'
        self.attrLongitude = u'longitude'
        self.attrSLDNID = "sldnid"
        self.attrAPI = "api"
        self.attrOperator = "Operator"
        self.attrCountry = "Country"
        self.attrDepth = "depth"
        self.attrMeasurement = "measure"
        self.attrElevation = "elevation"
        self.attrDatum = "datum"
        self.attrOn_offshore = "onoffshore"
        self.attrStatus = "status"
        self.attrSymbol = "symbol"
        self.attrSpud_date = "spud_date"
        self.attrGlobal_private = "glb_priv"
        self.attrOwner = "owner"
        self.attrCreated = "created"
        self.attrProject = "project"
        self.attrLablX = "lablx"
        self.attrLablY = "lably"
        self.attrLablOffX = "labloffx"
        self.attrLablOffY = "labloffy"

        self.proj4String = 'epsg:4326'
        self.db = None
        self.wellIdList = []

    def initDb(self):
        if self.project is None:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                self.tr(u'No current PDS project'), level=QgsMessageBar.CRITICAL)

            return False

        connection = create_connection(self.project)
        scheme = self.project['project']
        try:
            self.db = connection.get_db(scheme)
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj is not None:
                self.proj4String = 'PROJ4:' + proj.qgis_string
                destSrc = QgsCoordinateReferenceSystem()
                destSrc.createFromProj4(proj.qgis_string)
                sourceCrs = QgsCoordinateReferenceSystem('epsg:4326')
                self.xform = QgsCoordinateTransform(sourceCrs, destSrc)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Project projection read error {0}: {1}').format(
                                                    scheme, str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return False
        return True

    def setWellList(self, wellList):
        self.wellIdList = wellList

    def createWellLayer(self):
        if not self.initDb():
            return

        self.uri = "LineString?crs={}".format(self.proj4String)
        self.uri += '&field={}:{}'.format(self.attrWellId, "string")
        self.uri += '&field={}:{}'.format(self.attrLatitude, "double")
        self.uri += '&field={}:{}'.format(self.attrLongitude, "double")
        self.uri += '&field={}:{}'.format(self.attrSLDNID, "int")
        self.uri += '&field={}:{}'.format(self.attrAPI, "string")
        self.uri += '&field={}:{}'.format(self.attrOperator, "string")
        self.uri += '&field={}:{}'.format(self.attrCountry, "string")
        self.uri += '&field={}:{}'.format(self.attrDepth, "double")
        self.uri += '&field={}:{}'.format(self.attrMeasurement, "string")
        self.uri += '&field={}:{}'.format(self.attrElevation, "double")
        self.uri += '&field={}:{}'.format(self.attrDatum, "string")
        self.uri += '&field={}:{}'.format(self.attrOn_offshore, "string")
        self.uri += '&field={}:{}'.format(self.attrStatus, "string")
        self.uri += '&field={}:{}'.format(self.attrSymbol, "string")
        self.uri += '&field={}:{}'.format(self.attrSpud_date, "string")
        self.uri += '&field={}:{}'.format(self.attrGlobal_private, "string")
        self.uri += '&field={}:{}'.format(self.attrOwner, "string")
        self.uri += '&field={}:{}'.format(self.attrCreated, "DateTime")
        self.uri += '&field={}:{}'.format(self.attrProject, "string")
        self.uri += '&field={}:{}'.format(self.attrLablX, "double")
        self.uri += '&field={}:{}'.format(self.attrLablY, "double")
        self.uri += '&field={}:{}'.format(self.attrLablOffX, "double")
        self.uri += '&field={}:{}'.format(self.attrLablOffY, "double")

        layer = QgsVectorLayer(self.uri, "Well deviations", "memory")
        if layer is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'),
               self.tr(u'Error create wells layer'), QtGui.QMessageBox.Ok)

            return

        self.loadWells(layer, True, True, False, True, False)
        layer.commitChanges()
        self.db.disconnect()

        settings = QSettings()
        systemEncoding = settings.value('/UI/encoding', 'System')
        scheme = self.project['project']
        layerFile = '/{0}_deviations_{1}.shp'.format(scheme, time.strftime('%d_%m_%Y_%H_%M_%S', time.localtime()))

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

        layerName = 'Well deviations'
        layerList = QgsMapLayerRegistry.instance().mapLayersByName(layerName)
        if len(layerList):
            layerName = layerName + '  ' + time.strftime('%d-%m-%Y %H:%M:%S', time.localtime())

        #Register layer
        layer = QgsVectorLayer(layerFileName, layerName, 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

        layer.setCustomProperty("qgis_pds_type", "pds_well_deviations")
        layer.setCustomProperty("pds_project", str(self.project))

        #Set default style
        palyr = QgsPalLayerSettings()
        palyr.readFromLayer(layer)
        palyr.enabled = True
        palyr.fieldName = self.attrWellId
        palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionX, True, False, '', self.attrLablX)
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionY, True, False, '', self.attrLablY)
        palyr.writeToLayer(layer)

        #---load user styles
        load_styles_from_dir(layer=layer, styles_dir=os.path.join(plugin_path() ,STYLE_DIR, USER_DEVI_STYLE) ,switchActiveStyle=False)
        #---load default style
        load_style(layer=layer, style_path=os.path.join(plugin_path() ,STYLE_DIR ,DEVI_STYLE+".qml"))

        line = QgsSymbolV2.defaultSymbol(layer.geometryType())

        # Create an marker line.
        marker_line = QgsMarkerLineSymbolLayerV2()
        marker_line.setPlacement(QgsMarkerLineSymbolLayerV2.LastVertex)
        line.appendSymbolLayer(marker_line)

        # Add the style to the line layer.
        renderer = QgsSingleSymbolRendererV2(line)
        layer.setRendererV2(renderer)

        return layer

    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')

    def checkWell(self, well_name):
        sql = ("SELECT db_sldnid FROM tig_well_history WHERE rtrim(tig_latest_well_name) = '" + well_name + "' ")

        records = self.db.execute(sql)
        num = 0
        if records:
            for r in records:
                num += 1

        return num


    def loadWells(self, layer, isRefreshKoords, isRefreshData, isSelectedOnly, isAddMissing, isDeleteMissing):
        if self.db is None and layer:
            # prjStr = layer.customProperty("pds_project")
            # self.project = ast.literal_eval(prjStr)
            if not self.initDb():
                return

        if isDeleteMissing:
            deletedWells = []
            with edit(layer):
                for f in layer.getFeatures():
                    well_name = f.attribute(self.attrWellId)
                    if self.checkWell(well_name) < 1:
                        deletedWells.append(well_name)
                        layer.deleteFeature(f.id())
            if len(deletedWells):
                s = self.tr('Deleted from layer') + ': ' + ','.join(str(s) for s in deletedWells)
                QtGui.QMessageBox.warning(None, self.tr(u'Deleted from layer'), s, QtGui.QMessageBox.Ok)

        dbWells = self._readWells()
        if dbWells is None:
            return

        projectName = self.project['project']
        allWells = len(self.wellIdList) < 1

        refreshed = False
        with edit(layer):
            for row in dbWells:
                name = row[0]
                lng = row[19]
                lat = row[20]
                wellId = int(row[1])
                if lng and lat and (allWells or wellId in self.wellIdList):
                    pt = QgsPoint(lng, lat)

                    if self.xform:
                        pt = self.xform.transform(pt)

                    startX = pt.x()
                    startY = pt.y()
                    polyLine = [pt]

                    blob_x = numpy.fromstring(self.db.blobToString(row[21]), '>f').astype('d')
                    blob_y = numpy.fromstring(self.db.blobToString(row[22]), '>f').astype('d')
                    for ip in xrange(len(blob_x)):
                        dx = blob_x[ip]
                        dy = blob_y[ip]
                        pt = QgsPoint(startX+dx, startY+dy)
                        polyLine.append(pt)
                    pt = QgsPoint(pt.x()+0.00000001, pt.y()+0.00000001)
                    polyLine.append(pt)

                    geom = QgsGeometry.fromPolyline(polyLine)

                    num = 0
                    well = None
                    if isSelectedOnly:
                        searchRes = layer.selectedFeatures()
                        for f in searchRes:
                            if f.attribute(self.attrWellId) == name:
                                well = f
                                if isRefreshKoords:
                                    layer.changeGeometry(f.id(), geom)
                                    well.setGeometry(geom)
                                num = num + 1
                                break
                    else:
                        args = (self.attrWellId, name)
                        expr = QgsExpression('\"{0}\"=\'{1}\''.format(*args))
                        searchRes = layer.getFeatures(QgsFeatureRequest(expr))

                        for f in searchRes:
                            refreshed = True
                            well = f
                            if isRefreshKoords:
                                layer.changeGeometry(f.id(), geom)
                                well.setGeometry(geom)
                            num = num + 1

                    if not well and isAddMissing:
                        well = QgsFeature(layer.fields())

                    if well:
                        well.setAttribute(self.attrLablX, pt.x())
                        well.setAttribute(self.attrLablY, pt.y())

                        well.setAttribute(self.attrWellId, name)
                        well.setAttribute(self.attrLatitude, lat)
                        well.setAttribute(self.attrLongitude, lng)
                        well.setAttribute(self.attrSLDNID, row[1])
                        well.setAttribute(self.attrAPI, row[2])
                        well.setAttribute(self.attrOperator, row[3])
                        well.setAttribute(self.attrCountry, row[4])
                        well.setAttribute(self.attrDepth, row[7])
                        try:
                            well.setAttribute(self.attrMeasurement, row[8])
                        except:
                            pass
                        well.setAttribute(self.attrElevation, row[9])
                        well.setAttribute(self.attrDatum, row[10])
                        try:
                            well.setAttribute(self.attrOn_offshore, row[11])
                        except:
                            pass
                        well.setAttribute(self.attrStatus, row[12])
                        well.setAttribute(self.attrSymbol, row[13])
                        well.setAttribute(self.attrSpud_date, str(row[14]))
                        try:
                            well.setAttribute(self.attrGlobal_private, row[15])
                        except:
                            pass
                        well.setAttribute(self.attrOwner, row[16])
                        well.setAttribute(self.attrCreated, QDateTime.fromTime_t(0).addSecs(int(row[17])))
                        well.setAttribute(self.attrProject, projectName)

                        if not num:
                            if not isSelectedOnly:
                                if lat != 0 or lng != 0:
                                    well.setGeometry(geom)
                                    layer.addFeatures([well])
                        elif isRefreshData:
                            layer.updateFeature(well)

        if refreshed:
            self.iface.messageBar().pushMessage(self.tr(u'Layer: {0} refreshed').format(layer.name()), duration=10)

        layer.updateExtents()

    def _readWells(self):
        try:
            return self.db.execute(self.get_sql('WellBottoms.sql'))

        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)
            return None