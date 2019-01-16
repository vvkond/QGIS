# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtGui import *
from qgis import core, gui
import os
import csv
from datetime import *
import ast
from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from tig_projection import *
from bblInit import MyStruct
import numpy as np
import cx_Oracle
from QgisPDS.utils import to_unicode

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_oracleSql_base.ui'))

class QgisOracleSql(QtGui.QDialog, FORM_CLASS):
    def __init__(self, project, iface, parent=None):
        super(QgisOracleSql, self).__init__(parent)

        self.setupUi(self)

        self.project = project
        self.iface = iface

        if not self.initDb():
            return

        self.setWindowTitle(self.windowTitle() + ' - ' + self.project['project'])

        self.mRefreshToolButton.setIcon(QIcon(u':/plugins/QgisPDS/Refresh.png'))
        # self.mExecuteToolButton.setIcon(QIcon(u':/plugins/QgisPDS/ButtonPlayicon.png'))

    def on_buttonBox_accepted(self):
        if self.mCoordsRadioButton.isChecked():
            self.executeAsLayer()
        else:
            fileName = self.executeAsTable()
            name = os.path.basename(fileName)

            uri = u'file:///{0}?type=csv&geomType=none&subsetIndex=no&watchFile=no'.format(fileName)
            layer = QgsVectorLayer(uri, name, "delimitedtext")
            if layer:
                QgsMapLayerRegistry.instance().addMapLayer(layer)
            else:
                self.iface.messageBar().pushMessage(self.tr("Error"),
                                                    self.tr(u'Text file layer create error'),
                                                    level=QgsMessageBar.CRITICAL)

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
                self.xform = QgsCoordinateTransform(sourceCrs, destSrc)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Project projection read error {0}: {1}').format(
                                                    scheme, str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return False
        return True

    def selectFileClicked(self):
        lastFilePath = QSettings().value('PDS/OracleSQL/lastFilePath', u'.')
        fname = QFileDialog.getOpenFileName(self, u'Выбрать файл',
                                            lastFilePath, u"Файлы SQL (*.sql *.SQL);;Все файлы (*.*)")
        if fname:
            self.loadFile(fname)
            self.refreshFields()

            QSettings().setValue('PDS/OracleSQL/lastFilePath', os.path.dirname(fname))
            self.mFileNameLineEdit.setText(fname)
            if not self.mLayerNameLineEdit.text():
                self.mLayerNameLineEdit.setText(os.path.basename(os.path.splitext(fname)[0]))

    def refreshClicked(self):
        self.refreshFields()

    def executeClicked(self):
        pass

    def loadFile(self, fileName):
        try:
            with open(fileName, 'rb') as f:
                text = f.read().decode('utf-8')
                self.mSqlTextEdit.setPlainText(text)
        except:
            pass

    def executeAsTable(self):
        try:
            sql = self.mSqlTextEdit.toPlainText()
            names = self.db.names(sql)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'SQL error: {0}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return

        fileName = QgsProject.instance().homePath() + '/' + self.mLayerNameLineEdit.text() + '.csv'
        print fileName
        out_pipe = open(fileName, "wb")
        w = csv.writer(out_pipe)
        w.writerow(names)

        try:
            rows = self.db.execute(sql)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'SQL error: {0}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return
        for row in rows:
            rowdata = []
            for col in row:
                rowdata.append(str(col))
            w.writerow(rowdata)

        return fileName

    def executeAsLayer(self):
        layerName = self.mLayerNameLineEdit.text()
        try:
            sql = self.mSqlTextEdit.toPlainText()
            rows = self.db.execute_assoc(sql)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'SQL error: {0}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return

        uri = "Point?crs={}".format(self.proj4String)
        for row in rows:
            for key in row.keys():
                val = row[key]
                if type(val) == float:
                    uri += '&field={}:{}'.format(key, "double")
                elif type(val) == int:
                    uri += '&field={}:{}'.format(key, "int")
                else:
                    uri += '&field={}:{}'.format(key, "string")
            break

        layer = QgsVectorLayer(uri, layerName, "memory")
        if layer is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(
                u'Error create wells layer'), QtGui.QMessageBox.Ok)

            return

        try:
            sql = self.mSqlTextEdit.toPlainText()
            rows = self.db.execute_assoc(sql)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'SQL error: {0}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return

        xFieldName = self.mXcomboBox.currentText();
        yFieldName = self.mYcomboBox.currentText();
        needConvert = self.mLatLongCheckBox.isChecked()

        with edit(layer):
            for row in rows:
                cPoint = QgsFeature(layer.fields())
                x = None
                y = None
                for key in row.keys():
                    val = row[key]
                    cPoint.setAttribute(key, val)
                    if key == xFieldName:
                        x = val
                    if key == yFieldName:
                        y = val
                if x and y:
                    pt = QgsPoint(float(x), float(y))
                    if needConvert and self.xform:
                        pt = self.xform.transform(pt)
                    geom = QgsGeometry.fromPoint(pt)
                    cPoint.setGeometry(geom)

                layer.addFeatures([cPoint])

        layer.setCustomProperty("pds_project", str(self.project))

        QgsMapLayerRegistry.instance().addMapLayer(layer)


    def refreshFields(self):
        self.tableWidget.setRowCount(0)
        self.mYcomboBox.clear()
        self.mXcomboBox.clear()
        try:
            sql = self.mSqlTextEdit.toPlainText()
            names = self.db.names(sql)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'SQL error: {0}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return


        horHeaders = names
        self.tableWidget.setColumnCount(len(horHeaders))
        self.tableWidget.setHorizontalHeaderLabels(horHeaders)

        for name in names:
            self.mYcomboBox.addItem(name)
            self.mXcomboBox.addItem(name)

        try:
            rows = self.db.execute(sql)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'SQL error: {0}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return

        for row in rows:
            numRow = self.tableWidget.rowCount()
            self.tableWidget.insertRow(numRow)
            for n, col in enumerate(row):
                item = col
                if type(col) != 'float' and type(col) != 'int':
                    item = str(col)
                newitem = QTableWidgetItem(item)
                self.tableWidget.setItem(numRow, n, newitem)

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeRowsToContents()