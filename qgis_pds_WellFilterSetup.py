# -*- coding: utf-8 -*-

import os
import numpy
from struct import unpack_from
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from utils import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_wellFilterSetup_base.ui'))

class QgisPDSWellFilterSetupDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, _project, _iface, parent=None):
        """Constructor."""
        super(QgisPDSWellFilterSetupDialog, self).__init__(parent)

        self.project = _project
        self.iface = _iface