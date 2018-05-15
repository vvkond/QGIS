# -*- coding: utf-8 -*-

from qgis.core import *
from qgis.gui import *
from PyQt4 import QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from tig_projection import *
import ast
import os
import time
from processing.tools.vector import VectorWriter

debuglevel = 4

def debug(msg, verbosity=1):
    if debuglevel >= verbosity:
        try:
            qDebug(msg)
        except:
            pass

class QgisPDSWells(QObject):

    def __init__(self, iface, project):
        super(QgisPDSWells, self).__init__()

        self.plugin_dir = os.path.dirname(__file__)
        self.iface = iface
        self.project = project
        self.dateFormat = u'dd-MM-yyyy'

        self.attrWellId = u'well_id'
        self.attrLatitude = u'latitude'
        self.attrLongitude = u'longitude'
        self.proj4String = 'epsg:4326'
        self.db = None

    def createWellLayer(self):
        if not self.initDb():
            return

        self.uri = "Point?crs={}".format(self.proj4String)
        self.uri += '&field={}:{}'.format(self.attrWellId, "string")
        self.uri += '&field={}:{}'.format(self.attrLatitude, "double")
        self.uri += '&field={}:{}'.format(self.attrLongitude, "double")

        self.uri += '&field={}:{}'.format("sldnid", "int")
        self.uri += '&field={}:{}'.format("api", "string")
        self.uri += '&field={}:{}'.format("operator", "string")
        self.uri += '&field={}:{}'.format("country", "string")
        self.uri += '&field={}:{}'.format("depth", "double")
        self.uri += '&field={}:{}'.format("measuremen", "string")
        self.uri += '&field={}:{}'.format("elevation", "double")
        self.uri += '&field={}:{}'.format("datum", "string")
        self.uri += '&field={}:{}'.format("on_offshor", "string")
        self.uri += '&field={}:{}'.format("status", "string")
        self.uri += '&field={}:{}'.format("symbol", "string")
        self.uri += '&field={}:{}'.format("spud_date", "string")
        self.uri += '&field={}:{}'.format("global_pri", "string")
        self.uri += '&field={}:{}'.format("owner", "string")
        self.uri += '&field={}:{}'.format("created", "DateTime")
        self.uri += '&field={}:{}'.format("project", "string")

        self.uri += '&field={}:{}'.format("lablx", "double")
        self.uri += '&field={}:{}'.format("lably", "double")
        self.uri += '&field={}:{}'.format("labloffx", "double")
        self.uri += '&field={}:{}'.format("labloffy", "double")
        layer = QgsVectorLayer(self.uri, "PDS Wells", "memory")
        if layer is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(
                u'Error create wells layer'), QtGui.QMessageBox.Ok)

            return

        self.loadWells(layer, True, True, False)
        layer.commitChanges()
        self.db.disconnect()

        settings = QSettings()
        systemEncoding = settings.value('/UI/encoding', 'System')
        scheme = self.project['project']
        layerFile = '/{0}_wells_{1}.shp'.format(scheme, time.strftime('%d_%m_%Y_%H_%M_%S', time.localtime()))
        layerFileName = QgsProject.instance().homePath() + layerFile
        provider = layer.dataProvider()
        fields = provider.fields()
        writer = VectorWriter(layerFileName, systemEncoding,
                              fields,
                              provider.geometryType(), provider.crs())

        features = layer.getFeatures()
        idx = 0
        for f in features:
            try:
                l = f.geometry()
                feat = QgsFeature(f)
                feat.setGeometry(l)
                writer.addFeature(feat)
                idx = idx + 1
            except:
                pass

        del writer

        layerName = 'PDS Wells'
        layerList = QgsMapLayerRegistry.instance().mapLayersByName(layerName)
        if len(layerList):
            layerName = layerName + '  ' + time.strftime('%d-%m-%Y %H:%M:%S', time.localtime())

        layer = QgsVectorLayer(layerFileName, layerName, 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(layer)

        # layer.startEditing()
        layer.setCustomProperty("qgis_pds_type", "pds_wells")
        layer.setCustomProperty("pds_project", str(self.project))

        palyr = QgsPalLayerSettings()
        palyr.readFromLayer(layer)
        palyr.enabled = True
        palyr.fieldName = self.attrWellId
        palyr.placement = QgsPalLayerSettings.OverPoint
        palyr.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
        palyr.setDataDefinedProperty(QgsPalLayerSettings.OffsetXY, True, True,
                                     'format(\'%1,%2\', "labloffx" , "labloffy")', '')
        palyr.labelOffsetInMapUnits = False
        palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionX, True, False, '', 'lablx')
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionY, True, False, '', 'lably')
        palyr.writeToLayer(layer)

        # layer.commitChanges()


        return layer

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

    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')

    def loadWells(self, layer, isRefreshKoords, isRefreshData, isSelectedOnly):
        if self.db is None and layer:
            # prjStr = layer.customProperty("pds_project")
            # self.project = ast.literal_eval(prjStr)
            if not self.initDb():
                return

        dbWells = self._readWells()
        if dbWells is None:
            return

        projectName = self.project['project']

        refreshed = False
        with edit(layer):
            for row in dbWells:
                name= row[0]
                lng = row[20]
                lat = row[19]
                if lng and lat:
                    pt = QgsPoint(lng, lat)
                    
                    if self.xform:
                        pt = self.xform.transform(pt)

                    geom = QgsGeometry.fromPoint(pt)

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

                    if not well:
                        well = QgsFeature(layer.fields())

                    well.setAttribute(self.attrWellId, name)
                    well.setAttribute(self.attrLatitude, lat)
                    well.setAttribute(self.attrLongitude, lng)

                    well.setAttribute('sldnid', row[1])
                    well.setAttribute('api', row[2])
                    well.setAttribute('operator', row[3])
                    well.setAttribute('country', row[4])
                    well.setAttribute('depth', row[7])
                    try:
                        well.setAttribute('measuremen', row[8])
                    except: #Format before shapes
                        well.setAttribute('measurement', row[8])
                    well.setAttribute('elevation', row[9])
                    well.setAttribute('datum', row[10])
                    try:
                        well.setAttribute('on_offshor', row[11])
                    except: #Format before shapes
                        well.setAttribute('on_offshore', row[11])
                    well.setAttribute('status', row[12])
                    well.setAttribute('symbol', row[13])
                    well.setAttribute('spud_date', QDateTime.fromString(row[14], self.dateFormat))
                    try:
                        well.setAttribute('global_pri', row[15])
                    except: #Format before shapes
                        well.setAttribute('global_private', row[15])
                    well.setAttribute('owner', row[16])
                    well.setAttribute('created', QDateTime.fromString(row[17], self.dateFormat))
                    well.setAttribute('project', projectName)

                    if not num:
                        if not isSelectedOnly:
                            if lat != 0 or lng != 0:
                                well.setGeometry(geom)
                                layer.addFeatures([well])
                    elif isRefreshData:
                        layer.updateFeature(well)

        if refreshed:
            self.iface.messageBar().pushMessage(self.tr(u'Layer: {0} refreshed').format(layer.name()), duration=10)


        # palyr = QgsPalLayerSettings()
        # palyr.readFromLayer(layer)
        # palyr.enabled = True
        # palyr.fieldName = self.attrWellId
        # palyr.placement= QgsPalLayerSettings.OverPoint
        # palyr.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
        # palyr.setDataDefinedProperty(QgsPalLayerSettings.OffsetXY , True, True, 'format(\'%1,%2\', "labloffx" , "labloffy")', '')
        # palyr.labelOffsetInMapUnits = False
        # palyr.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'8','')
        # palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionX,True,False,'','lablx')
        # palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionY,True,False,'','lably')
        # palyr.writeToLayer(layer)

        layer.updateExtents()




    def _readWells(self):
        try:
            return self.db.execute(self.get_sql('Wells.sql'))
            # result = self.db.execute(
            #     "select tig_latest_well_name, tig_latitude, tig_longitude from tig_well_history")

            
            # return result
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)
            return None


