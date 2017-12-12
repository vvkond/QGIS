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
        self.mExecuteToolButton.setIcon(QIcon(u':/plugins/QgisPDS/ButtonPlayicon.png'))

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
        pass

    def executeClicked(self):
        pass

    def loadFile(self, fileName):
        try:
            with open(fileName, 'rb') as f:
                text = f.read().decode('utf-8')
                self.mSqlTextEdit.setPlainText(text)
        except:
            pass

    def refreshFields(self):
        sql = self.mSqlTextEdit.toPlainText()
        rows = self.db.execute_assoc(sql)
        for row in rows:
            print row.keys()
            break