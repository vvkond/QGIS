# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from qgis.core import *
from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtGui import *
from qgis import core, gui
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_refreshSetup_base.ui'))

class QgisPDSRefreshSetup(QtGui.QDialog, FORM_CLASS):
    def __init__(self, _project, parent=None):
        super(QgisPDSRefreshSetup, self).__init__(parent)

        self.setupUi(self)

        if _project:
            scheme = _project['project']
            if scheme:
                self.setWindowTitle(self.windowTitle() + ' - ' + scheme)

        self.restoreSettings()

    def on_buttonBox_accepted(self):
        self.saveSettings()

    def saveSettings(self):
        sett = QSettings()

        if self.isRefreshKoords:
            sett.setValue('PDS/refreshSetup/mKoordsCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mKoordsCheckBox', 'False')
        if self.isRefreshData:
            sett.setValue('PDS/refreshSetup/mDataCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mDataCheckBox', 'False')
        if self.isSelectedOnly:
            sett.setValue('PDS/refreshSetup/mSelectedCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mSelectedCheckBox', 'False')

    def restoreSettings(self):
        sett = QSettings()
        self.mKoordsCheckBox.setChecked(sett.value('PDS/refreshSetup/mKoordsCheckBox', 'True') == 'True')
        self.mDataCheckBox.setChecked(sett.value('PDS/refreshSetup/mDataCheckBox', 'True') == 'True')
        self.mSelectedCheckBox.setChecked(sett.value('PDS/refreshSetup/mSelectedCheckBox', 'False') == 'True')

    @property
    def isRefreshKoords(self):
        return self.mKoordsCheckBox.isChecked()

    @property
    def isRefreshData(self):
        return self.mDataCheckBox.isChecked()

    @property
    def isSelectedOnly(self):
        return self.mSelectedCheckBox.isChecked()