# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisPDS
                                 A QGIS plugin
 PDS link
                              -------------------
        begin                : 2016-11-05
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Viktor Kondrashov
        email                : viktor@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsVertexMarker
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from qgis_pds_dialog import QgisPDSDialog
from qgis_pds_production import QgisPDSProductionDialog
from qgis_pds_cpoints import QgisPDSCPointsDialog
from qgis_pds_wells import *
from qgis_pds_prodRenderer import *
from qgis_pds_prod_layer_type import *
from qgis_pds_prodSetup import *
from qgis_pds_bubbleSetup import *
from QgisPDS.ControlPointReader import ControlPointReader
from QgisPDS.ContoursReader import ContoursReader
from QgisPDS.SurfaceReader import SurfaceReader
from QgisPDS.qgis_pds_CoordFromZone import QgisPDSCoordFromZoneDialog
from QgisPDS.qgis_pds_zonations import QgisPDSZonationsDialog
from QgisPDS.qgis_pds_residual import QgisPDSResidualDialog
from QgisPDS.qgis_pds_pressureMap import QgisPDSPressure
from QgisPDS.qgis_pds_deviation import QgisPDSDeviation
from QgisPDS.qgis_pds_statistic import QgisPDSStatisticsDialog
from QgisPDS.qgis_pds_refreshSetup import QgisPDSRefreshSetup
from QgisPDS.qgis_pds_SaveMapsetToPDS import QgisSaveMapsetToPDS
from QgisPDS.qgis_pds_oracleSql import QgisOracleSql
from QgisPDS.qgis_pds_createIsolines import QgisPDSCreateIsolines
from QgisPDS.qgis_pds_transite import QgisPDSTransitionsDialog
from qgis_pds_SelectMapTool import QgisPDSSelectMapTool
import os
import os.path
import ast
import json


