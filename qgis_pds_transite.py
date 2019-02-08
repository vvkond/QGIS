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
from utils import edit_layer
from bblInit import layer_to_labeled


IS_DEBUG=False

#===============================================================================
# 
#===============================================================================
class QgisPDSTransitionsDialog(QgisPDSCoordFromZoneDialog):
    def __init__(self, _project, _iface, _editLayer, parent=None, allow_split_layer=True):
        """Constructor."""
        super(QgisPDSTransitionsDialog, self).__init__(_project, _iface, _editLayer, parent)

        newTitle = self.tr(u'Transite wells') + ' - ' + self.project['project']
        self.setWindowTitle(newTitle)

        self.mTwoLayers.setVisible(True)

        settings = QSettings()
        self.mTwoLayers.setEnabled(allow_split_layer)
        self.mTwoLayers.setChecked(settings.value("/PDS/Zonations/TwoLayers", 'True') == 'True')
        
        self.isOnlyPublicDeviChkBox.setVisible(False)
        self.notUseLastZoneChkBox.setVisible(True)
        self.notUseLastZoneNum.setVisible(True)
        self.notUseLastZoneNum.setEnabled(self.notUseLastZoneChkBox.isChecked())
        
        #QObject.connect(self.notUseLastZoneChkBox, SIGNAL("stateChanged(int)"), self.notUseLastZoneChkBoxChecked)
        self.notUseLastZoneChkBox.stateChanged.connect(self.notUseLastZoneChkBoxChecked)
        self.notUseLastZoneNum.valueChanged.connect(self.notUseLastZoneNumChanged)
        self.zonationListWidget.itemSelectionChanged.connect(self.notUseLastZoneNumChanged)
    
    def notUseLastZoneChkBoxChecked(self,state):
        if state==Qt.Unchecked:
            self.notUseLastZoneNum.setEnabled(False)
            for pos in range(0,self.zoneListWidget.count()):
                self.zoneListWidget.setItemHidden(self.zoneListWidget.item(pos), False)
        elif state==Qt.Checked:
            self.notUseLastZoneNum.setEnabled(True)
            self.notUseLastZoneNumChanged()
    def notUseLastZoneNumChanged(self):
        if self.notUseLastZoneChkBox.isChecked():
            first_pos=self.zoneListWidget.count()-self.notUseLastZoneNum.value()
            for pos in range(first_pos,self.zoneListWidget.count()):
                self.zoneListWidget.setItemHidden(self.zoneListWidget.item(pos), True)
            for pos in range(0,first_pos):
                self.zoneListWidget.setItemHidden(self.zoneListWidget.item(pos), False) 
        pass
    #===========================================================================
    # 
    #===========================================================================
    @property
    def twoLayers(self):
        return self.mTwoLayers.isChecked()
    #===========================================================================
    # 
    #===========================================================================
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
            with edit_layer(self.editLayer):
                self.editLayer.dataProvider().addAttributes([QgsField("transite", QVariant.String)])
                fieldIdx = self.editLayer.dataProvider().fieldNameIndex('transite')

        with edit_layer(self.editLayer):
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

    #===========================================================================
    # 
    #===========================================================================
    def performOperationTwoLayers(self):
        selectedZonations = []
        selectedZones = []
        selectedZonesNames = []
        for si in self.zonationListWidget.selectedItems():
            selectedZonations.append(int(si.data(Qt.UserRole)))

        sel = None
        for zones in self.zoneListWidget.selectedItems():
            sel = zones.data(Qt.UserRole)
            selectedZones.append(sel[0])
            selectedZonesNames.append(zones.text())

        if sel is None:
            return selectedZonations, selectedZones

        settings = QSettings()
        systemEncoding = settings.value('/UI/encoding', 'System')

        transiteName = u'transite_' +"_".join(map(str,selectedZonesNames))+"_" +self.editLayer.name()
        targetName = u'target_'+"_".join(map(str,selectedZonesNames))+"_" + self.editLayer.name()
        
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


        with edit_layer(self.editLayer):
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
                elif self.isZoneTarget(wellId, sel):
                    feat = QgsFeature(f)
                    feat.setGeometry(l)
                    targetWriter.addFeature(feat)

                self.progress.setValue(index/fCount*100.0)
                index = index + 1

        del transiteWriter
        del targetWriter

        pds_type = self.editLayer.customProperty("qgis_pds_type", "")
        pds_prj = self.editLayer.customProperty("pds_project", "")

        targetLayer = QgsVectorLayer(targetFileName, targetName, 'ogr')
        transiteLayer = QgsVectorLayer(transiteFileName, transiteName, 'ogr')

        for layer in [targetLayer, transiteLayer]:
            palyr = QgsPalLayerSettings()
            palyr.readFromLayer(layer)
            palyr=layer_to_labeled(palyr)  #---enable EasyLabel
            palyr.writeToLayer(layer)
            layer.setCustomProperty("qgis_pds_type", pds_type)
            layer.setCustomProperty("pds_project", pds_prj)
            
            QgsMapLayerRegistry.instance().addMapLayer( layer )

        return selectedZonations, selectedZones

    #===========================================================================
    # 
    #===========================================================================
    def process(self):

        global IS_DEBUG
        IS_DEBUG=     self.isDebugChkBox.isChecked()
        
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

    #===========================================================================
    # 
    #===========================================================================
    def getTransiteList(self, wellId, zoneDef):
        sql = self.get_sql('ZonationTransite.sql')
        records = self.db.execute(sql
                                  , well_id= wellId
                                  , zonation_id= zoneDef[1]
                                  , zone_id= zoneDef[0]
                                  , interval_order= None
                                  , skeep_last_n_zone=self.notUseLastZoneNum.value() if self.notUseLastZoneChkBox.isChecked() else None
                                  )
        
        result = []
        if records:
            for input_row in records:
                result.append(input_row[3]);
        return ','.join(result)
    
    #===========================================================================
    # 
    #===========================================================================
    def isZoneTarget(self, wellId, zoneDef):
        sql = self.get_sql('ZonationTarget.sql')
        records = self.db.execute(sql
                                  , well_id= wellId
                                  , zonation_id= zoneDef[1]
                                  )
        result = []
        isTarget=False
        if records:
            for input_row in records:
                if input_row[4]==zoneDef[0]:
                    isTarget=True
                    break
        return isTarget
    
    
    
    