# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
import os


class ReaderBase(QObject):
    def __init__(self):
        super(ReaderBase, self).__init__()

        self.db = None
        self.layer = None
        self.groupFile = 'ControlPoints_group.sql'
        self.setFile = 'ControlPoints_set.sql'


    def setupGui(self, dialog):
        dialog.mValueLineEdit.setVisible(False)
        dialog.mDefaultValueGroupBox.setVisible(False)
        dialog.mLoadAsContourCheckBox.setVisible(False)


    def createLayer(self, layerName, pdsProject, groupSetId, defaultValue):
        pass

    def setDb(self, _db):
        self.db = _db

    def getGroups(self):
        groups = []
        if self.db is None:
            return groups

        sqlFile = os.path.join(self.plugin_dir, 'db', self.groupFile)
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read()
            f.close()

            records = self.db.execute(sql)

            for rec in records:
                groups.append( rec )

        return groups

    def getSets(self, groupId):
        sets = []
        if self.db is None:
            return sets

        sqlFile = os.path.join(self.plugin_dir, 'db', self.setFile)
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read()
            f.close()

            records = self.db.execute(sql, group_id=groupId)
            for rec in records:
                sets.append( rec )

        return sets
