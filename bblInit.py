# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from QgisPDS.utils import *
from collections import namedtuple


FLUID_CODE = namedtuple('FLUID_CODE', ['name', 'code', 'backColor', 'lineColor', 'labelColor'])
Production = namedtuple('Production', ['volumeVals', 'massVals', 'stadat', 'enddat', 'days'])
# ProductionWell = namedtuple('ProductionWell', ['sldnid', 'name', 'liftMethod', 'prods'])
LiftMethod = namedtuple('LiftMethod', ['isFlowing', 'isPump'])
BBL_CONVERTED_SYMBOL = namedtuple('BBL_CONVERTED_SYMBOL', ['initialWellRole', 'currentWellRole', 'wellStatus', 'symbol'])
BBL_SYMBOL = namedtuple('BBL_SYMBOL', ['wellRole', 'wellStatus', 'symbol'])
SYMBOL = namedtuple('SYMBOL', ['wellRole', 'symbol'])
StandardDiagram = namedtuple('StandardDiagram', ['name', 'scale', 'unitsType', 'units', 'fluids'])

class MyStruct(object):
    def __init__(self,**kwargs):
        self.__dict__.update(kwargs)

class NAMES(MyStruct):
    name = None
    selected = False

class ProductionWell(MyStruct):
    sldnid = 0
    name = ''
    liftMethod = ''
    prods = []
    reservoirState = 'NO_MOVING'
    movingReservoir = ''


