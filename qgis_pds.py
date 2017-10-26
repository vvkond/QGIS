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
from qgis_pds_prod_layer import *
from qgis_pds_prod_layer_type import *
from qgis_pds_prodSetup import *
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
import os.path


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


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('QgisPDS', message)


    def connectToProject(self):
        proj = QgsProject.instance()
        proj.readProject.connect(self.loadData)
        # QObject.connect(proj, SIGNAL("readProject(const QDomDocument &)"),self.loadData)
        # QObject.connect(QgsMapLayerRegistry.instance(), SIGNAL("layerWasAdded(QgsMapLayer *)"),self.connectProvider)
        QObject.connect(self.iface.legendInterface(), SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerSelected)
        # QObject.connect(self.iface.mapCanvas(), SIGNAL("mapCanvasRefreshed ()"), self.renderComplete)


    def disconnectFromProject(self):
        proj = QgsProject.instance()
        proj.readProject.disconnect(self.loadData)
        # QObject.disconnect(proj, SIGNAL("readProject(const QDomDocument &)"),self.loadData)
        # QObject.disconnect(QgsMapLayerRegistry.instance(), SIGNAL("layerWasAdded(QgsMapLayer *)"),self.connectProvider)
        QObject.disconnect(self.iface.legendInterface(), SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerSelected)
        # QObject.disconnect(self.iface.mapCanvas(), SIGNAL("mapCanvasRefreshed ()"), self.renderComplete)


    
    def loadData(self):
        name = QgsProject.instance().fileName()
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            if not layer.type() == 0:
                return

            if bblInit.isProductionLayer(layer) or bblInit.isWellLayer(layer):
                layer.attributeValueChanged.connect(self.pdsLayerModified)


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

            idxOffX = editLayerProvider.fieldNameIndex('LablOffX')
            idxOffY = editLayerProvider.fieldNameIndex('LablOffY')
            if idxOffX < 0 or idxOffY < 0:
                editLayerProvider.addAttributes(
                    [QgsField("LablOffX", QVariant.Double),
                     QgsField("LablOffY", QVariant.Double)])
                idxOffX = editLayerProvider.fieldNameIndex('LablOffX')
                idxOffY = editLayerProvider.fieldNameIndex('LablOffY')

            if idxOffX < 0 or idxOffY < 0:
                return


            if fieldname == 'LablX':
                if variant == NULL:  # case when user unpins the label > sets arrow back to arrow based on point location
                    return
                if isinstance(variant, basestring):  # test case, when editing from attribute table, variant is sent as text! converts to float
                    variant = float(variant)
                newFinalX = variant

                pixelOffset = tr.transform(QgsPoint(newFinalX, originY))
                mmOffset = (pixelOffset.x() - pixelOrig.x()) / xMm

                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablX'), None)
                editedLayer.changeAttributeValue(FeatureId, idxOffX, mmOffset)
                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablOffset'), 1)

            if fieldname == 'LablY':
                if variant == NULL:  # case when user unpins the label > sets arrow back to arrow based on point location
                    return
                if isinstance(variant, basestring):  # test case, when editing from attribute table, variant is sent as text! converts to float
                    variant = float(variant)
                newFinalY = variant

                pixelOffset = tr.transform(QgsPoint(originX, newFinalY))
                mmOffset = (pixelOffset.y() - pixelOrig.y()) / xMm

                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablY'), None)
                editedLayer.changeAttributeValue(FeatureId, idxOffY, mmOffset)
                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablOffset'), 1)




    def layerSelected(self, layer):
        """Change action enable"""
        enabled = False
        enabledWell = False
        if layer is not None: 
            enabled = bblInit.isProductionLayer(layer)
            enabledWell = bblInit.isWellLayer(layer)

        self.actionProductionSetup.setEnabled(enabled)
        self.actionCoordsFromZone.setEnabled(enabled or enabledWell)


    
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
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

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

        icon_path = ':/plugins/QgisPDS/splash_logo.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Select PDS project'),
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

        icon_path = ':/plugins/QgisPDS/CoordFromZonations.png'
        self.actionCoordsFromZone = self.add_action(
            icon_path,
            text=self.tr(u'Well coordinate from zone'),
            callback=self.wellCoordFromZone,
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

        # icon_path = ':/plugins/QgisPDS/label.png'
        # self.actionCPlaceLabels = self.add_action(
        #     icon_path,
        #     text=u'Расположить подписи',
        #     callback=self.placeLabels,
        #     parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginDatabaseMenu( self.tr(u'&PDS'), action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

        QgsPluginLayerRegistry.instance().removePluginLayerType(QgisPDSProductionLayer.LAYER_TYPE)

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
      
            
    def createProductionlayer(self):
        dlg = QgisPDSProductionDialog(self.currentProject, self.iface)
        if dlg.isInitialised():
            result = dlg.exec_()
            if dlg.getLayer() is not None:
                dlg.getLayer().attributeValueChanged.connect(self.pdsLayerModified)


    def loadPressure(self):
        dlg = QgisPDSPressure(self.currentProject, self.iface)
        if dlg.isInitialised():
            result = dlg.exec_()

    def loadZonations(self):
        dlg = QgisPDSZonationsDialog(self.currentProject, self.iface)
        dlg.exec_()

    def placeLabels(self):
        self.renderComplete()

    def createSummProductionlayer(self):
        dlg = QgisPDSProductionDialog(self.currentProject, self.iface, False)
        if dlg.isInitialised():
            result = dlg.exec_()
            if dlg.getLayer() is not None:
                dlg.getLayer().attributeValueChanged.connect(self.pdsLayerModified)


    def loadProduction(self, layer, project, isCurrentProd):
        dlg = QgisPDSProductionDialog(project, self.iface, isCurrentProd, layer)
        if dlg.isInitialised():
            result = dlg.exec_()
        # dlg.loadProductionLayer(layer)


    def createCPointsLayer(self):
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ControlPointReader())
        dlg.exec_()


    def createContoursLayer(self):
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(0))
        dlg.exec_()


    def createPolygonsLayer(self):
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(1))
        dlg.exec_()

    def createSurfaceLayer(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            return

        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, SurfaceReader())
        dlg.exec_()
        del dlg


    def createFaultsLayer(self):
        dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(2))
        dlg.exec_()
      

    def createWellLayer(self):
        # if not QgsProject.instance().homePath():
            # self.iface.messageBar().pushMessage(self.tr("Error"),
                        # self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            # return
        wells = QgisPDSWells(self.iface, self.currentProject)
        layer = wells.createWellLayer()
        if layer is not None:
            layer.attributeValueChanged.connect(self.pdsLayerModified)


    def createWellDeviationLayer(self):
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


    def wellCoordFromZone(self):
        currentLayer = self.iface.activeLayer()
        if currentLayer is None:
            return

        dlg  = QgisPDSCoordFromZoneDialog(self.currentProject, self.iface, currentLayer)
        dlg.exec_()
        return

        
    def refreshLayer( self):
        currentLayer = self.iface.activeLayer()
        if currentLayer.type() != QgsMapLayer.VectorLayer:
            return
        pr = currentLayer.dataProvider()

        prop = currentLayer.customProperty("qgis_pds_type")
        if prop == "pds_wells":
            dlg = QgisPDSRefreshSetup()
            if dlg.exec_():
                self.loadWells(currentLayer, self.currentProject, dlg.isRefreshKoords, dlg.isRefreshData, dlg.isSelectedOnly)
        elif prop == "pds_current_production":
            self.loadProduction(currentLayer, self.currentProject, True)
        elif prop == "pds_cumulative_production":
            self.loadProduction(currentLayer, self.currentProject, False)
        elif prop == "pds_well_deviations":
            dlg = QgisPDSRefreshSetup()
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

        
    def saveSettings(self):
        QSettings().setValue('currentProject', self.currentProject)
        
