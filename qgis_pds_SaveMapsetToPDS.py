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
from osgeo import gdal

class FeatureRecord(MyStruct):
    points = []
    parameter = None

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_saveMapsetToPDS_base.ui'))

class QgisSaveMapsetToPDS(QtGui.QDialog, FORM_CLASS):
    def __init__(self, project, iface, layerToSave, parent=None):
        super(QgisSaveMapsetToPDS, self).__init__(parent)

        self.setupUi(self)

        self.currentLayer = layerToSave
        self.iface = iface
        self.project = project
        self.groupFile = 'ControlPoints_group.sql'
        self.setFile = 'ControlPoints_set.sql'
        self.mapSetType = 0
        self.mapSetCpSource = 0
        self.plugin_dir = os.path.dirname(__file__)
        self.xform = None

        prjStr = self.currentLayer.customProperty("pds_project")
        if prjStr:
            self.project = ast.literal_eval(prjStr)

        self.proj4String = 'epsg:4326'
        self.db = None

        if not self.initDb():
            return

        self.prop = self.currentLayer.customProperty("qgis_pds_type")
        if self.prop == 'pds_contours':
            self.groupFile = "Contours_group.sql"
            self.setFile = "Contours_set.sql"
            self.mapSetCpSource = 4
            self.mSaveAsComboBox.setCurrentIndex(2)
        if self.prop == 'pds_polygon':
            self.groupFile = "Polygons_group.sql"
            self.setFile = "Polygons_set.sql"
            self.mSaveAsComboBox.setCurrentIndex(3)
        if self.prop == 'pds_faults':
            self.groupFile = "Faults_group.sql"
            self.setFile = "Faults_set.sql"
            self.mSaveAsComboBox.setCurrentIndex(1)
        if self.prop == 'qgis_surface':
            self.groupFile = 'Surface_group.sql'
            self.setFile = 'Surface_set.sql'
            self.mapSetType = 4

        self.updateInterpreters()
        if self.currentLayer.type() == QgsMapLayer.VectorLayer:
            self.updateFieldsComboBox()
        else:
            self.mSaveAsComboBox.setEnabled(False)
            self.mSetFieldsCroupBox.setEnabled(False)
            self.mapSetType = 3
            self.groupFile = "Surface_group.sql"
            self.setFile = "Surface_set.sql"

        name = self.currentLayer.name()
        self.mGroupLineEdit.setText(name)
        names = name.split('/')
        if len(names) > 0:
            self.mGroupLineEdit.setText(names[0])
        if len(names) > 1:
            self.mSetLineEdit.setText(names[1])


    def on_buttonBox_accepted(self):
        # try:
        self.saveToDb()
        # except Exception as e:
        #     self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)

    def saveAsActivated(self):
        self.resetMapSetType()

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
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj and sourceCrs:
                destSrc = QgsCoordinateReferenceSystem()
                destSrc.createFromProj4(proj.qgis_string)
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

        self.mSubsetFields.clear()
        self.mParameterFields.clear()
        self.mKeyFields.clear()

        self.mSubsetFields.addItem('-')
        self.mParameterFields.addItem('-')
        for f in self.currentLayer.fields():
            self.mSubsetFields.addItem(f.name())
            self.mParameterFields.addItem(f.name())
            self.mKeyFields.addItem(f.name())

        try:
            if self.mSubsetFields.count() > 0:
                self.mSubsetFields.setCurrentIndex(self.mSubsetFields.findText('subset_name'))
                self.mParameterFields.setCurrentIndex(self.mParameterFields.findText('parameter'))
                self.mKeyFields.setCurrentIndex(self.mKeyFields.findText('subset_no'))
        except:
            pass

    def updateInterpreters(self):
        self.mInterpreter.clear()
        sql = 'select tig_user_id, tig_login_name from  tig_interpreter'
        users = self.db.execute(sql)
        if users:
            for user in users:
                self.mInterpreter.addItem(to_unicode(user[1]), user[0])
                if user[1] == 'tig':
                    self.mInterpreter.setCurrentIndex(self.mInterpreter.count()-1)

    def getGroupNo(self, mapSetName):
        mapSetNo = -1
        if self.db is None:
            return mapSetNo

        try:
            sqlFile = os.path.join(self.plugin_dir, 'db', self.groupFile)
            if os.path.exists(sqlFile):
                f = open(sqlFile, 'r')
                sql = f.read()
                f.close()

                records = self.db.execute(sql)

                for rec in records:
                    if rec[1] == mapSetName:
                        mapSetNo = rec[0]
                        break
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)

        return mapSetNo

    def getSetNo(self, groupId, mapSetName):
        mapSetNo = -1
        if self.db is None:
            return mapSetNo

        try:
            sqlFile = os.path.join(self.plugin_dir, 'db', self.setFile)
            if os.path.exists(sqlFile):
                f = open(sqlFile, 'r')
                sql = f.read()
                f.close()

                records = self.db.execute(sql, group_id=groupId)
                for rec in records:
                    if rec[1] == mapSetName:
                        mapSetNo = rec[0]
                        break
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)

        return mapSetNo

    def resetMapSetType(self):
        self.mapSetCpSource = 0
        self.mKeyFields.setEnabled(False)
        self.mKetFieldsLabel.setEnabled(False)
        if self.mSaveAsComboBox.currentIndex() == 0:
            self.mapSetType = 1
            self.groupFile = 'ControlPoints_group.sql'
            self.setFile = 'ControlPoints_set.sql'
            self.mKeyFields.setEnabled(True)
            self.mKetFieldsLabel.setEnabled(True)
        elif self.mSaveAsComboBox.currentIndex() == 1:
            self.mapSetType = 2
            self.groupFile = "Faults_group.sql"
            self.setFile = "Faults_set.sql"
        elif self.mSaveAsComboBox.currentIndex() == 2:
            self.mapSetType = 1
            self.groupFile = "Contours_group.sql"
            self.setFile = "Contours_set.sql"
            self.mapSetCpSource = 4
        else:
            self.mapSetType = 3
            self.groupFile = "Polygons_group.sql"
            self.setFile = "Polygons_set.sql"

        if self.currentLayer.type() == QgsMapLayer.RasterLayer:
            self.groupFile = 'Surface_group.sql'
            self.setFile = 'Surface_set.sql'
            self.mapSetType = 4


    def getMaxSetNumber(self, sql):
        records = self.db.execute(sql)
        num = 0
        if records:
            for rec in records:
                num = num + rec[0]
        return num

    def executeInsert(self, sql):
        try:
            self.db.execute(sql)
            self.db.commit()
            return True
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL, duration=30)
            return False

    def saveToDb(self):
        groupNameToSave = self.mGroupLineEdit.text()
        setNameToSave = self.mSetLineEdit.text()

        self.interpreter = int(self.mInterpreter.itemData(self.mInterpreter.currentIndex()))

        if len(groupNameToSave) < 2 or len(setNameToSave) < 2:
            QtGui.QMessageBox.critical(self, self.tr(u'Save to PDS'), self.tr(u'Group or Set name is empty'))
            return

        self.groupNo = self.getGroupNo(groupNameToSave)

        # Set MAP_SET_TYPE
        self.resetMapSetType()

        if self.groupNo >= 0:
            setNo = self.getSetNo(self.groupNo, groupNameToSave+'/'+setNameToSave)
            if setNo >= 0:
                QtGui.QMessageBox.critical(self, self.tr(u'Save to PDS'), self.tr(u'Group/Set names already exists'))
                return

        #Get _NO numbers
        self.maxMapSetNo = self.getMaxSetNumber('select max(tig_map_set_no) from tig_map_set')
        self.maxMapSubsetNo = self.getMaxSetNumber('select max(tig_map_subset_no) from tig_map_subset')
        self.maxMapSetParameterNo = self.getMaxSetNumber('select max(tig_map_set_parameter_no) from TIG_MAP_SET_PARAM')

        if self.currentLayer.type() == QgsMapLayer.RasterLayer:
            self.createGroupSet(groupNameToSave, setNameToSave)
            self.writeSurface()
            return


        provider = self.currentLayer.dataProvider()
        self.subsetFieldName = self.mSubsetFields.currentText()
        self.parameterFieldName = self.mParameterFields.currentText()
        self.keyFieldName = self.mKeyFields.currentText()
        self.subsetFieldIndex = provider.fieldNameIndex(self.subsetFieldName)
        self.parameterFieldIndex = provider.fieldNameIndex(self.parameterFieldName)
        self.keyFieldIndex = provider.fieldNameIndex(self.keyFieldName)

        if self.mapSetType == 0 and self.keyFieldIndex < 0:
            if QtGui.QMessageBox.question(self, self.tr(u'Save to PDS'), self.tr(u'Key field name is not found. Proceed?'),
                                       QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
                return

        if self.subsetFieldIndex < 0:
            if QtGui.QMessageBox.question(self, self.tr(u'Save to PDS'), self.tr(u'Subset field name is not found. Proceed?'),
                                       QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
                return

        if self.parameterFieldIndex < 0:
            if QtGui.QMessageBox.question(self, self.tr(u'Save to PDS'), self.tr(u'Parameter field name is not found. Proceed?'),
                                       QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
                return

        #Create Group/Set
        self.createGroupSet(groupNameToSave, setNameToSave)

        isPointsGeom = True
        features = self.currentLayer.getFeatures()
        for f in features:
            geom = f.geometry()
            t = geom.wkbType()

            if t == QGis.WKBPoint:
                isPointsGeom = True
                break
            elif t == QGis.WKBMultiPoint:
                mpt = geom.asMultiPoint()
                ll = len(mpt)
                if ll > 1:
                    isPointsGeom = False
                else:
                    isPointsGeom = True
                break
            elif t == QGis.WKBLineString:
                isPointsGeom = False
                break
            elif t == QGis.WKBPolygon:
                isPointsGeom = False
                break

        if isPointsGeom:
            self.processAsPoints()
        else:
            self.processAsMultiPoints()

        self.iface.messageBar().pushMessage(self.tr('{0}/{1} is saved.')
                                                    .format(groupNameToSave, setNameToSave), duration=20)

    def createGroupSet(self, groupNameToSave, setNameToSave):
        if self.groupNo < 0:
            #Create new Group
            self.groupNo = self.maxMapSetNo + 1
            if not self.executeInsert("insert into tig_map_set (db_sldnid, tig_map_set_name, tig_map_set_no, "
                                      "TIG_MAP_SET_TYPE, tig_interpreter_sldnid) "
                               "values (TIG_MAP_SET_SEQ.nextval, '{0}', {1}, {2}, {3})"
                               .format(groupNameToSave, self.groupNo, self.mapSetType, self.interpreter)):
                return

        # Create new param set
        self.paramNo = self.maxMapSetParameterNo + 1
        sql1 = ("insert into tig_map_set_param (db_sldnid, tig_param_short_name, TIG_PARAM_LONG_NAME, "
                "tig_map_set_no, tig_map_set_parameter_no, TIG_MAP_SET_CP_SOURCE, tig_interpreter_sldnid ) "
                "values (TIG_MAP_SET_PARAM_SEQ.nextval, '19', '{0}', {1}, {2}, {3}, {4})"
                .format(setNameToSave, self.groupNo, self.paramNo, self.mapSetCpSource, self.interpreter))
        self.db.execute(sql1)

    def processAsPoints(self):
        features = self.currentLayer.getFeatures()
        pointsX = []
        pointsY = []
        params = []
        paramName = 'Qgis'
        prevKey = None
        key = None
        for f in features:
            if self.keyFieldIndex >= 0:
                key = f.attribute(self.keyFieldName)

            if prevKey and prevKey != key:
                self.writePoints(pointsX, pointsY, params, paramName)
                pointsX = []
                pointsY = []
                params = []

            parameter = -9999
            if self.subsetFieldIndex >= 0:
                paramName = f.attribute(self.subsetFieldName)
            if self.parameterFieldIndex >= 0:
                par = f.attribute(self.parameterFieldName)
                if par:
                    parameter = float(par)

            geom = f.geometry()
            t = geom.wkbType()
            pt = None
            if t == QGis.WKBPoint:
                pt = self.xform.transform(geom.asPoint())
            elif t == QGis.WKBMultiPoint:
                mpt = geom.asMultiPoint()
                if len(mpt):
                    pt = self.xform.transform(mpt[0])

            if pt:
                pointsX.append(pt.x())
                pointsY.append(pt.y())
                params.append(parameter)

            prevKey = key

        if len(pointsX):
            self.writePoints(pointsX, pointsY, params, paramName)


    def writePoints(self, pointsX, pointsY, params, paramName):
        assert len(params)==len(pointsX), 'Parameters/points are mismatch'
        subsetNo = self.maxMapSubsetNo+1

        npX = np.asarray(pointsX, '>d').tostring()
        npY = np.asarray(pointsY, '>d').tostring()
        npZ = np.asarray(params, '>d').tostring()
        sql = ("insert into tig_map_subset (db_sldnid, tig_map_subset_name, tig_map_set_no, "
               "tig_map_subset_no, tig_interpreter_sldnid, TIG_MAP_X, TIG_MAP_Y) "
               "values (TIG_MAP_SUBSET_SEQ.nextval, '{0}', {1}, {2}, {3}, :blobX, :blobY)"
               .format(paramName, self.groupNo, subsetNo, self.interpreter))

        sql2 = ("insert into tig_map_subset_param_val (db_sldnid, "
                "tig_map_set_no, tig_map_subset_no, tig_map_set_parameter_no, tig_interpreter_sldnid, "
                "TIG_MAP_PARAM_VRLONG ) values (TIG_MAP_SUBSET_PARAM_VAL_SEQ.nextval, {0}, {1}, {2}, {3}, :paramZ)"
                .format(self.groupNo, subsetNo, self.paramNo, self.interpreter))

        cursor = self.db.cursor()
        blobvarX = cursor.var(cx_Oracle.BLOB)
        blobvarX.setvalue(0, npX)
        blobvarY = cursor.var(cx_Oracle.BLOB)
        blobvarY.setvalue(0, npY)
        blobvarZ = cursor.var(cx_Oracle.BLOB)
        blobvarZ.setvalue(0, npZ)

        self.db.execute(sql, blobX=blobvarX, blobY=blobvarY)
        self.db.execute(sql2, paramZ=blobvarZ)
        self.db.commit()

        self.maxMapSubsetNo = self.maxMapSubsetNo + 1

    def processAsMultiPoints(self):

        features = self.currentLayer.getFeatures()
        for f in features:
            paramName = 'Qgis'
            parameter = -9999
            if self.subsetFieldIndex >= 0:
                paramName = f.attribute(self.subsetFieldName)
            if self.parameterFieldIndex >= 0:
                par = f.attribute(self.parameterFieldName)
                if par:
                    parameter = float(par)

            geom = f.geometry()
            pointsX = []
            pointsY = []
            params = []
            t = geom.wkbType()
            if t == QGis.WKBMultiPoint:
                mpt = geom.asMultiPoint()
                for pt in mpt:
                    newPt = self.xform.transform(pt)
                    pointsX.append(newPt.x())
                    pointsY.append(newPt.y())
                    params.append(parameter)
                self.writePoints(pointsX, pointsY, params, paramName)
            elif t == QGis.WKBLineString:
                mpt = geom.asPolyline()
                for pt in mpt:
                    newPt = self.xform.transform(pt)
                    pointsX.append(newPt.x())
                    pointsY.append(newPt.y())
                    params.append(parameter)
                self.writePoints(pointsX, pointsY, params, paramName)
            elif t == QGis.WKBPolygon:
                mpt = geom.asPolygon()
                for polyline in mpt:
                    for pt in polyline:
                        newPt = self.xform.transform(pt)
                        pointsX.append(newPt.x())
                        pointsY.append(newPt.y())
                        params.append(parameter)
                    self.writePoints(pointsX, pointsY, params, paramName)


    def writeSurface(self):
        gdal_input_raster = gdal.Open(self.currentLayer.source())
        band = gdal_input_raster.GetRasterBand(1)
        input_raster = np.array(band.ReadAsArray())

        cols = gdal_input_raster.RasterXSize
        rows = gdal_input_raster.RasterYSize
        noDataValue = band.GetNoDataValue()
        stats = band.GetStatistics(0,1)
        minZ = 0
        maxZ = 0
        if len(stats):
            minZ = stats[0]
        if len(stats) > 1:
            maxZ = stats[1]
        (min_x, step_x, x_rotation, min_y, y_rotation, step_y) = gdal_input_raster.GetGeoTransform()
        max_x = min_x + step_x * (cols-1)
        max_y = min_y + step_y * (rows-1)
        if step_y < 0:
            tmp = min_y
            min_y = max_y
            max_y = tmp
            step_y = -step_y

        minPoint = self.xform.transform(QgsPoint(min_x, min_y))
        maxPoint = self.xform.transform(QgsPoint(max_x, max_y))

        # print step_x, (maxPoint.x()-minPoint.x())/(cols-1)

        x = [min_x, max_x, step_x]
        y = [min_y, max_y, step_y]
        z = [minZ, maxZ, 0]

        size_x = int((max_x - min_x) / step_x + 1.005)
        size_y = int((max_y - min_y) / step_y + 1.005)
        # print cols, rows, size_x, size_y, minZ, maxZ

        input_raster[input_raster == noDataValue] = 1E+20
        data = np.flipud(input_raster)
        data = data.reshape((cols*rows))
        dataStr = np.asarray(data, '>f').tostring()
        xStr = np.asarray(x, '>d').tostring()
        yStr = np.asarray(y, '>d').tostring()
        zStr = np.asarray(z, '>d').tostring()

        cursor = self.db.cursor()
        blobvarData = cursor.var(cx_Oracle.BLOB)
        blobvarData.setvalue(0, dataStr)
        blobvarX = cursor.var(cx_Oracle.BLOB)
        blobvarX.setvalue(0, xStr)
        blobvarY = cursor.var(cx_Oracle.BLOB)
        blobvarY.setvalue(0, yStr)
        blobvarZ = cursor.var(cx_Oracle.BLOB)
        blobvarZ.setvalue(0, zStr)

        subsetNo = self.maxMapSubsetNo + 1
        paramName = 'Surface from QGIS'
        sql = ("insert into tig_map_subset (db_sldnid, tig_map_subset_name, tig_map_set_no, "
               "tig_map_subset_no, tig_interpreter_sldnid, TIG_MAP_X, TIG_MAP_Y) "
               "values (TIG_MAP_SUBSET_SEQ.nextval, '{0}', {1}, {2}, {3}, :blobX, :blobY)"
               .format(paramName, self.groupNo, subsetNo, self.interpreter))

        sql2 = ("insert into tig_map_subset_param_val (db_sldnid, "
                "tig_map_set_no, tig_map_subset_no, tig_map_set_parameter_no, tig_interpreter_sldnid, "
                "TIG_MAP_PARAM_VRSHRT ) values (TIG_MAP_SUBSET_PARAM_VAL_SEQ.nextval, {0}, {1}, {2}, {3}, :paramZ)"
                .format(self.groupNo, subsetNo, self.paramNo, self.interpreter))

        self.db.execute(sql, blobX=blobvarX, blobY=blobvarY)
        self.db.execute(sql2, paramZ=blobvarData)
        self.db.commit()
