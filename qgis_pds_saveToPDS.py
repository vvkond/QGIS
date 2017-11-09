# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from qgis.core import *
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
    os.path.dirname(__file__), 'qgis_pds_saveToPDS_base.ui'))

class QgisSaveWellsToPDS(QtGui.QDialog, FORM_CLASS):
    def __init__(self, project, iface, layerToSave, parent=None):
        super(QgisSaveWellsToPDS, self).__init__(parent)

        self.setupUi(self)

        self.currentLayer = layerToSave
        self.iface = iface
        self.project = project

        try:
            prjStr = self.currentLayer.customProperty("pds_project")
            if prjStr:
                self.project = ast.literal_eval(prjStr)

            self.proj4String = 'epsg:4326'
            self.db = None

            if not self.initDb():
                return

            self.updateFieldsComboBox()
        except:
            pass

    def on_buttonBox_accepted(self):
        self.writeWells()

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

        self.mFieldsComboBox.clear()
        for f in self.currentLayer.fields():
            self.mFieldsComboBox.addItem(f.name())

    def writeWells(self):
        fn = self.mFieldsComboBox.currentText()
        if not self.currentLayer or not fn:
            return

        provider = self.currentLayer.dataProvider()

        features = provider.getFeatures()
        infoStr = ''
        countToSave = 0
        block = False
        lastWell = ''
        for f in features:
            wellId = f.attribute(fn)
            count = self.getDbWellCount(wellId)
            if count == 0:
                countToSave = countToSave + 1
                lastWell = str(wellId)
                if not block:
                    l = len(infoStr)
                    if l:
                        infoStr = infoStr + ', '
                    infoStr = infoStr + str(wellId)
                    if l > 100:
                        infoStr = infoStr + '...'
                        block = True
        if block:
            infoStr = infoStr + str(lastWell)

        if len(infoStr):
            if QtGui.QMessageBox.question(self, self.tr(u'Save to PDS'), self.tr(u'Save {0} well to PDS?\n({1})')
                                       .format(countToSave, infoStr),
                                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
                return
        else:
            return

        features = provider.getFeatures()
        for f in features:
            wellId = f.attribute(fn)
            geom = f.geometry()
            pt = None
            t = geom.wkbType()
            if t == QGis.WKBPoint:
                pt = geom.asPoint()
            elif t == QGis.WKBMultiPoint:
                mpt = geom.asMultiPoint()
                if mpt and len(mpt):
                    pt = mpt[0]

            count = self.getDbWellCount(wellId)
            if count == 0 and pt:
                self.insertWell(wellId, self.xform.transform(pt))


    def getDbWellCount(self, wellId):
        sql = ("SELECT count(*) FROM tig_well_history "
               "WHERE rtrim(tig_latest_well_name) = '" + str(wellId) + "' ")

        num = 0

        res = self.db.execute_scalar(sql)
        if res:
            for r in res:
                num = num + r
        return num

    def insertWell(self, wellId, coord):
        try:
            sql = ("INSERT into tig_well_history (db_sldnid, tig_latest_well_name, tig_longitude, tig_latitude, "
                   "TIG_INTERPRETER_SLDNID, TIG_GLOBAL_DATA_FLAG, TIG_LATEST_OPERATOR_NAME ) "
                   " VALUES(TIG_WELL_HISTORY_SEQ.nextval, "
                   "'{0}', {1}, {2}, 1001, 1, 'QGis' )".format(wellId, coord.x(), coord.y()))
            self.db.execute(sql)
            self.db.commit()
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Well insert error {0}: {1}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
