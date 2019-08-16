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
from utils import edit_layer, LayersHider
from bblInit import layer_to_labeled, Fields


IS_DEBUG=False
C_TRANSITE='transite'
C_TARGET='target'
#===============================================================================
# 
#===============================================================================
class QgisPDSTransitionsDialog(QgisPDSCoordFromZoneDialog):
    def __init__(self, _project, _iface, _editLayers, parent=None, allow_split_layer=True):
        """Constructor."""
        super(QgisPDSTransitionsDialog, self).__init__(_project, _iface, _editLayers, parent)

        newTitle = self.tr(u'Transite wells') + ' - ' + self.project['project']
        self.setWindowTitle(newTitle)

        self.mTwoLayers.setVisible(True)


        settings = QSettings()
        self.mTwoLayers.setEnabled(allow_split_layer)

        self.clearTargetFieldChkBox=QCheckBox(u'очистить столбец target')
        self.clearTargetFieldChkBox.setChecked(True)
        self.enableFilterChkBox=QCheckBox(u'вкл. фильтр')
        self.enableFilterChkBox.setChecked(False)
        self.horizontalLayout_2.addWidget(self.clearTargetFieldChkBox)
        self.horizontalLayout_2.addWidget(self.enableFilterChkBox)
       
        self.isOnlyPublicDeviChkBox.setVisible(False)
        self.notUseLastZoneChkBox.setVisible(True)
        self.notUseLastZoneNum.setVisible(True)
        self.notUseLastZoneNum.setEnabled(self.notUseLastZoneChkBox.isChecked())
        
        #QObject.connect(self.notUseLastZoneChkBox, SIGNAL("stateChanged(int)"), self.notUseLastZoneChkBoxChecked)
        self.notUseLastZoneChkBox.stateChanged.connect(self.notUseLastZoneChkBoxChecked)
        self.notUseLastZoneNum.valueChanged.connect(self.notUseLastZoneNumChanged)
        self.zonationListWidget.itemSelectionChanged.connect(self.notUseLastZoneNumChanged)

        self.mTwoLayers.setChecked(             settings.value("/PDS/Zonations/TwoLayers", 'True') == 'True')
        self.notUseLastZoneChkBox.setChecked(   settings.value("/PDS/Zonations/notUseLastZone", 'False') == 'True')
        self.notUseLastZoneNum.setValue(int(    settings.value("/PDS/Zonations/notUseLastZoneNum", '0')))
        self.clearTargetFieldChkBox.setChecked( settings.value("/PDS/Zonations/clearTargetField", 'True') == 'True')
        self.enableFilterChkBox.setChecked(     settings.value("/PDS/Zonations/enableFilter", 'True') == 'True')

        
    
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
    def performOperation(self,clear_target=True,clear_transite=True):
        selectedZonations = []
        selectedZones = []
        for si in self.zonationListWidget.selectedItems():
            selectedZonations.append(int(si.data(Qt.UserRole)))

        sel = None
        selTxt=None
        for zones in self.zoneListWidget.selectedItems():
            sel = zones.data(Qt.UserRole)
            selectedZones.append(sel[0])
            selTxt=zones.text()

        if sel is None:
            return selectedZonations, selectedZones

        fieldIdx={}
        for fieldName,fieldType in [
                                     [C_TRANSITE,QVariant.String]
                                    ,[C_TARGET,QVariant.String]
                                    ]:
            fieldIdx[fieldName] = self.editLayer.dataProvider().fieldNameIndex(fieldName)
            if fieldIdx[fieldName] < 0:
                with edit_layer(self.editLayer):
                    self.editLayer.dataProvider().addAttributes([QgsField(fieldName, fieldType)])
                    fieldIdx[fieldName] = self.editLayer.dataProvider().fieldNameIndex(fieldName)
        wellIdIdx = self.editLayer.dataProvider().fieldNameIndex('Well identifier')
        if wellIdIdx < 0:
            wellIdIdx = self.editLayer.dataProvider().fieldNameIndex(Fields.WellId.name)
        
        subsetStr=self.editLayer.subsetString()
        
        with edit_layer(self.editLayer):
            self.editLayer.setSubsetString('')
            fCount = float(self.editLayer.featureCount()) + 1.0
            index = 0
            for index,feature in enumerate(self.editLayer.dataProvider().getFeatures()):
                wellId = feature[wellIdIdx]
                if clear_transite: self.editLayer.changeAttributeValue(feature.id(), fieldIdx[C_TRANSITE], None)
                if clear_target  : self.editLayer.changeAttributeValue(feature.id(), fieldIdx[C_TARGET],   None)
                transites = self.getTransiteList(wellId, sel)
                if transites:
                    self.editLayer.changeAttributeValue(feature.id(), fieldIdx[C_TRANSITE], transites)
                elif self.isZoneTarget(wellId, sel):
                    self.editLayer.changeAttributeValue(feature.id(), fieldIdx[C_TARGET], selTxt)

                self.progress.setValue(index/fCount*100.0)

        self.editLayer.updateExtents()
        if self.enableFilterChkBox.isChecked():
            self.editLayer.setSubsetString('"{C_TRANSITE}" is not NULL OR "{C_TARGET}" is not NULL'.format(C_TRANSITE=C_TRANSITE,C_TARGET=C_TARGET))
        else:
            self.editLayer.setSubsetString(subsetStr)

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
        #hide layers
        layer_hider=LayersHider(self.iface)
        layer_hider.hide()
        #
        for editLayer in self.selectedLayers:
            progressMessageBar = self.iface.messageBar()
            self.progress = QProgressBar()
            self.progress.setMaximum(100)
            progressMessageBar.pushWidget(self.progress)
            self.editLayer=editLayer
            try:
                if self.twoLayers:
                    selectedZonations, selectedZones = self.performOperationTwoLayers()
                else:
                    selectedZonations, selectedZones = self.performOperation(clear_target=self.clearTargetFieldChkBox.isChecked())
        
                settings = QSettings()
                settings.setValue("/PDS/Zonations/SelectedZonations", selectedZonations)
                settings.setValue("/PDS/Zonations/selectedZones",     selectedZones)
                settings.setValue("/PDS/Zonations/TwoLayers",         'True' if self.twoLayers else 'False')
                settings.setValue("/PDS/Zonations/notUseLastZone",    'True' if self.notUseLastZoneChkBox.isChecked() else 'False')
                settings.setValue("/PDS/Zonations/notUseLastZoneNum", str(self.notUseLastZoneNum.value()))
                settings.setValue("/PDS/Zonations/clearTargetField",  'True' if self.clearTargetFieldChkBox.isChecked() else 'False')
                settings.setValue("/PDS/Zonations/enableFilter",      'True' if self.enableFilterChkBox.isChecked() else 'False')
                
            except Exception as e:
                QtGui.QMessageBox.critical(None, self.tr(u'Error'), str(e), QtGui.QMessageBox.Ok)
    
            self.iface.messageBar().clearWidgets()
        #show layers
        layer_hider.show()

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
                                  , skeep_last_n_zone=self.notUseLastZoneNum.value() if self.notUseLastZoneChkBox.isChecked() else None
                                  )
        result = []
        isTarget=False
        if records:
            for input_row in records:
                if input_row[4]==zoneDef[0]:
                    isTarget=True
                    break
        return isTarget
    
    
    
    