class bblInit:

    fluidCodes = [  MyStruct(name= QCoreApplication.translate('bblInit', u'Crude oil'), code="crude oil",
                        backColor=QColor(Qt.darkRed),   lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Natural gas'), code="natural gas",
                        backColor=QColor(Qt.darkYellow), lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Produced water'), code="produced water",
                        backColor=QColor(Qt.blue),      lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Condensate'), code="condensate",
                        backColor=QColor(Qt.gray),      lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Injected gas'), code="injected gas",
                        backColor=QColor(Qt.yellow),    lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Injected water'), code="injected water",
                        backColor=QColor(0, 160, 230),  lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Lift gas'), code="lift gas",
                        backColor=QColor(Qt.yellow),    lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Free gas'), code="free gas",
                        backColor=QColor(Qt.darkYellow), lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                        inPercent=0)]

    bblLiftMethods =  {u"flowing": LiftMethod(True, False),
                            u"centrifugal pump": LiftMethod( False, True),
                            u"diaphragm pump": LiftMethod( False, True),
                            u"sucker-rod pump": LiftMethod( False, True),
                            u"jet pump": LiftMethod( False, True),
                            u"plunger pump": LiftMethod( False, True),
                            u"gas lift": LiftMethod( False, False),
                            u"spiral pump": LiftMethod( False, True),
                            u"RED pump": LiftMethod( False, True)}

    standardDiagramms = {
                    "1LIQUID_PRODUCTION": StandardDiagram(name=u"Диаграмма жидкости", scale=300000, unitsType=0, units=0, fluids=[1, 0, 1, 0, 0, 0, 0, 0]),
                    "2LIQUID_INJECTION": StandardDiagram(name=u"Диаграмма закачки", scale=300000, unitsType=0, units=0, fluids=[0, 0, 0, 0, 1, 1, 0, 0]),
                    "3GAS_PRODUCTION": StandardDiagram(name=u"Диагмамма газа", scale=3000000, unitsType=1, units=0, fluids=[0, 1, 0, 0, 0, 0, 0, 0]),
                    "4CONDENSAT_PRODUCTION": StandardDiagram(name=u"Диаграмма конденсата", scale=3000000, unitsType=0, units=0, fluids=[0, 0, 0, 1, 0, 0, 0, 0])
                }

    bblSymbols = [
            BBL_SYMBOL("oil producing", "active stock", 81),
            BBL_SYMBOL("water injecting", "active stock", 83),
            BBL_SYMBOL("gas producing", "active stock", 220),
            BBL_SYMBOL("water-supply", "active stock", 103),
            BBL_SYMBOL("water absorbing", "active stock", 105),
            BBL_SYMBOL("oil producing", "suspended stock", 147),
            BBL_SYMBOL("water injecting", "suspended stock", 152),
            BBL_SYMBOL("gas producing", "suspended stock", 221),
            BBL_SYMBOL("water-supply", "suspended stock", 230),
            BBL_SYMBOL("water absorbing", "suspended stock", 239),
            BBL_SYMBOL("oil producing", "waiting completion stock", 117),
            BBL_SYMBOL("water injecting", "waiting completion stock", 121),
            BBL_SYMBOL("gas producing", "waiting completion stock", 222),
            BBL_SYMBOL("water-supply", "waiting completion stock", 231),
            BBL_SYMBOL("water absorbing", "waiting completion stock", 240),
            BBL_SYMBOL("oil producing", "completion stock", 118),
            BBL_SYMBOL("water injecting", "completion stock", 122),
            BBL_SYMBOL("gas producing", "completion stock", 223),
            BBL_SYMBOL("water-supply", "completion stock", 232),
            BBL_SYMBOL("water absorbing", "completion stock", 241),
            BBL_SYMBOL("oil producing", "QC stock", 85),
            BBL_SYMBOL("water injecting", "QC stock", 85),
            BBL_SYMBOL("gas producing", "QC stock", 85),
            BBL_SYMBOL("water-supply", "QC stock", 85),
            BBL_SYMBOL("water absorbing", "QC stock", 85),
            BBL_SYMBOL("oil producing", "piezometric stock", 89),
            BBL_SYMBOL("water injecting", "piezometric stock", 89),
            BBL_SYMBOL("gas producing", "piezometric stock", 89),
            BBL_SYMBOL("water-supply", "piezometric stock", 89),
            BBL_SYMBOL("water absorbing", "piezometric stock", 89),
            BBL_SYMBOL("oil producing", "conservation stock", 145),
            BBL_SYMBOL("water injecting", "conservation stock", 150),
            BBL_SYMBOL("gas producing", "conservation stock", 224),
            BBL_SYMBOL("water-supply", "conservation stock", 233),
            BBL_SYMBOL("water absorbing", "conservation stock", 242),
            BBL_SYMBOL("oil producing", "abandonment stock", 181),
            BBL_SYMBOL("water injecting", "abandonment stock", 185),
            BBL_SYMBOL("gas producing", "abandonment stock", 225),
            BBL_SYMBOL("water-supply", "abandonment stock", 234),
            BBL_SYMBOL("water absorbing", "abandonment stock", 243),
            BBL_SYMBOL("oil producing", "waiting abandonment stock", 181),
            BBL_SYMBOL("water injecting", "waiting abandonment stock", 185),
            BBL_SYMBOL("gas producing", "waiting abandonment stock", 225),
            BBL_SYMBOL("water-supply", "waiting abandonment stock", 235),
            BBL_SYMBOL("water absorbing", "waiting abandonment stock", 244),
            BBL_SYMBOL("oil producing", "inactive stock", 202),
            BBL_SYMBOL("water injecting", "inactive stock", 203),
            BBL_SYMBOL("gas producing", "inactive stock", 227),
            BBL_SYMBOL("water-supply", "inactive stock", 237),
            BBL_SYMBOL("water absorbing", "inactive stock", 246),
            BBL_SYMBOL("oil producing", "proposed stock", 82),
            BBL_SYMBOL("water injecting", "proposed stock", 84),
            BBL_SYMBOL("gas producing", "proposed stock", 228),
            BBL_SYMBOL("water-supply", "proposed stock", 104),
            BBL_SYMBOL("water absorbing", "proposed stock", 106),
            BBL_SYMBOL("oil producing", "drilling stock", 116),
            BBL_SYMBOL("water injecting", "drilling stock", 120),
            BBL_SYMBOL("gas producing", "drilling stock", 229),
            BBL_SYMBOL("water-supply", "drilling stock", 238),
            BBL_SYMBOL("water absorbing", "drilling stock", 247),
            BBL_SYMBOL("oil producing", "test stock", 126),
            BBL_SYMBOL("water injecting", "test stock", 126),
            BBL_SYMBOL("gas producing", "test stock", 126),
            BBL_SYMBOL("water-supply", "test stock", 126),
            BBL_SYMBOL("water absorbing", "test stock", 126),
            BBL_SYMBOL("oil producing", "exploration abandonment stock", 188),
            BBL_SYMBOL("water injecting", "exploration abandonment stock", 188),
            BBL_SYMBOL("gas producing", "exploration abandonment stock", 188),
            BBL_SYMBOL("water-supply", "exploration abandonment stock", 188),
            BBL_SYMBOL("water absorbing", "exploration abandonment stock", 188)]

    bblConvertedSymbols = [
            BBL_CONVERTED_SYMBOL("water injecting", "oil producing", "active stock", 211),      #producing well converted from injecting
            BBL_CONVERTED_SYMBOL("water injecting", "oil producing", "suspended stock", 211),
            BBL_CONVERTED_SYMBOL("oil producing", "water injecting", "active stock", 212),
            BBL_CONVERTED_SYMBOL("oil producing", "water injecting", "suspended stock", 212)]   #producing well converted from injecting

    unit_to_mult = {
        0: 1,       # кг
        1: 1000.0,  #г
        2: 10**-3,  #tonn
        3: 10**-6,  #t. tonn
        4: 1.0/907.18474, #UK ton(short)
        5: 1.0/1016.0469088, #UK ton(long)
        10: 1,      #m3
        11: 10**3,  #dm3
        12: 10**6,  #sm3
        13: 10**-9,  #km3
        14: 10**-3,  #1000m3
        15: 10**-6  #1000000m3
        
    }

    def __init__(self):
        pass

    @staticmethod
    def isProductionLayer(layer):
        return (layer.customProperty("qgis_pds_type") == "pds_current_production" or 
                layer.customProperty("qgis_pds_type") == "pds_cumulative_production")

    @staticmethod
    def isWellLayer(layer):
        return (layer.customProperty("qgis_pds_type") == "pds_wells")

