# -*- coding: utf-8 -*-

import os
import numpy
from struct import unpack_from
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from QgisPDS.tig_projection import *
from QgisPDS.qgis_pds_CoordFromZone import QgisPDSCoordFromZoneDialog

class QgisPDSTransitionsDialog(QgisPDSCoordFromZoneDialog):
    def __init__(self, _project, _iface, _editLayer, parent=None):
        """Constructor."""
        super(QgisPDSTransitionsDialog, self).__init__(_project, _iface, _editLayer, parent)

        self.setWindowTitle(self.tr(u'Transite wells'))

    def process(self):
        selectedZonations = []
        selectedZones = []
        for si in self.zonationListWidget.selectedItems():
            selectedZonations.append(int(si.data(Qt.UserRole)))

        sel = None
        for zones in self.zoneListWidget.selectedItems():
            sel = zones.data(Qt.UserRole)
            selectedZones.append(sel[0])

        if sel is None:
            return

        with edit(self.editLayer):
            fieldIdx = self.editLayer.dataProvider().fieldNameIndex('transite')
            if fieldIdx < 0:
                self.editLayer.dataProvider().addAttributes([QgsField("transite", QVariant.String)])
                fieldIdx = self.editLayer.dataProvider().fieldNameIndex('transite')

            self.editLayer.setSubsetString('')

            wellIdIdx = self.editLayer.dataProvider().fieldNameIndex('Well identifier')
            if wellIdIdx < 0:
                wellIdIdx = self.editLayer.dataProvider().fieldNameIndex('well_id')

            iter = self.editLayer.dataProvider().getFeatures()
            for feature in iter:
                wellId = feature[wellIdIdx]
                self.editLayer.changeAttributeValue(feature.id(), fieldIdx, None)
                transites = self.getTransiteList(wellId, sel)
                if transites:
                    self.editLayer.changeAttributeValue(feature.id(), fieldIdx, transites)

            self.editLayer.setSubsetString('"transite" is not NULL')

        try:
            settings = QSettings()
            settings.setValue("/PDS/Zonations/SelectedZonations", selectedZonations)
            settings.setValue("/PDS/Zonations/selectedZones", selectedZones)
        except:
            return


    def getTransiteList(self, wellId, zoneDef):
        sql = self.get_sql('ZonationTransite.sql')
        records = self.db.execute(sql, well_id=wellId, zonation_id=zoneDef[1], zone_id=zoneDef[0])
        result = []
        if records:
            for input_row in records:
                result.append(input_row[3]);

        return ','.join(result)