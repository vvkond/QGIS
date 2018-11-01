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
from bblInit import STYLE_DIR
from utils import plugin_path, load_styles_from_dir, load_style, edit_layer

debuglevel = 4

def debug(msg, verbosity=1):
    if debuglevel >= verbosity:
        try:
            qDebug(msg)
        except:
            pass

class QgisPDSWells(QObject):

    def __init__(self, iface, project ,styleName=None ,styleUserDir=None):
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
        self.wellIdList = []
        
        self.styleName=styleName
        self.styleUserDir=styleUserDir
        

    def setWellList(self, wellList):
        self.wellIdList = wellList

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

        #---load user styles
        if self.styleUserDir is not None:
            load_styles_from_dir(layer=layer, styles_dir=os.path.join(plugin_path() ,STYLE_DIR, self.styleUserDir) ,switchActiveStyle=False)
        #---load default style
        if self.styleName is not None:
            load_style(layer=layer, style_path=os.path.join(plugin_path() ,STYLE_DIR ,self.styleName+".qml"))

        
        self.loadWells(layer, True, True, False, True, False)
        layer.commitChanges()
        self.db.disconnect()

        settings = QSettings()
        systemEncoding = settings.value('/UI/encoding', 'System')
        scheme = self.project['project']
        layerFile = '/{0}_wells_{1}.shp'.format(scheme, time.strftime('%d_%m_%Y_%H_%M_%S', time.localtime()))

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
            with edit_layer(layer):
                for f in layer.getFeatures():
                    well_name = f.attribute(self.attrWellId)
                    if self.checkWell(well_name) < 1:
                        deletedWells.append(well_name)
                        layer.deleteFeature(f.id())
            if len(deletedWells):
                s = self.tr('Deleted from layer') + ': ' + ','.join(str(s) for s in deletedWells)
                QtGui.QMessageBox.warning(None, self.tr(u'Warning'), s, QtGui.QMessageBox.Ok)

        dbWells = self._readWells()
        if dbWells is None:
            return

        projectName = self.project['project']

        allWells = len(self.wellIdList) < 1

        refreshed = False
        with edit_layer(layer):
            for row in dbWells:
                name= row[0]
                lng = row[20]
                lat = row[19]
                wellId = int(row[1])
                if lng and lat and (allWells or wellId in self.wellIdList):
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

                    if not well and isAddMissing:
                        well = QgsFeature(layer.fields())

                    if well:
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
                        well.setAttribute('spud_date', str(row[14]))
                        try:
                            well.setAttribute('global_pri', row[15])
                        except: #Format before shapes
                            well.setAttribute('global_private', row[15])
                        well.setAttribute('owner', row[16])
                        well.setAttribute('created', QDateTime.fromTime_t(0).addSecs(int(row[17])))
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

        layer.updateExtents()


    def _readWells(self):
        try:
            return self.db.execute(self.get_sql('Wells.sql'))
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)
            return None


