# -*- coding: utf-8 -*-

import os
import numpy
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from QgisPDS.tig_projection import *
from ControlPointReader import ControlPointReader


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_cpoints_base.ui'))

class QgisPDSCPointsDialog(QtGui.QDialog, FORM_CLASS):

    def __init__(self, project, iface, reader, parent=None):
        """Constructor."""
        super(QgisPDSCPointsDialog, self).__init__(parent)

        self.setupUi(self)

        self.iface = iface
        self.project = project

        try:
            connection = create_connection(self.project)
            scheme = self.project['project']

            self.db = connection.get_db(scheme)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                self.tr(u'Project {0}: {1}').format(scheme, str(e)), level=QgsMessageBar.CRITICAL)
            return

        self.dbReader = reader
        self.dbReader.setDb( self.db )
        self.dbReader.setupGui(self)

        self.restoreSettings();


        self.setWindowTitle(self.dbReader.windowTitle)

        groups = self.dbReader.getGroups()

        for grId, grName in groups:
            item = QListWidgetItem(to_unicode(grName))
            item.setData(Qt.UserRole, grId)
            self.groupsListWidget.addItem(item)

        return

    def saveSettings(self):
        QSettings().setValue("/PDS/CPoints/lastValue", self.mValueLineEdit.value())
        if self.mDefaultValueGroupBox.isChecked():
            QSettings().setValue("/PDS/CPoints/userDefaultValue", "True")
        else:
            QSettings().setValue("/PDS/CPoints/userDefaultValue", "False")


    def restoreSettings(self):
        self.mValueLineEdit.setValue(float(QSettings().value("/PDS/CPoints/lastValue", "0.0")))
        self.mDefaultValueGroupBox.setChecked(QSettings().value("/PDS/CPoints/userDefaultValue", "False") == 'True')


    def on_buttonBox_accepted(self):

        for si in self.setsListWidget.selectedItems():
#            try:
            self.saveSettings();

            defValue = -9999
            if self.mDefaultValueGroupBox.isChecked():
                defValue = self.mValueLineEdit.value()

            self.layer = self.dbReader.createLayer(si.text(), self.project, si.data(Qt.UserRole), defValue)

#            except Exception as e:
#                self.iface.messageBar().pushMessage(self.tr("Error"),
#                    self.tr(u'Read control points from project {0}: {1}').format(scheme, str(e)), level=QgsMessageBar.CRITICAL)
            if self.layer is not None:
                QgsMapLayerRegistry.instance().addMapLayer(self.layer)

        return


    def _fillSets(self, groupId):
        sets = self.dbReader.getSets(groupId)

        for setNo, setName in sets:
            item = QListWidgetItem(to_unicode(setName))
            item.setData(Qt.UserRole, [groupId, setNo])
            self.setsListWidget.addItem(item)

        return


    def on_groupsListWidget_itemSelectionChanged(self):
        self.setsListWidget.clear()
        for si in self.groupsListWidget.selectedItems():
            self._fillSets(si.data(Qt.UserRole))
