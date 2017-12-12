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

        self.mRefreshToolButton.setIcon(QIcon(u':/plugins/QgisPDS/Refresh.png'))
        self.mSelectFileToolButton.setIcon(QIcon(u':/plugins/QgisPDS/openfileicon.png'))
        self.mExecuteToolButton.setIcon(QIcon(u':/plugins/QgisPDS/ButtonPlayicon.png'))

    def selectFileClicked(self):
        fname = QFileDialog.getOpenFileName(self, u'Выбрать файл',
                                            u'.', u"Файлы SQL (*.sql *.SQL);;Все файлы (*.*)")

    def refreshClicked(self):
        pass

    def executeClicked(self):
        pass