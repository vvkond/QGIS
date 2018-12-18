# -*- coding: utf-8 -*-

import os
import numpy
import time
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from qgis.PyQt.QtGui  import *
from qgis.PyQt.QtCore import *

from QgisPDS.db import Oracle
from connections import create_connection
from QgisPDS.utils import to_unicode
from QgisPDS.tig_projection import *
from utils import edit_layer,WithQtProgressBar

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_zonations_base.ui'))
IS_DEBUG=False
IS_USE_PUBLIC_DEVI_ONLY=True
#===============================================================================
# 
#===============================================================================
class QgisPDSCoordFromZoneDialog(QtGui.QDialog, FORM_CLASS, WithQtProgressBar):
    #===========================================================================
    # 
    #===========================================================================
    def __init__(self, _project, _iface, _editLayer, parent=None):
        """Constructor."""
        super(QgisPDSCoordFromZoneDialog, self).__init__(parent)

        self.setupUi(self)

        self.mParameterFrame.setVisible(False)
        self.mTwoLayers.setVisible(False)

        self.plugin_dir = os.path.dirname(__file__)
        self.iface = _iface
        self.project = _project
        self.editLayer = _editLayer
        

        if _project:
            self.scheme = _project['project']
        else:
            self.scheme = ''

        try:
            connection = create_connection(self.project)
            scheme = self.project['project']
            if scheme:
                self.setWindowTitle(self.windowTitle() + ' - ' + scheme)

            self.db = connection.get_db(scheme)
        except Exception as e:
            self.errorMessage(self.tr(u'{0}').format(str(e)))
            return

        self.proj4String = 'epsg:4326'
        try:
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj is not None:
                self.proj4String = 'PROJ4:'+proj.qgis_string
                destSrc = QgsCoordinateReferenceSystem()
                destSrc.createFromProj4(proj.qgis_string)
                sourceCrs = QgsCoordinateReferenceSystem('epsg:4326')
                self.xform = QgsCoordinateTransform(sourceCrs, destSrc)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Project projection read error {0}: {1}').format(
                                                scheme, str(e)),
                                                level=QgsMessageBar.CRITICAL)

        settings = QSettings()
        selectedZonations = settings.value("/PDS/Zonations/SelectedZonations/v"+self.scheme, [])
        selectedZones = settings.value("/PDS/Zonations/selectedZones/v"+self.scheme, [])

        self.selectedZonations = [int(z) for z in selectedZonations]
        self.selectedZones = [int(z) for z in selectedZones]


        self.fillZonations()
    #===========================================================================
    # 
    #===========================================================================
    def errorMessage(self, msg):
        self.iface.messageBar().pushMessage(self.tr("Error"), msg, level=QgsMessageBar.CRITICAL)
    #===========================================================================
    # 
    #===========================================================================
    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')
    #===========================================================================
    # 
    #===========================================================================
    def on_buttonBox_accepted(self):
        self.process()
    #===========================================================================
    # 
    #===========================================================================
    def process(self):
        global IS_DEBUG, IS_USE_PUBLIC_DEVI_ONLY
        IS_DEBUG=     self.isDebugChkBox.isChecked()
        IS_USE_PUBLIC_DEVI_ONLY= self.isOnlyPublicDeviChkBox.isChecked()
        selectedZonations = []
        selectedZones = []
        self.no_devi_wells=[]
        for si in self.zonationListWidget.selectedItems():
            selectedZonations.append(int(si.data(Qt.UserRole)))

        dataProvider = self.editLayer.dataProvider()

        sel = None
        for zones in self.zoneListWidget.selectedItems():
            sel = zones.data(Qt.UserRole)
            selectedZones.append(sel[0])

        if sel is None:
            return

        idxMd = dataProvider.fieldNameIndex('MD')
        idxTvd = dataProvider.fieldNameIndex('TVD')
        if idxMd < 0:
            dataProvider.addAttributes([QgsField("MD", QVariant.Double)])
        if idxTvd < 0:
            dataProvider.addAttributes([QgsField("TVD", QVariant.Double)])

        idx1 = dataProvider.fieldNameIndex('Well identifier')

        
        self.showProgressBar(msg="Update well location", maximum=self.editLayer.featureCount())
        now=time.time()
        
        with edit_layer(self.editLayer):
            for idx,feature in enumerate(self.editLayer.getFeatures()):
                self.progress.setValue(idx)
                if time.time()-now>1:  QCoreApplication.processEvents();time.sleep(0.02);now=time.time() #refresh GUI
                if idx1 >= 0:
                    tigWellId = feature[u'Well identifier']
                else:
                    tigWellId = feature['well_id']
                coords = self._getCoords(sel, tigWellId)
                if coords is not None:
                    IS_DEBUG and QgsMessageLog.logMessage(u"\t move well {} to {}".format(tigWellId,coords), tag="QgisPDS.coordFromZone")
                    geom = QgsGeometry.fromPoint(coords)
                    self.editLayer.changeGeometry(feature.id(), geom)
                    #self.editLayer.commitChanges()  #--- commit each row
                    #self.editLayer.startEditing()   #--- and start edit again

        settings = QSettings()
        settings.setValue("/PDS/Zonations/SelectedZonations/v"+self.scheme, selectedZonations)
        settings.setValue("/PDS/Zonations/selectedZones/v"+self.scheme, selectedZones)
        
        QgsMessageLog.logMessage(self.tr(u"\t Deviation is private or no deviation in wells: {} ").format(",".join(self.no_devi_wells)), tag="QgisPDS.coordFromZone")
    #===========================================================================
    # 
    #===========================================================================
    def on_zonationListWidget_itemSelectionChanged(self):
        self.zoneListWidget.clear()
        for si in self.zonationListWidget.selectedItems():
            self._fillZones(int(si.data(Qt.UserRole)))
        if len(self.zoneListWidget.selectedItems()) < 1:
            self.zoneListWidget.setCurrentRow(0)
    #===========================================================================
    # 
    #===========================================================================
    def _getCoords(self, zoneDef, wellId):
        def read_floats(index):
            return numpy.fromstring(self.db.blobToString(input_row[index]), '>f').astype('d')

        newCoords = None
        sql = self.get_sql('ZonationCoords.sql')
        records = self.db.execute(sql
                                  , well_id=wellId
                                  , zonation_id=zoneDef[1]
                                  , zone_id=None
                                  , interval_order=zoneDef[2]
                                  , only_pub_devi=1 if IS_USE_PUBLIC_DEVI_ONLY else None
                                  )  #zoneDef= i_id, zonationId, i_order, i_level
        if records is not None:
            for input_row in records:
                devi_id=input_row[15]
                if devi_id is None:
                    self.no_devi_wells.append(wellId)
                else:
                    x = read_floats(16)
                    y = read_floats(17)
                    md = read_floats(18)
                    tvd = read_floats(19)
                    depth = input_row[3]
                    lon = input_row[9]
                    lat = input_row[10]
                    pt = QgsPoint(lon, lat)
                    if self.xform:
                        pt = self.xform.transform(pt)
                    IS_DEBUG and QgsMessageLog.logMessage(u"\t well {} zone {} tvd {}".format(wellId, zoneDef[0], tvd), tag="QgisPDS.coordFromZone")
                    newCoords = self._calcOffset(pt.x(), pt.y(), x, y, md, tvd, depth)
        return newCoords
    #===========================================================================
    # 
    #===========================================================================
    def _calcOffset(self, lon, lat, x, y, md, tvd, depth):
        jp = None
        lastIdx = len(x) - 1
        for ip in xrange(len(x) - 1):
            if md[ip] <= depth <= md[ip + 1]:
                jp = ip

        xPosition = 0
        yPosition = 0
        if jp is not None:
            rinterp = (depth - md[jp]) / (md[jp + 1] - md[jp])
            xPosition = x[jp] + rinterp * (x[jp + 1] - x[jp])
            yPosition = y[jp] + rinterp * (y[jp + 1] - y[jp])
        elif depth >= md[lastIdx]:
            xPosition = x[lastIdx]
            yPosition = y[lastIdx]

        # newCoords = self.lon_lat_add(lon, lat, xPosition, yPosition)
        newCoords = QgsPoint(lon+xPosition, lat+yPosition)

        return newCoords
    #===========================================================================
    # 
    #===========================================================================
    def lon_lat_add(self, lon, lat, x, y):
        meterCrs = QgsCoordinateReferenceSystem()
        meterCrs.createFromProj4('+proj=tmerc +lon_0={} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(lon))
        geoCrs = QgsCoordinateReferenceSystem('epsg:4326')

        toMeters = QgsCoordinateTransform(geoCrs, meterCrs)
        toGeo = QgsCoordinateTransform(meterCrs, geoCrs)

        geoPt = QgsPoint(lon, lat)
        mPt = toMeters.transform(geoPt)

        return toGeo.transform(QgsPoint(mPt.x()+x, mPt.y()+y))
    #===========================================================================
    # 
    #===========================================================================
    def fillZonations(self):
        sqlFile = os.path.join(self.plugin_dir, 'db', 'ZonationParams_zonation.sql')
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read()
            f.close()

            records = self.db.execute(sql)

            scrollToItem = None
            for id,desc in records:
                item = QListWidgetItem(to_unicode(desc))
                item.setData(Qt.UserRole, id)
                self.zonationListWidget.addItem(item)

                if id in self.selectedZonations:
                    item.setSelected(True)
                    if scrollToItem is None:
                        scrollToItem = item

            self.zonationListWidget.scrollToItem(scrollToItem)

        return
    #===========================================================================
    # 
    #===========================================================================
    def _fillZones(self, zonationId):
        sqlFile = os.path.join(self.plugin_dir, 'db', 'ZonationParams_zone.sql')
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read()
            f.close()

            records = self.db.execute(sql, zonation_id=zonationId)

            scrollToItem = None
            for i_id, i_desc, i_name, i_order, i_level in records:
                item = QListWidgetItem(to_unicode(i_desc))
                item.setData(Qt.UserRole, [i_id, zonationId, i_order, i_level])
                self.zoneListWidget.addItem(item)

                if i_id in self.selectedZones:
                    item.setSelected(True)
                    if scrollToItem is None:
                        scrollToItem = item

            self.zoneListWidget.scrollToItem(scrollToItem)

        return
    #===========================================================================
    # 
    #===========================================================================
    def mParamToolButton_clicked(self):
        pass
    #===========================================================================
    # 
    #===========================================================================
    def hideEvent(self, event):
        className = type(self).__name__
        QSettings().setValue('/PDS/{0}/Geometry'.format(className), self.geometry())

        super(QgisPDSCoordFromZoneDialog, self).hideEvent(event)
    #===========================================================================
    # 
    #===========================================================================
    def showEvent(self, event):
        super(QgisPDSCoordFromZoneDialog, self).showEvent(event)

        className = type(self).__name__
        rect = QSettings().value('/PDS/{0}/Geometry'.format(className))
        if rect:
            self.setGeometry(rect)
            
            
            