# -*- coding: utf-8 -*-

from PyQt4.QtCore import *


class ReaderBase(QObject):
    def __init__(self):
        super(ReaderBase, self).__init__()


    def setupGui(self, dialog):
        dialog.mValueLineEdit.setVisible(False)
        dialog.mDefaultValueGroupBox.setVisible(False)
        dialog.mLoadAsContourCheckBox.setVisible(False)


    def createLayer(self, layerName, pdsProject, groupSetId, defaultValue):
        pass
