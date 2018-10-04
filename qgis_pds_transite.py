# -*- coding: utf-8 -*-

import os
import numpy
from struct import unpack_from
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from processing.tools.vector import VectorWriter

from .db import Oracle
from .connections import create_connection
from .utils import to_unicode, makeShpFileName
from .tig_projection import *
from .qgis_pds_CoordFromZone import QgisPDSCoordFromZoneDialog

class QgisPDSTransitionsDialog(QgisPDSCoordFromZoneDialog):
    def __init__(self, _project, _iface, _editLayer, parent=None):
        """Constructor."""
        super(QgisPDSTransitionsDialog, self).__init__(_project, _iface, _editLayer, parent)

        newTitle = self.tr(u'Transite wells') + ' - ' + self.project['project']
        self.setWindowTitle(newTitle)

        self.mTwoLayers.setVisible(True)

        settings = QSettings()
        self.mTwoLayers.setChecked( settings.value("/PDS/Zonations/TwoLayers", 'True') == 'True')

    @property
    def twoLayers(self):
        return self.mTwoLayers.isChecked()

    def performOperation(self):
        selectedZonations = []
        selectedZones = []
        for si in self.zonationListWidget.selectedItems():
            selectedZonations.append(int(si.data(Qt.UserRole)))

        sel = None
        for zones in self.zoneListWidget.selectedItems():
            sel = zones.data(Qt.UserRole)
            selectedZones.append(sel[0])

        if sel is None:
            return selectedZonations, selectedZones

        fieldIdx = self.editLayer.dataProvider().fieldNameIndex('transite')
        if fieldIdx < 0:
            with edit(self.editLayer):
                self.editLayer.dataProvider().addAttributes([QgsField("transite", QVariant.String)])
                fieldIdx = self.editLayer.dataProvider().fieldNameIndex('transite')

        with edit(self.editLayer):
            self.editLayer.setSubsetString('')

            wellIdIdx = self.editLayer.dataProvider().fieldNameIndex('Well identifier')
            if wellIdIdx < 0:
                wellIdIdx = self.editLayer.dataProvider().fieldNameIndex('well_id')

            fCount = float(self.editLayer.featureCount()) + 1.0
            iter = self.editLayer.dataProvider().getFeatures()
            index = 0
            for feature in iter:
                wellId = feature[wellIdIdx]
                self.editLayer.changeAttributeValue(feature.id(), fieldIdx, None)
                transites = self.getTransiteList(wellId, sel)
                if transites:
                    self.editLayer.changeAttributeValue(feature.id(), fieldIdx, transites)

                self.progress.setValue(index/fCount*100.0)
                index = index + 1

        self.editLayer.updateExtents()
        self.editLayer.setSubsetString('"transite" is not NULL')

        return selectedZonations, selectedZones


    def performOperationTwoLayers(self):
        selectedZonations = []
        selectedZones = []
        for si in self.zonationListWidget.selectedItems():
            selectedZonations.append(int(si.data(Qt.UserRole)))

        sel = None
        for zones in self.zoneListWidget.selectedItems():
            sel = zones.data(Qt.UserRole)
            selectedZones.append(sel[0])

        if sel is None:
            return selectedZonations, selectedZones

        settings = QSettings()
        systemEncoding = settings.value('/UI/encoding', 'System')

        transiteName = u'transite - ' + self.editLayer.name()
        targetName = u'target - ' + self.editLayer.name()
        reg = QgsMapLayerRegistry.instance()
        reg.removeMapLayers(reg.mapLayersByName(transiteName))
        reg.removeMapLayers(reg.mapLayersByName(targetName))

        transiteFileName = makeShpFileName(self.scheme, str(hash(transiteName)), False)
        targetFileName = makeShpFileName(self.scheme, str(hash(targetName)), False)

        provider = self.editLayer.dataProvider()
        transiteFields = self.editLayer.fields()
        transiteFields.append(QgsField("transite", QVariant.String))
        transiteWriter = VectorWriter(transiteFileName, systemEncoding,
                                      transiteFields,
                                      provider.geometryType(), provider.crs())

        fields = self.editLayer.fields()
        targetWriter = VectorWriter(targetFileName, systemEncoding,
                          fields,
                          provider.geometryType(), provider.crs())


        with edit(self.editLayer):
            self.editLayer.setSubsetString('')

            wellIdIdx = self.editLayer.dataProvider().fieldNameIndex('Well identifier')
            if wellIdIdx < 0:
                wellIdIdx = self.editLayer.dataProvider().fieldNameIndex('well_id')

            fCount = float(self.editLayer.featureCount()) + 1.0
            features = self.editLayer.dataProvider().getFeatures()
            index = 0
            for f in features:
                wellId = f[wellIdIdx]

                l = f.geometry()

                transites = self.getTransiteList(wellId, sel)
                if transites:
                    feat = QgsFeature(transiteFields)
                    feat.setGeometry(l)
                    feat.setAttributes(f.attributes())
                    feat.setAttribute('transite', transites)
                    transiteWriter.addFeature(feat)
                else:
                    feat = QgsFeature(f)
                    feat.setGeometry(l)
                    targetWriter.addFeature(feat)

                self.progress.setValue(index/fCount*100.0)
                index = index + 1

        del transiteWriter
        del targetWriter

        pds_type = self.editLayer.customProperty("qgis_pds_type", "")

        targetLayer = QgsVectorLayer(targetFileName, targetName, 'ogr')
        transiteLayer = QgsVectorLayer(transiteFileName, transiteName, 'ogr')

        targetLayer.setCustomProperty("qgis_pds_type", pds_type)
        transiteLayer.setCustomProperty("qgis_pds_type", pds_type)

        QgsMapLayerRegistry.instance().addMapLayer( targetLayer )
        QgsMapLayerRegistry.instance().addMapLayer( transiteLayer )

        return selectedZonations, selectedZones


    def process(self):
        progressMessageBar = self.iface.messageBar()
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        progressMessageBar.pushWidget(self.progress)

        try:
            if self.twoLayers:
                selectedZonations, selectedZones = self.performOperationTwoLayers()
            else:
                selectedZonations, selectedZones = self.performOperation()
    
            settings = QSettings()
            settings.setValue("/PDS/Zonations/SelectedZonations", selectedZonations)
            settings.setValue("/PDS/Zonations/selectedZones", selectedZones)
            settings.setValue("/PDS/Zonations/TwoLayers", 'True' if self.twoLayers else 'False')
        except Exception as e:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), str(e), QtGui.QMessageBox.Ok)

        self.iface.messageBar().clearWidgets()


    def getTransiteList(self, wellId, zoneDef):
        sql = self.get_sql('ZonationTransite.sql')
        records = self.db.execute(sql, well_id=wellId, zonation_id=zoneDef[1], zone_id=zoneDef[0])
        result = []
        if records:
            for input_row in records:
                result.append(input_row[3]);

        return ','.join(result)