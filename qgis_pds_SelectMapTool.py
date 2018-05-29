# -*- coding: utf-8 -*-

from qgis.PyQt import uic, QtCore, QtGui
from PyQt4.QtCore import *
import qgis
from qgis.core import *
from qgis.gui import *

class QgisPDSSelectMapTool(QgsMapToolEmitPoint):

    finished = pyqtSignal(list, str, str)

    def __init__(self, canvas, layer=None):
        self.layer = layer
        self.canvas = canvas
        self.exeName = ''
        self.appArgs = ''
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.rubberBand = QgsRubberBand(self.canvas, QGis.WKBLineString)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setWidth(1)
        self.reset()
        self.features = []

        if self.layer:
            self.layer.removeSelection()

    def setArgs(self, exeName, appArgs, layer):
        self.exeName = exeName
        self.appArgs = appArgs
        self.layer = layer

    def setLayer(self, layer):
        self.reset()
        self.layer = layer

    def reset(self):
        self.startPoint = self.endPoint = None
        self.rubberBand.reset(True)
        self.features = []
        if self.layer:
            self.layer.removeSelection()

    def canvasPressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.startPoint = self.toMapCoordinates(e.pos())
            self.endPoint = self.startPoint

            pt1 = self.toMapCoordinates(QPoint(e.pos().x()-5, e.pos().y() - 5))
            pt2 = self.toMapCoordinates(QPoint(e.pos().x() + 5, e.pos().y() + 5))
            rect = QgsRectangle(pt1, pt2)
            it = self.layer.getFeatures(QgsFeatureRequest(rect))
            ids1 = [i.id() for i in self.features]
            for f in it:
                if f.id() in ids1:
                    ids1.remove(f.id())
                    self.features = [ f1 for f1 in self.features if f1.id() != f.id() ]
                else:
                    self.features.append(f)
                    ids1.append(f.id())

            self.layer.setSelectedFeatures( ids1 )

            self.showRect(self.endPoint)
        elif e.button() == Qt.RightButton:
            self.finished.emit(self.features, self.exeName, self.appArgs)
            self.reset()

    def canvasReleaseEvent(self, e):
        pass

    def canvasMoveEvent(self, e):
        self.endPoint = self.toMapCoordinates(e.pos())
        self.showRect(self.endPoint)

    def getFeaturePoint(self, geom):
        try:
            t = geom.wkbType()
            if t == QGis.WKBPoint:
                return geom.asPoint()
            elif t == QGis.WKBMultiPoint:
                mpt = geom.asMultiPoint()
                if len(mpt) > 0:
                    return mpt[len(mpt)-1]
            elif t == QGis.WKBLineString:
                mpt = geom.asPolyline()
                if len(mpt) > 0:
                    return mpt[len(mpt)-1]
            elif t == QGis.WKBPolygon:
                mpt = geom.asPolygon()
                if len(mpt) > 0:
                    line = mpt[0]
                    if len(line) > 0:
                        return line[len(line) - 1]
        except:
            pass
        return None

    def showRect(self, endPoint):
        self.rubberBand.reset()

        for f in self.features:
            point1 = self.getFeaturePoint(f.geometry())
            if point1:
                self.rubberBand.addPoint(point1, False)

        point3 = QgsPoint(endPoint.x(), endPoint.y())
        self.rubberBand.addPoint(point3, True)

        self.rubberBand.show()

    def activate(self):
        self.canvas.setCursor(Qt.CrossCursor)
        self.reset()
        self.emit(SIGNAL("activated()"))


    def deactivate(self):
        self.emit(SIGNAL("deactivated()"))
        self.rubberBand.reset()