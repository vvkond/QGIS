# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtGui import *
from qgis import core, gui
import os
import ast
from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from tig_projection import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_saveMapsetToPDS_base.ui'))

class QgisSaveMapsetToPDS(QtGui.QDialog, FORM_CLASS):
    def __init__(self, project, iface, layerToSave, parent=None):
        super(QgisSaveMapsetToPDS, self).__init__(parent)

        self.setupUi(self)

        self.currentLayer = layerToSave
        self.iface = iface
        self.project = project
        self.groupFile = 'ControlPoints_group.sql'
        self.setFile = 'ControlPoints_set.sql'
        self.mapSetType = -1
        self.mapSetCpSource = 0
        self.plugin_dir = os.path.dirname(__file__)

        try:
            prjStr = self.currentLayer.customProperty("pds_project")
            if prjStr:
                self.project = ast.literal_eval(prjStr)

            self.proj4String = 'epsg:4326'
            self.db = None

            if not self.initDb():
                return

            self.prop = self.currentLayer.customProperty("qgis_pds_type")
            if self.prop == 'pds_contours':
                self.groupFile = "Contours_group.sql"
                self.setFile = "Contours_set.sql"
                self.mapSetCpSource = 4
                self.mSaveAsComboBox.setCurrentIndex(2)
            if self.prop == 'pds_polygon':
                self.groupFile = "Polygons_group.sql"
                self.setFile = "Polygons_set.sql"
                self.mSaveAsComboBox.setCurrentIndex(3)
            if self.prop == 'pds_faults':
                self.groupFile = "Faults_group.sql"
                self.setFile = "Faults_set.sql"
                self.mSaveAsComboBox.setCurrentIndex(1)
            if self.prop == 'qgis_surface':
                self.groupFile = 'Surface_group.sql'
                self.setFile = 'Surface_set.sql'
                self.mapSetType = 4
                self.mSaveAsComboBox.setEnabled(False)
                self.mSetFieldsCroupBox.setEnabled(False)

            if self.prop != 'qgis_surface':
                self.updateFieldsComboBox()

            name = self.currentLayer.name()
            self.mGroupLineEdit.setText(name)
            names = name.split('/')
            if len(name) > 0:
                self.mGroupLineEdit.setText(names[0])
            if len(name) > 1:
                self.mSetLineEdit.setText(names[1])

        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)

    def on_buttonBox_accepted(self):
        self.saveToDb()

    def initDb(self):
        if self.project is None:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                self.tr(u'No current PDS project'), level=QgsMessageBar.CRITICAL)

            return False

        connection = create_connection(self.project)
        scheme = self.project['project']
        try:
            self.db = connection.get_db(scheme)
            sourceCrs = self.currentLayer.crs()
            if sourceCrs is not None:
                destSrc = QgsCoordinateReferenceSystem('epsg:4326')
                self.xform = QgsCoordinateTransform(sourceCrs, destSrc)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Project projection read error {0}: {1}').format(
                                                    scheme, str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return False
        return True

    def updateFieldsComboBox(self):
        if not self.currentLayer:
            return

        self.mSubsetFields.clear()
        self.mParamNameFields.clear()
        self.mParameterFields.clear()

        self.mSubsetFields.addItem('-')
        self.mParamNameFields.addItem('-')
        self.mParameterFields.addItem('-')
        for f in self.currentLayer.fields():
            self.mSubsetFields.addItem(f.name())
            self.mParamNameFields.addItem(f.name())
            self.mParameterFields.addItem(f.name())

        if self.mSubsetFields.count() > 0:
            self.mSubsetFields.setCurrentIndex(self.mSubsetFields.findText('subset_name'))
            self.mParamNameFields.setCurrentIndex(self.mParamNameFields.findText('param_name'))
            self.mParameterFields.setCurrentIndex(self.mParameterFields.findText('parameter'))

    def getGroupNo(self, mapSetName):
        mapSetNo = -1
        if self.db is None:
            return mapSetNo

        try:
            sqlFile = os.path.join(self.plugin_dir, 'db', self.groupFile)
            if os.path.exists(sqlFile):
                f = open(sqlFile, 'r')
                sql = f.read()
                f.close()

                records = self.db.execute(sql)

                for rec in records:
                    if rec[1] == mapSetName:
                        mapSetNo = rec[0]
                        break
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)

        return mapSetNo

    def getSetNo(self, groupId, mapSetName):
        mapSetNo = -1
        if self.db is None:
            return mapSetNo

        try:
            sqlFile = os.path.join(self.plugin_dir, 'db', self.setFile)
            if os.path.exists(sqlFile):
                f = open(sqlFile, 'r')
                sql = f.read()
                f.close()

                records = self.db.execute(sql, group_id=groupId)
                for rec in records:
                    if rec[1] == mapSetName:
                        mapSetNo = rec[0]
                        break
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)

        return mapSetNo

    def resetMapSetType(self):
        if self.mSaveAsComboBox.currentIndex() == 0:
            self.mapSetType = 1
        elif self.mSaveAsComboBox.currentIndex() == 1:
            self.mapSetType = 2
        elif self.mSaveAsComboBox.currentIndex() == 2:
            self.mapSetType = 1
        else:
            self.mapSetType = 3

    def getMaxSetNumber(self, sql):
        records = self.db.execute(sql)
        num = 0
        if records:
            for rec in records:
                num = num + rec[0]
        return num

    def saveToDb(self):
        groupNameToSave = self.mGroupLineEdit.text()
        setNameToSave = self.mSetLineEdit.text()

        groupNo = self.getGroupNo(groupNameToSave)

        if groupNo >= 0:
            setNo = self.getSetNo(groupNo, groupNameToSave+'/'+setNameToSave)
            print groupNo, setNo
            if setNo >= 0:
                QtGui.QMessageBox.critical(self, self.tr(u'Save to PDS'), self.tr(u'Group/Set names already exists'))
                return
        else:
            print groupNo

        if self.prop == 'qgis_surface':
            print "Saving surface..."
            return

        #Set MAP_SET_TYPE
        self.resetMapSetType()

        print 'saving...'
        maxMapSetNo = self.getMaxSetNumber('select max(tig_map_set_no) from tig_map_set')
        maxMapSubsetNo = self.getMaxSetNumber('select max(tig_map_subset_no) from tig_map_subset')
        maxMapSetParameterNo = self.getMaxSetNumber('select max(tig_map_set_parameter_no) from TIG_MAP_SET_PARAM')
        print maxMapSetNo, maxMapSubsetNo, maxMapSetParameterNo
        