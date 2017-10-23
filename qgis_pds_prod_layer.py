# -*- coding: utf-8 -*-
"""
/***************************************************************************
Production layer Plugin
A QGIS plugin

"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *



debuglevel = 4  # 0 (none) - 4 (all)


def debug(msg, verbosity=1):
    if debuglevel >= verbosity:
        try:
            qDebug(msg)
        except:
            pass

class CurrentProdRenderer(QgsMapLayerRenderer):
    def __init__(self, layer, context):
        """ Initialize the object. This function is still run in the GUI thread.
            Should refrain from doing any heavy work.
        """
        QgsMapLayerRenderer.__init__(self, layer.id())
        self.context = context
        self.loop = None

    def render(self):
        """ do the rendering. This function is called in the worker thread """

        debug("[WORKER THREAD] Calling request() asynchronously", 3)
        QMetaObject.invokeMethod(self.controller, "request")

        # setup a timer that checks whether the rendering has not been stopped in the meanwhile
        timer = QTimer()
        timer.setInterval(50)
        timer.timeout.connect(self.onTimeout)
        timer.start()

        debug("[WORKER THREAD] Waiting for the async request to complete", 3)
        self.loop = QEventLoop()
        # self.controller.finished.connect(self.loop.exit)
        self.loop.exec_()

        debug("[WORKER THREAD] Async request finished", 3)
        self.iface.messageBar().pushMessage('Current PDS project:')

        painter = self.context.painter()
        # painter.drawImage(0, 0, self.controller.img
        painter.setBrush(QBrush(Qt.blue))
        painter.drawEcllipse(52.2, 51.6, 1000, 1000)
        return True

    def onTimeout(self):
        """ periodically check whether the rendering should not be stopped """
        if self.context.renderingStopped():
            debug("[WORKER THREAD] Cancelling rendering", 3)
            self.loop.exit()

class QgisPDSProductionLayer(QgsPluginLayer):
    LAYER_TYPE="currentproduction"

    def __init__(self, iface):
        QgsPluginLayer.__init__(self, QgisPDSProductionLayer.LAYER_TYPE, "Current production layer")
        self.iface = iface
        self.setValid(True)

    def readXml(self, node):
        # custom properties
        print "ReadXlm"
        debug("[WORKER THREAD] readXml", 3)
        self.readCustomProperties(node)
        self.setExtent(QgsRectangle(-2003.34, -2003.34, 2003.34, 2003.34))
        return True

    def writeXml(self, node, doc):
        element = node.toElement()
        # write plugin layer type to project  (essential to be read from project)
        element.setAttribute("type", "plugin")
        element.setAttribute("name", QgisPDSProductionLayer.LAYER_TYPE);
        # custom properties

        return True

    def setLayerType(self, layerType):
        qDebug(" setLayerType: %s" % layerType.layerTypeName)
        self.layerType = layerType
        self.setCustomProperty(OpenlayersLayer.LAYER_PROPERTY, layerType.layerTypeName)
        coordRefSys = self.layerType.coordRefSys(None)  # FIXME
        self.setCrs(coordRefSys)
        #TODO: get extent from layer type
        self.setExtent(QgsRectangle(-20037508.34, -20037508.34, 20037508.34, 20037508.34))

    def createMapRenderer(self, context):
        return CurrentProdRenderer(self, context)