class QgisPDS(QObject):
    """QGIS Plugin Implementation."""

    def __init__(self, _iface):
        """Constructor. """
        QObject.__init__(self)
        # Save reference to the QGIS interface
        self.iface = _iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QgisPDS_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&PDS')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'QgisPDS')
        self.toolbar.setObjectName(u'QgisPDS')
        
        #Restore settings
        self.currentProject = QSettings().value('currentProject')

        #Connect signals
        self.connectToProject()

        self.labelPositions = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.onTimer)
        # QObject.connect(self.timer, SIGNAL("timeout()"), self.onTimer)

        self.selectMapTool = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('QgisPDS', message)


    def connectToProject(self):
        proj = QgsProject.instance()
        proj.readProject.connect(self.loadData)
        QObject.connect(self.iface.legendInterface(), SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerSelected)
        # QObject.connect(self.iface.mapCanvas(), SIGNAL("mapCanvasRefreshed ()"), self.renderComplete)


    def disconnectFromProject(self):
        proj = QgsProject.instance()
        proj.readProject.disconnect(self.loadData)
        self.disconnectFromLayers()
        QObject.disconnect(self.iface.legendInterface(), SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerSelected)

        # QObject.disconnect(self.iface.mapCanvas(), SIGNAL("mapCanvasRefreshed ()"), self.renderComplete)


    
    def loadData(self):
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            if not layer.type() == 0:
                continue

            if bblInit.isProductionLayer(layer) or bblInit.isWellLayer(layer):
                layer.attributeValueChanged.connect(self.pdsLayerModified)


    def disconnectFromLayers(self):
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            if not layer.type() == 0:
                continue

            try:
                if bblInit.isProductionLayer(layer) or bblInit.isWellLayer(layer):
                    layer.attributeValueChanged.disconnect(self.pdsLayerModified)
            except:
                pass

    def pdsLayerModified(self, FeatureId, idx, variant):
        sender = self.sender()
        if not sender or not sender.type() == 0 or sender == self:
            return

        editedLayer = sender
        mc = self.iface.mapCanvas()
        tr = mc.getCoordinateTransform()
        xMm = mc.mapSettings().outputDpi() / 25.4

        dp = editedLayer.dataProvider()
        editFeature = QgsFeature()
        if editedLayer == None or editedLayer.getFeatures(QgsFeatureRequest().setFilterFid(FeatureId)).nextFeature(
                editFeature) is False:
            return
        else:
            # print 'traitement signal'
            editGeom = editFeature.geometry()
            editLayerProvider = editedLayer.dataProvider()
            fields = editLayerProvider.fields()

            fieldname = ''
            try:
                fieldname = fields[idx].name()
            except:
                pass
            originX = editGeom.asPoint().x()
            originY = editGeom.asPoint().y()
            pixelOrig = tr.transform(QgsPoint(originX, originY))

            idxOffX = editLayerProvider.fieldNameIndex('labloffx')
            idxOffY = editLayerProvider.fieldNameIndex('labloffy')
            if idxOffX < 0 or idxOffY < 0:
                editLayerProvider.addAttributes(
                    [QgsField("labloffx", QVariant.Double),
                     QgsField("labloffy", QVariant.Double)])
                idxOffX = editLayerProvider.fieldNameIndex('labloffx')
                idxOffY = editLayerProvider.fieldNameIndex('labloffy')

            if editLayerProvider.fieldNameIndex('labloffset') < 0:
                editLayerProvider.addAttributes([QgsField("labloffset", QVariant.Double)])

            if idxOffX < 0 or idxOffY < 0:
                return


            if fieldname.lower() == 'lablx':
                if variant == NULL:  # case when user unpins the label > sets arrow back to arrow based on point location
                    return
                if isinstance(variant, basestring):  # test case, when editing from attribute table, variant is sent as text! converts to float
                    variant = float(variant)
                newFinalX = variant

                pixelOffset = tr.transform(QgsPoint(newFinalX, originY))
                mmOffset = (pixelOffset.x() - pixelOrig.x()) / xMm

                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablX'), None)
                editedLayer.changeAttributeValue(FeatureId, idxOffX, mmOffset)
                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('labloffset'), 1)

            if fieldname.lower() == 'lably':
                if variant == NULL:  # case when user unpins the label > sets arrow back to arrow based on point location
                    return
                if isinstance(variant, basestring):  # test case, when editing from attribute table, variant is sent as text! converts to float
                    variant = float(variant)
                newFinalY = variant

                pixelOffset = tr.transform(QgsPoint(originX, newFinalY))
                mmOffset = (pixelOffset.y() - pixelOrig.y()) / xMm

                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablY'), None)
                editedLayer.changeAttributeValue(FeatureId, idxOffY, mmOffset)
                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('labloffset'), 1)


    @property
    def sldnidFieldName(self):
        return 'sldnid'

    def layerSelected(self, layer):
        """Change action enable"""
        enabled = False
        enabledWell = False
        runAppEnabled = False
        try:
            if layer is not None:
                enabled = bblInit.isProductionLayer(layer)
                enabledWell = bblInit.isWellLayer(layer)
                runAppEnabled = layer.fieldNameIndex(self.sldnidFieldName) >= 0
        except:
            pass

        self.actionProductionSetup.setEnabled(enabled)
        self.actionCoordsFromZone.setEnabled(enabled or enabledWell)
        self.actionTransiteWells.setEnabled(enabled or enabledWell)

        self.runAppAction.setEnabled(runAppEnabled)


    
    #Save label positions
    def onTimer(self):
        self.timer.stop()

        mc = self.iface.mapCanvas()
        lr = mc.labelingResults()

        layers = mc.layers()
        ll = {}
        commitLayers = []
        if layers is not None:
            for lay in layers:
                if bblInit.isProductionLayer(lay):
                    ll[lay.id()] = lay
                    if not lay.isEditable():
                        lay.startEditing()
                        commitLayers.append(lay)

            for l in self.labelPositions:
                curLayer = ll[l.layerID]  
                if curLayer is not None:
                    curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablWidth'), l.width)  
                    curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffX'), l.labelRect.xMinimum())      
                    curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffY'), l.labelRect.yMinimum())                       
                        
                
        for lay in commitLayers:
            lay.commitChanges()

        self.labelPositions = []

    def getLabelLayerName(self, name):
        return name + ' - outline'

    def createLabelLayer(self, lay, name):
        crs = lay.crs()
        if crs:
            crsString = crs.toProj4()
            self.uri = "LineString?crs=PROJ4:{}".format(crsString)
            self.uri += '&field={}:{}'.format("SLDNID", "int")
            layer = QgsVectorLayer(self.uri, name, "memory")
            if layer:
                QgsMapLayerRegistry.instance().addMapLayer(layer)
            return layer
        return None

    def checkLabellingLayer(self, lay):
        labelLayerName = self.getLabelLayerName(lay.name())
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            if layer.name() == labelLayerName:
                return layer

        return self.createLabelLayer(lay, labelLayerName)


    #Collect label positions
    def renderComplete(self):
        mc = self.iface.mapCanvas()
        lr = mc.labelingResults()

        layers = mc.layers()
        ll = {}
        ll1 = {}
        if layers is None:
            return

        for lay in layers:
            if bblInit.isProductionLayer(lay):
                labelLayer = self.checkLabellingLayer(lay)
                if labelLayer:
                    ll[lay.id()] = lay
                    ll1[lay.id()] = labelLayer

        if len(ll) < 1:
            return

        # self.timer.stop()
        self.labelPositions = []

        tr = mc.getCoordinateTransform()
        xMm = mc.mapSettings().outputDpi() / 25.4

        commitLayers = []
        if lr is not None:
            labels = lr.labelsWithinRect(mc.extent())
            if labels is not None:
                for l in labels:
                    if not l.layerID in ll:
                        continue

                    curLayer = ll[l.layerID]
                    curLabLayer = ll1[l.layerID]
                    rect = l.labelRect
                    if curLayer is not None:

                        ff = curLayer.getFeatures(QgsFeatureRequest(l.featureId))
                        if ff is not None:
                            if not curLabLayer.isEditable():
                                curLabLayer.startEditing()
                                commitLayers.append(curLabLayer)
                            for f in ff:
                                editGeom = f.geometry()
                                geom = QgsGeometry.fromPolyline([editGeom.asPoint(), QgsPoint(rect.xMinimum(), rect.yMinimum())])

                                expr = QgsExpression('\"{0}\"={1}'.format("SLDNID", l.featureId))
                                searchRes = curLabLayer.getFeatures(QgsFeatureRequest(expr))
                                num = 0
                                for f1 in searchRes:
                                    curLabLayer.changeGeometry(f1.id(), geom)
                                    num = num + 1

                                if num == 0:
                                    fea = QgsFeature(curLabLayer.fields())
                                    fea.setAttribute("SLDNID", l.featureId)
                                    fea.setGeometry(geom)
                                    curLabLayer.addFeatures([fea])

                                # originX = editGeom.asPoint().x()
                                # originY = editGeom.asPoint().y()
                                # pixelOrig = tr.transform(editGeom.asPoint())
                                # pixelOffset = tr.transform(QgsPoint( rect.xMinimum(), rect.yMinimum()))
                                # mmOffsetX = (pixelOffset.x() - pixelOrig.x()) / xMm
                                # mmOffsetY = (pixelOffset.y() - pixelOrig.y()) / xMm
                                # curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablWidth'), l.width)
                                # curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffX'), mmOffsetX)
                                # curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffY'), mmOffsetY)


        for lay in commitLayers:
            lay.commitChanges()
        mc.refresh()
        # if len(self.labelPositions) > 0:
        #     self.timer.start(100)
        

    def add_action(
        self,
        icon_path,
        text,
        callback=None,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
        menu=None):
        

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        if callback is not None:
            action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if menu is not None:
            action.setMenu(menu)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        toolTipText = self.tr(u'Select PDS project')
        if self.currentProject:
            toolTipText += ' ({0})'.format(self.currentProject['project'])

        icon_path = ':/plugins/QgisPDS/splash_logo.png'
        self.selectProjectAction = self.add_action(
            icon_path,
            text=toolTipText,
            callback=self.selectProject,
            status_tip=self.tr(u'Select project'),
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR028.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load control points'),
            callback=self.createCPointsLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR029.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load faults'),
            callback=self.createFaultsLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR014.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load contours'),
            callback=self.createContoursLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR030.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load polygons'),
            callback=self.createPolygonsLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR012.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load surface'),
            callback=self.createSurfaceLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/ME002.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load wells'),
            callback=self.createWellLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/deviations.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load well deviations'),
            callback=self.createWellDeviationLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/GeoPROD24a.png'
        self.actionCurrentProduction = self.add_action(
            icon_path,
            text=self.tr(u'Load current production'),
            callback=self.createProductionlayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/GeoPROD24Sum.png'
        self.actionProduction = self.add_action(
            icon_path,
            text=self.tr(u'Load production'),
            callback=self.createSummProductionlayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/Pressure-50.png'
        self.actionLoadPressure = self.add_action(
            icon_path,
            text=u'Загрузить давления',
            callback=self.loadPressure,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/zonation.png'
        self.actionLoadPressure = self.add_action(
            icon_path,
            text=self.tr(u'Zonation parameters'),
            callback=self.loadZonations,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/piechart1.png'
        self.actionProductionSetup = self.add_action(
            icon_path,
            text=self.tr(u'Production setup'),
            callback=self.productionSetup,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/piechart2.png'
        self.actionBubblesSetup = self.add_action(
            icon_path,
            text=self.tr(u'Bubbles setup'),
            callback=self.bubblesSetup,
            enabled_flag=True,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/CoordFromZonations.png'
        self.actionCoordsFromZone = self.add_action(
            icon_path,
            text=self.tr(u'Well coordinate from zone'),
            callback=self.wellCoordFromZone,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/mActionFilter.png'
        self.actionTransiteWells = self.add_action(
            icon_path,
            text=self.tr(u'Mark transite wells'),
            callback=self.transiteWells,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/Refresh.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'Update production layer'),
            callback=self.refreshLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/water-drop.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'Residuals'),
            callback=self.residuals,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/statistics.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'Calculate statistics'),
            callback=self.calcStatistics,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/mActionFileSave.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Save to PDS'),
            callback=self.saveLayerToPDS,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/new_sql_query.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Layer from Oracle SQL'),
            callback=self.dataFromOracleSql,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/GeoCART24.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create isolines'),
            callback=self.createIsolines,
            parent=self.iface.mainWindow())

        applicationMenu = QMenu(self.iface.mainWindow())
        action = QAction(self.tr(u'Well Correlation && Zonation'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startWcorr)
        action = QAction(self.tr(u'Well view'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startWellView)
        action = QAction(self.tr(u'Well Log Processing'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startWellLogProcessing)
        action = QAction(self.tr(u'Deviation Survey'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startDevSurvey)
        action = QAction(self.tr(u'Log Plot'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startLogPlot)
        applicationMenu.addSeparator()
        action = QAction(self.tr(u'Seismic Interpretation 2D'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.seis2D)
        action = QAction(self.tr(u'Seismic Interpretation 3D'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.seis3D)

        icon_path = ':/plugins/QgisPDS/play_24x24.png'
        self.runAppAction = self.add_action(
            icon_path,
            text=self.tr(u'Run application'),
            parent=self.iface.mainWindow(),
            enabled_flag=False,
            menu=applicationMenu)

        self._metadata = BabbleSymbolLayerMetadata()
        QgsSymbolLayerV2Registry.instance().addSymbolLayerType(self._metadata)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginDatabaseMenu( self.tr(u'&PDS'), action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

        # QgsPluginLayerRegistry.instance().removePluginLayerType(QgisPDSProductionLayer.LAYER_TYPE)

        #remove SIGNALS
        self.disconnectFromProject()


    def setReferenceLayer(self, layer):
        self.layer = layer


    def selectProject(self):
        dlg = QgisPDSDialog(self.iface)
        if self.currentProject is not None:
            dlg.setCurrentProject(self.currentProject)
        
        result = dlg.exec_()
        if result:
            self.currentProject = dlg.selectedProject()           
            self.saveSettings()
            toolTipText = self.tr(u'Select PDS project')
            if self.currentProject:
                toolTipText += ' ({0})'.format(self.currentProject['project'])
            self.selectProjectAction.setToolTip(toolTipText)
      
            
    def createProductionlayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return

        dlg = QgisPDSProductionDialog(self.currentProject, self.iface)
        if dlg.isInitialised():
            result = dlg.exec_()
            if dlg.getLayer() is not None:
                dlg.getLayer().attributeValueChanged.connect(self.pdsLayerModified)


    def loadPressure(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return

        dlg = QgisPDSPressure(self.currentProject, self.iface)
        if dlg.isInitialised():
            result = dlg.exec_()

    def loadZonations(self):
        dlg = QgisPDSZonationsDialog(self.currentProject, self.iface)
        dlg.exec_()

    def placeLabels(self):
        self.renderComplete()

    def createSummProductionlayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return

        dlg = QgisPDSProductionDialog(self.currentProject, self.iface, False)
        if dlg.isInitialised():
            result = dlg.exec_()
            if dlg.getLayer() is not None:
                dlg.getLayer().attributeValueChanged.connect(self.pdsLayerModified)


    def loadProduction(self, layer, project, isCurrentProd):
        dlg = QgisPDSProductionDialog(project, self.iface, isCurrentProd, layer)
        if dlg.isInitialised():
            result = dlg.exec_()
            if result and layer:
                prodSetup = QgisPDSProdSetup(self.iface, layer)
                prodSetup.setup(layer)
        del dlg


    def createCPointsLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ControlPointReader())
        dlg.exec_()


    def createContoursLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(0))
        dlg.exec_()


    def createPolygonsLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(1))
        dlg.exec_()

    def createSurfaceLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, SurfaceReader())
        dlg.exec_()
        del dlg


    def createFaultsLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(2))
        dlg.exec_()
      

    def createWellLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load wells'), level=QgsMessageBar.CRITICAL)
            return

        wells = QgisPDSWells(self.iface, self.currentProject)
        layer = wells.createWellLayer()
        if layer is not None:
            layer.attributeValueChanged.connect(self.pdsLayerModified)


    def createWellDeviationLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr("Error"),
                        self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
            return

        wells = QgisPDSDeviation(self.iface, self.currentProject)
        layer = wells.createWellLayer()
        # if layer is not None:
        #     layer.attributeValueChanged.connect(self.pdsLayerModified)

        
    def loadWells(self, layer, project, isRefreshKoords, isRefreshData, isSelectedOnly):
        wells = QgisPDSWells(self.iface, project)
        wells.loadWells(layer, isRefreshKoords, isRefreshData, isSelectedOnly)


    def loadWellDeviations(self, layer, project, isRefreshKoords, isRefreshData, isSelectedOnly):
        wells = QgisPDSDeviation(self.iface, project)
        wells.loadWells(layer, isRefreshKoords, isRefreshData, isSelectedOnly)


    def productionSetup(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            return

        currentLayer = self.iface.activeLayer()
        if currentLayer is None:
            return

        prodSetup = QgisPDSProdSetup(self.iface, currentLayer)
        prodSetup.exec_()

    def bubblesSetup(self):
        currentLayer = self.iface.activeLayer()
        if currentLayer is None:
            return

        prodSetup = QgisPDSBubbleSetup(self.iface, currentLayer)
        prodSetup.exec_()


    def wellCoordFromZone(self):
        currentLayer = self.iface.activeLayer()
        if currentLayer is None:
            return

        projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
        proj = ast.literal_eval(projStr)

        dlg  = QgisPDSCoordFromZoneDialog(self.currentProject, self.iface, currentLayer)
        dlg.exec_()
        return

    def transiteWells(self):
        currentLayer = self.iface.activeLayer()
        if currentLayer is None:
            return

        projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
        proj = ast.literal_eval(projStr)

        dlg = QgisPDSTransitionsDialog(self.currentProject, self.iface, currentLayer)
        dlg.exec_()
        return

        
    def refreshLayer( self):
        currentLayer = self.iface.activeLayer()
        if currentLayer.type() != QgsMapLayer.VectorLayer:
            return
        pr = currentLayer.dataProvider()

        projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
        proj = ast.literal_eval(projStr)

        prop = currentLayer.customProperty("qgis_pds_type")
        if prop == "pds_wells":
            dlg = QgisPDSRefreshSetup(self.currentProject)
            if dlg.exec_():
                self.loadWells(currentLayer, self.currentProject, dlg.isRefreshKoords, dlg.isRefreshData, dlg.isSelectedOnly)
        elif prop == "pds_current_production":
            self.loadProduction(currentLayer, self.currentProject, True)
        elif prop == "pds_cumulative_production":
            self.loadProduction(currentLayer, self.currentProject, False)
        elif prop == "pds_well_deviations":
            dlg = QgisPDSRefreshSetup(self.currentProject)
            if dlg.exec_():
                self.loadWellDeviations(currentLayer, self.currentProject, dlg.isRefreshKoords, dlg.isRefreshData, dlg.isSelectedOnly)

       
    def addProductionLayer(self):
        layer = QgisPDSProductionLayer(self.iface)
        if layer.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(layer)

    def residuals(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSResidualDialog(self.currentProject, self.iface)
        dlg.exec_()
        return

    def calcStatistics(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSStatisticsDialog(self.currentProject, self.iface)
        dlg.exec_()
        return

    def saveLayerToPDS(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        dlg = QgisSaveMapsetToPDS(self.currentProject, self.iface, currentLayer)
        dlg.exec_()

    def dataFromOracleSql(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            return

        dlg = QgisOracleSql(self.currentProject, self.iface)
        dlg.exec_()

    def createIsolines(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            return

        dlg = QgisPDSCreateIsolines(self.iface)
        dlg.exec_()

    def createProjectString(self, args={}):
        projectName = args['project']
        options = json.loads(args['options'])
        host = options['host']
        sid = options['sid']

        return u'{0}/{1}/{2}'.format(host, sid, projectName)

    def startSelectMapTool(self, layer, exeName, appArgs):
        if not self.selectMapTool:
            self.selectMapTool = QgisPDSSelectMapTool(self.iface.mapCanvas(), layer)
            self.selectMapTool.finished.connect(self.selectMapTool_finished)

        self.selectMapTool.setArgs(exeName, appArgs)
        self.iface.mapCanvas().setMapTool(self.selectMapTool)

    @pyqtSlot(list, str, str)
    def selectMapTool_finished(self, features, exeName, appArgs):
        if len(features):
            ids = self.getSelectedSldnids(features)
            # print  appArgs + '{' + ids + '})" '
            self.runTigressProcess(exeName, appArgs + '{' + ids + '})" ')


    def startWcorr(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"wcorr.load_template(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'wcorr.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('wcorr.exe', args)

    def startWellView(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"wellview.load_well(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'wellview.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('wellview.exe', args)

    def startWellLogProcessing(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"gsp.load_tz_table(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'gsp.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('gsp.exe', args)

    def startDevSurvey(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"dvsrvy.load_survey(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'dvsrvy.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('dvsrvy.exe', args)

    def startLogPlot(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"compos.load_resultsplot(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'compos.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('compos.exe', args)

    def seis2D(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        ids = '0'
        args = " -script \"inp.load_2dlines(" + "'{0}', ".format(project)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('inp.exe', args)

    def seis3D(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        ids = '0'
        args = " -script \"inp.load_survey3d(" + "'{0}', ".format(project)
        args += '{' + ids + '})" '
        self.runTigressProcess('inp.exe', args)
        
    def saveSettings(self):
        QSettings().setValue('currentProject', self.currentProject)

    def runTigressProcess(self, appName, args):
        tigdir = os.environ['TIGDIR']
        tigdir = tigdir.replace('\\', '/')
        exeName = tigdir + '/bin/' + appName
        if not os.path.exists(exeName):
            exeName = tigdir + '/../bin/' + appName

        if not os.path.exists(exeName):
            QtGui.QMessageBox.critical(None, self.tr(u'Error'),
                                       appName + ': ' + self.tr(u'file not found.\nPlease set TIGDIR variable'.format(appName)),
                                       QtGui.QMessageBox.Ok)
            return

        runStr = exeName + ' ' + args
        process = QProcess(self.iface)
        process.start(runStr)

    # def getSelectedSldnids(self, layer):
    #     idx = layer.fieldNameIndex(self.sldnidFieldName)
    #     if idx < 0:
    #         return '';
    #
    #     result = '0'
    #     features = layer.selectedFeatures()
    #     for f in features:
    #          result += ',{0}'.format(f.attribute(self.sldnidFieldName))
    #
    #     return result
    def getSelectedSldnids(self, features):
        result = '0'
        try:
            for f in features:
                 result += ',{0}'.format(f.attribute(self.sldnidFieldName))
        except:
            pass

        return result