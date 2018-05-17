# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from utils import *
from qgis.core import *
# from processing.tools.vector import VectorWriter
import time
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

    def memoryToShp(self, layer, scheme, layerName):
        return memoryToShp(layer, scheme, layerName)
        # settings = QSettings()
        # systemEncoding = settings.value('/UI/encoding', 'System')
        #
        # ln = layerName.replace('/', '-').replace('\\', '-')
        # layerFile = '/{0}_{1}_{2}.shp'.format(scheme, ln, time.strftime('%d_%m_%Y_%H_%M_%S', time.localtime()))
        #
        # (prjPath, prjExt) = os.path.splitext(QgsProject.instance().fileName())
        # if not os.path.exists(prjPath):
        #     os.mkdir(prjPath)
        #
        # layerFileName = prjPath + layerFile
        #
        # provider = layer.dataProvider()
        # fields = provider.fields()
        # writer = VectorWriter(layerFileName, systemEncoding,
        #                       fields,
        #                       provider.geometryType(), provider.crs())
        # features = layer.getFeatures()
        # for f in features:
        #     try:
        #         l = f.geometry()
        #         feat = QgsFeature(f)
        #         feat.setGeometry(l)
        #         writer.addFeature(feat)
        #     except:
        #         pass
        #
        # del writer
        #
        # layerName = createLayerName(layerName)
        #
        # return QgsVectorLayer(layerFileName, layerName, 'ogr')

