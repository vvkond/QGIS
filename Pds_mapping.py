##PDS=group
##Input_pressure=vector
##Vector_fields=field Input_pressure
##Input_contour=vector
##Contour_fields=field Input_contour
##Output_layer=output vector

from qgis.core import *
from PyQt4.QtCore import *
from processing.tools.vector import VectorWriter

vector = processing.getObject(Input_pressure)
contour = processing.getObject(Input_contour)

fields = [QgsField('distance', QVariant.Double)]
writer = VectorWriter(Output_layer, None, fields, QGis.WKBLineString, vector.crs())

geometryType = vector.geometryType()
iter = vector.getFeatures()
for feature in iter:    
    print feature.geometry(), feature[Vector_fields]
    
del writer