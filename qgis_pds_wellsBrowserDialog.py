# -*- coding: utf-8 -*-

import os
import ast
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.connections import create_connection
from utils import *
from QgisPDS.tig_projection import *
from qgis_pds_wellsBrowserForm import QgisPDSWellsBrowserForm

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'wellsBrowserDialog_base.ui'))

class QgisPDSWellsBrowserDialog(QtGui.QDialog, FORM_CLASS):
    """Constructor."""
    def __init__(self, _iface, _project, parent=None, selectedIds=None):
        super(QgisPDSWellsBrowserDialog, self).__init__(parent)
        self.setupUi(self)

        self.plugin_dir = os.path.dirname(__file__)
        self.project = _project
        self.iface = _iface
        self.initDb()

        self.wellsBrowser = QgisPDSWellsBrowserForm(_iface, self.db, self.getAllWells, self.project, parent=self, selectedIds=selectedIds)
        self.verticalLayout.insertWidget(0, self.wellsBrowser)

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
                sourceCrs = QgsCoordinateReferenceSystem(QgisProjectionConfig.get_default_latlon_prj_epsg())
                #self.xform = QgsCoordinateTransform(sourceCrs, destSrc)
                self.xform=get_qgis_crs_transform(sourceCrs,destSrc,self.tig_projections.fix_id)
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

    def getWellIds(self):
        return self.wellsBrowser.getSelectedWells()

    def getAllWells(self):
        wellList = []
        try:
            records = self.db.execute(self.get_sql('Wells.sql'))
            if records:
                for rec in records:
                    well = []
                    well.append(int(rec[1]))  # id (not shown)
                    well.append(rec[0])  # wellName
                    well.append(rec[21])  # Full name
                    well.append(rec[3])  # Operator
                    well.append(rec[2])  # API number
                    well.append(rec[11])  # Location
                    well.append(float(rec[19]))  # Latitude
                    well.append(float(rec[20]))  # Longitude
                    well.append(rec[22])  # Slot number
                    well.append(rec[16])  # Owner
                    # dt = QDateTime.fromString(rec[17], 'dd-MM-yyyy HH:mm:ss')  # Date
                    well.append(QDateTime.fromTime_t(0).addSecs(int(rec[17])))
                    wellList.append(well)

            return wellList
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)

        return wellList

    def hideEvent(self, event):
        className = type(self).__name__
        QSettings().setValue('/PDS/{0}/Geometry'.format(className), self.geometry())

        super(QgisPDSWellsBrowserDialog, self).hideEvent(event)

    def showEvent(self, event):
        super(QgisPDSWellsBrowserDialog, self).showEvent(event)

        className = type(self).__name__
        rect = QSettings().value('/PDS/{0}/Geometry'.format(className))
        if rect:
            self.setGeometry(rect)