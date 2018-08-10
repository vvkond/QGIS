# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from QgisPDS.utils import *
from collections import namedtuple

try:
    from PyQt4.QtCore import QString
except ImportError:
    QString = type("")


FLUID_CODE = namedtuple('FLUID_CODE', ['name', 'code', 'backColor', 'lineColor', 'labelColor'])
Production = namedtuple('Production', ['volumeVals', 'massVals', 'stadat', 'enddat', 'days'])
# ProductionWell = namedtuple('ProductionWell', ['sldnid', 'name', 'liftMethod', 'prods'])
LiftMethod = namedtuple('LiftMethod', ['isFlowing', 'isPump'])
BBL_CONVERTED_SYMBOL = namedtuple('BBL_CONVERTED_SYMBOL', ['initialWellRole', 'currentWellRole', 'wellStatus', 'symbol', 'wellRoleTr'])
BBL_SYMBOL = namedtuple('BBL_SYMBOL', ['wellRole', 'wellStatus', 'symbol', 'wellRoleTr'])
SYMBOL = namedtuple('SYMBOL', ['wellRole', 'symbol'])
StandardDiagram = namedtuple('StandardDiagram', ['name', 'scale', 'unitsType', 'units', 'fluids'])
OLD_NEW_FIELDNAMES = [u'BubbleFields', u'bubbleflds']

class MyStruct(object):
    def __init__(self,**kwargs):
        self.__dict__.update(kwargs)

class NAMES(MyStruct):
    name = None
    selected = False

class ProdDebit(MyStruct):
    massValue = 0
    volValue = 0
    massDebitDate = ''
    volDebitDate = ''

class ProductionWell(MyStruct):
    sldnid = 0
    name = ''
    liftMethod = ''
    prods = []
    reservoirState = 'NO_MOVING'
    movingReservoir = ''
    maxDebits = []


class bblInit:

    fluidCodes = [  MyStruct(name= QCoreApplication.translate('bblInit', u'Crude oil'),
                                 code="oil", componentId="crude oil", alias=u'Сырая нефть',
                                 backColor=QColor(Qt.darkRed),   lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                 inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Natural gas'),
                                 code="ngas", componentId="natural gas", alias=u'Природный газ',
                                 backColor=QColor(Qt.darkYellow), lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                 inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Produced water'),
                                code="pw", componentId="produced water", alias=u'Добыча вода',
                                backColor=QColor(Qt.blue),      lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Condensate'),
                                code="cond", componentId="condensate", alias=u'Конденсат',
                                backColor=QColor(Qt.gray),      lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Injected gas'),
                                code="igas", componentId="injected gas", alias=u'Закачка газа',
                                backColor=QColor(Qt.yellow),    lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Injected water'),
                                code="iw", componentId="injected water", alias=u'Закачка воды',
                                backColor=QColor(0, 160, 230),  lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Lift gas'),
                                code="lgas", componentId="lift gas", alias=u'Газлифт',
                                backColor=QColor(Qt.yellow),    lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Free gas'),
                                code="fgas", componentId="free gas", alias=u'Свободный газ',
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
            BBL_SYMBOL("unknown well", "active stock", 70,
                       QCoreApplication.translate('bblInit', u'unknown well')),
            BBL_SYMBOL("oil producing", "active stock", 81,
                       QCoreApplication.translate('bblInit', u'oil producing active stock')),
            BBL_SYMBOL("water injecting", "active stock", 83,
                       QCoreApplication.translate('bblInit', u'water injecting active stock')),
            BBL_SYMBOL("gas producing", "active stock", 220,
                       QCoreApplication.translate('bblInit', u'gas producing active stock')),
            BBL_SYMBOL("water-supply", "active stock", 103,
                       QCoreApplication.translate('bblInit', u'water-supply active stock')),
            BBL_SYMBOL("water absorbing", "active stock", 105,
                       QCoreApplication.translate('bblInit', u'water absorbing active stock')),
            BBL_SYMBOL("oil producing", "suspended stock", 147,
                       QCoreApplication.translate('bblInit', u'oil producing suspended stock')),
            BBL_SYMBOL("water injecting", "suspended stock", 152,
                       QCoreApplication.translate('bblInit', u'water injecting suspended stock')),
            BBL_SYMBOL("gas producing", "suspended stock", 221,
                       QCoreApplication.translate('bblInit', u'gas producing suspended stock')),
            BBL_SYMBOL("water-supply", "suspended stock", 230,
                       QCoreApplication.translate('bblInit', u'water-supply suspended stock')),
            BBL_SYMBOL("water absorbing", "suspended stock", 239,
                       QCoreApplication.translate('bblInit', u'water absorbing suspended stock')),
            BBL_SYMBOL("oil producing", "waiting completion stock", 117,
                       QCoreApplication.translate('bblInit', u'oil producing waiting completion stock')),
            BBL_SYMBOL("water injecting", "waiting completion stock", 121,
                       QCoreApplication.translate('bblInit', u'water injecting waiting completion stock')),
            BBL_SYMBOL("gas producing", "waiting completion stock", 222,
                       QCoreApplication.translate('bblInit', u'gas producing waiting completion stock')),
            BBL_SYMBOL("water-supply", "waiting completion stock", 231,
                       QCoreApplication.translate('bblInit', u'water-supply waiting completion stock')),
            BBL_SYMBOL("water absorbing", "waiting completion stock", 240,
                       QCoreApplication.translate('bblInit', u'water absorbing waiting completion stock')),
            BBL_SYMBOL("oil producing", "completion stock", 118,
                       QCoreApplication.translate('bblInit', u'oil producing completion stock')),
            BBL_SYMBOL("water injecting", "completion stock", 122,
                       QCoreApplication.translate('bblInit', u'water injecting completion stock')),
            BBL_SYMBOL("gas producing", "completion stock", 223,
                       QCoreApplication.translate('bblInit', u'gas producing completion stock')),
            BBL_SYMBOL("water-supply", "completion stock", 232,
                       QCoreApplication.translate('bblInit', u'water-supply completion stock')),
            BBL_SYMBOL("water absorbing", "completion stock", 241,
                       QCoreApplication.translate('bblInit', u'water absorbing completion stock')),
            BBL_SYMBOL("oil producing", "QC stock", 85,
                       QCoreApplication.translate('bblInit', u'oil producing QC stock')),
            BBL_SYMBOL("water injecting", "QC stock", 85,
                       QCoreApplication.translate('bblInit', u'water injecting QC stock')),
            BBL_SYMBOL("gas producing", "QC stock", 85,
                       QCoreApplication.translate('bblInit', u'gas producing QC stock')),
            BBL_SYMBOL("water-supply", "QC stock", 85,
                       QCoreApplication.translate('bblInit', u'water-supply QC stock')),
            BBL_SYMBOL("water absorbing", "QC stock", 85,
                       QCoreApplication.translate('bblInit', u'water absorbing QC stock')),
            BBL_SYMBOL("oil producing", "piezometric stock", 89,
                       QCoreApplication.translate('bblInit', u'oil producing piezometric stock')),
            BBL_SYMBOL("water injecting", "piezometric stock", 89,
                       QCoreApplication.translate('bblInit', u'water injecting piezometric stock')),
            BBL_SYMBOL("gas producing", "piezometric stock", 89,
                       QCoreApplication.translate('bblInit', u'gas producing piezometric stock')),
            BBL_SYMBOL("water-supply", "piezometric stock", 89,
                       QCoreApplication.translate('bblInit', u'water-supply piezometric stock')),
            BBL_SYMBOL("water absorbing", "piezometric stock", 89,
                       QCoreApplication.translate('bblInit', u'water absorbing piezometric stock')),
            BBL_SYMBOL("oil producing", "conservation stock", 145,
                       QCoreApplication.translate('bblInit', u'oil producing conservation stock')),
            BBL_SYMBOL("water injecting", "conservation stock", 150,
                       QCoreApplication.translate('bblInit', u'water injecting conservation stock')),
            BBL_SYMBOL("gas producing", "conservation stock", 224,
                       QCoreApplication.translate('bblInit', u'gas producing conservation stock')),
            BBL_SYMBOL("water-supply", "conservation stock", 233,
                       QCoreApplication.translate('bblInit', u'water-supply conservation stock')),
            BBL_SYMBOL("water absorbing", "conservation stock", 242,
                       QCoreApplication.translate('bblInit', u'water absorbing conservation stock')),
            BBL_SYMBOL("oil producing", "abandonment stock", 181,
                       QCoreApplication.translate('bblInit', u'oil producing abandonment stock')),
            BBL_SYMBOL("water injecting", "abandonment stock", 185,
                       QCoreApplication.translate('bblInit', u'water injecting abandonment stock')),
            BBL_SYMBOL("gas producing", "abandonment stock", 225,
                       QCoreApplication.translate('bblInit', u'gas producing abandonment stock')),
            BBL_SYMBOL("water-supply", "abandonment stock", 234,
                       QCoreApplication.translate('bblInit', u'water-supply abandonment stock')),
            BBL_SYMBOL("water absorbing", "abandonment stock", 243,
                       QCoreApplication.translate('bblInit', u'water absorbing abandonment stock')),
            BBL_SYMBOL("oil producing", "waiting abandonment stock", 181,
                       QCoreApplication.translate('bblInit', u'oil producing waiting abandonment stock')),
            BBL_SYMBOL("water injecting", "waiting abandonment stock", 185,
                       QCoreApplication.translate('bblInit', u'water injecting waiting abandonment stock')),
            BBL_SYMBOL("gas producing", "waiting abandonment stock", 225,
                       QCoreApplication.translate('bblInit', u'gas producing waiting abandonment stock')),
            BBL_SYMBOL("water-supply", "waiting abandonment stock", 235,
                       QCoreApplication.translate('bblInit', u'water-supply waiting abandonment stock')),
            BBL_SYMBOL("water absorbing", "waiting abandonment stock", 244,
                       QCoreApplication.translate('bblInit', u'water absorbing waiting abandonment stock')),
            BBL_SYMBOL("oil producing", "inactive stock", 202,
                       QCoreApplication.translate('bblInit', u'oil producing inactive stock')),
            BBL_SYMBOL("water injecting", "inactive stock", 203,
                       QCoreApplication.translate('bblInit', u'water injecting inactive stock')),
            BBL_SYMBOL("gas producing", "inactive stock", 227,
                       QCoreApplication.translate('bblInit', u'gas producing inactive stock')),
            BBL_SYMBOL("water-supply", "inactive stock", 237,
                       QCoreApplication.translate('bblInit', u'water-supply inactive stock')),
            BBL_SYMBOL("water absorbing", "inactive stock", 246,
                       QCoreApplication.translate('bblInit', u'water absorbing inactive stock')),
            BBL_SYMBOL("oil producing", "proposed stock", 82,
                       QCoreApplication.translate('bblInit', u'oil producing proposed stock')),
            BBL_SYMBOL("water injecting", "proposed stock", 84,
                       QCoreApplication.translate('bblInit', u'water injecting proposed stock')),
            BBL_SYMBOL("gas producing", "proposed stock", 228,
                       QCoreApplication.translate('bblInit', u'gas producing proposed stock')),
            BBL_SYMBOL("water-supply", "proposed stock", 104,
                       QCoreApplication.translate('bblInit', u'water-supply proposed stock')),
            BBL_SYMBOL("water absorbing", "proposed stock", 106,
                       QCoreApplication.translate('bblInit', u'water absorbing proposed stock')),
            BBL_SYMBOL("oil producing", "drilling stock", 116,
                       QCoreApplication.translate('bblInit', u'oil producing drilling stock')),
            BBL_SYMBOL("water injecting", "drilling stock", 120,
                       QCoreApplication.translate('bblInit', u'water injecting drilling stock')),
            BBL_SYMBOL("gas producing", "drilling stock", 229,
                       QCoreApplication.translate('bblInit', u'gas producing drilling stock')),
            BBL_SYMBOL("water-supply", "drilling stock", 238,
                       QCoreApplication.translate('bblInit', u'water-supply drilling stock')),
            BBL_SYMBOL("water absorbing", "drilling stock", 247,
                       QCoreApplication.translate('bblInit', u'water absorbing drilling stock')),
            BBL_SYMBOL("oil producing", "test stock", 126,
                       QCoreApplication.translate('bblInit', u'oil producing test stock')),
            BBL_SYMBOL("water injecting", "test stock", 126,
                       QCoreApplication.translate('bblInit', u'water injecting test stock')),
            BBL_SYMBOL("gas producing", "test stock", 126,
                       QCoreApplication.translate('bblInit', u'gas producing test stock')),
            BBL_SYMBOL("water-supply", "test stock", 126,
                       QCoreApplication.translate('bblInit', u'water-supply test stock')),
            BBL_SYMBOL("water absorbing", "test stock", 126,
                       QCoreApplication.translate('bblInit', u'water absorbing test stock')),
            BBL_SYMBOL("oil producing", "exploration abandonment stock", 188,
                       QCoreApplication.translate('bblInit', u'oil producing exploration abandonment stock')),
            BBL_SYMBOL("water injecting", "exploration abandonment stock", 188,
                       QCoreApplication.translate('bblInit', u'water injecting exploration abandonment stock')),
            BBL_SYMBOL("gas producing", "exploration abandonment stock", 188,
                       QCoreApplication.translate('bblInit', u'gas producing exploration abandonment stock')),
            BBL_SYMBOL("water-supply", "exploration abandonment stock", 188,
                       QCoreApplication.translate('bblInit', u'water-supply exploration abandonment stock')),
            BBL_SYMBOL("water absorbing", "exploration abandonment stock", 188,
                       QCoreApplication.translate('bblInit', u'water absorbing exploration abandonment stock'))]

    bblConvertedSymbols = [
            BBL_CONVERTED_SYMBOL("water injecting", "oil producing", "active stock", 211,
                                 QCoreApplication.translate('bblInit', u'water injecting oil producing active stock')),      #producing well converted from injecting
            BBL_CONVERTED_SYMBOL("water injecting", "oil producing", "suspended stock", 211,
                                 QCoreApplication.translate('bblInit', u'water injecting oil producing suspended stock')),
            BBL_CONVERTED_SYMBOL("oil producing", "water injecting", "active stock", 212,
                                 QCoreApplication.translate('bblInit', u'oil producing water injecting active stock')),
            BBL_CONVERTED_SYMBOL("oil producing", "water injecting", "suspended stock", 212,
                                 QCoreApplication.translate('bblInit', u'oil producing water injecting suspended stock'))]   #producing well converted from injecting

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
        return (layer.customProperty("qgis_pds_type") == "pds_wells" or
                layer.customProperty("qgis_pds_type") == "pds_well_deviations")

    @staticmethod
    def attrFluidVolume(fluidCode):
        return fluidCode + u"vol"

    @staticmethod
    def attrFluidMass(fluidCode):
        return fluidCode + u"mas"

    @staticmethod
    def attrFluidMaxDebitMass(fluidCode):
        return fluidCode + u"max_m"

    @staticmethod
    def attrFluidMaxDebitDateMass(fluidCode):
        return fluidCode + u"maxd_m"

    @staticmethod
    def attrFluidMaxDebitVol(fluidCode):
        return fluidCode + u"max_v"

    @staticmethod
    def attrFluidMaxDebitDateVol(fluidCode):
        return fluidCode + u"maxd_v"

    @staticmethod
    def attrFluidMassOld(fluidCode):
        return fluidCode + u" (mass)"

    @staticmethod
    def attrFluidVolumeOld(fluidCode):
        return fluidCode + u" (volume)"

    @staticmethod
    def aliasFluidVolume(fluidCode):
        return fluidCode + u" (объем)"

    @staticmethod
    def aliasFluidMass(fluidCode):
        return fluidCode + u" (масса)"

    @staticmethod
    def aliasFluidMaxDebitMass(fluidCode):
        return fluidCode + u" (макс. дебит по массе)"

    @staticmethod
    def aliasFluidMaxDebitDateMass(fluidCode):
        return fluidCode + u" (дата макс. дебита по массе)"

    @staticmethod
    def aliasFluidMaxDebitVol(fluidCode):
        return fluidCode + u" (макс. дебит по объему)"

    @staticmethod
    def aliasFluidMaxDebitDateVol(fluidCode):
        return fluidCode + u" (дата макс. дебита по объему)"

    @staticmethod
    def updateOldProductionStructure(layer):
        needCopyData = False
        provider = layer.dataProvider()

        def copyValue(feature, newName, oldName, alias):
            idx = layer.fieldNameIndex(newName)
            if idx >= 0:
                val = feature.attribute(oldName)
                if val:
                    layer.changeAttributeValue(feature.id(), idx, float(val))
                layer.addAttributeAlias(idx, alias)

        with edit(layer):
            for fl in bblInit.fluidCodes:
                #Check mass fields
                newName = bblInit.attrFluidMass(fl.code)
                oldName = bblInit.attrFluidMassOld(fl.componentId)
                newIdx = layer.fieldNameIndex(newName)
                if newIdx < 0:
                    provider.addAttributes([QgsField(newName, QVariant.Double, QString(""), 20, 5)])
                    needCopyData = True

                #Check volume fields
                newName = bblInit.attrFluidVolume(fl.code)
                oldName = bblInit.attrFluidVolumeOld(fl.componentId)
                newIdx = layer.fieldNameIndex(newName)
                if newIdx < 0:
                    provider.addAttributes([QgsField(newName, QVariant.Double, QString(""), 20, 5)])
                    needCopyData = True

                # Check max debit fields mass
                newName = bblInit.attrFluidMaxDebitMass(fl.code)
                newIdx = layer.fieldNameIndex(newName)
                if newIdx < 0:
                    provider.addAttributes([QgsField(newName, QVariant.Double, QString(""), 20, 5)])

                # Check max debit date fields mass
                newName = bblInit.attrFluidMaxDebitDateMass(fl.code)
                newIdx = layer.fieldNameIndex(newName)
                if newIdx < 0:
                    provider.addAttributes([QgsField(newName, QVariant.Date, QString(""), 50, 0)])

                # Check max debit fields volume
                newName = bblInit.attrFluidMaxDebitVol(fl.code)
                newIdx = layer.fieldNameIndex(newName)
                if newIdx < 0:
                    provider.addAttributes([QgsField(newName, QVariant.Double, QString(""), 20, 5)])

                # Check max debit date fields volume
                newName = bblInit.attrFluidMaxDebitDateVol(fl.code)
                newIdx = layer.fieldNameIndex(newName)
                if newIdx < 0:
                    provider.addAttributes([QgsField(newName, QVariant.Date, QString(""), 50, 0)])


        if needCopyData:
            with edit(layer):
                features = layer.getFeatures()
                for feature in features:
                    for fl in bblInit.fluidCodes:
                        #Copy mass fields
                        newName = bblInit.attrFluidMass(fl.code)
                        oldName = bblInit.attrFluidMassOld(fl.componentId)
                        alias = bblInit.aliasFluidMass(fl.alias)
                        copyValue(feature, newName, oldName, alias)
                        # idx = layer.fieldNameIndex(newName)
                        # if idx >= 0:
                        #     val = feature.attribute(oldName)
                        #     if val:
                        #         layer.changeAttributeValue(feature.id(), idx, float(val))
                        #     layer.addAttributeAlias(idx, alias)

                        #Copy volume fields
                        newName = bblInit.attrFluidVolume(fl.code)
                        oldName = bblInit.attrFluidVolumeOld(fl.componentId)
                        alias = bblInit.aliasFluidVolume(fl.alias)
                        copyValue(feature, newName, oldName, alias)
                        # idx = layer.fieldNameIndex(newName)
                        # if idx >= 0:
                        #     layer.changeAttributeValue(feature.id(), idx, float(feature.attribute(oldName)))
                        #     layer.addAttributeAlias(idx, alias)

    @staticmethod
    def setAliases(layer):
        features = layer.getFeatures()
        for feature in features:
            for fl in bblInit.fluidCodes:
                # mass fields
                newName = bblInit.attrFluidMass(fl.code)
                alias = bblInit.aliasFluidMass(fl.alias)
                idx = layer.fieldNameIndex(newName)
                if idx >= 0:
                    layer.addAttributeAlias(idx, alias)

                # volume fields
                newName = bblInit.attrFluidVolume(fl.code)
                alias = bblInit.aliasFluidVolume(fl.alias)
                idx = layer.fieldNameIndex(newName)
                if idx >= 0:
                    layer.addAttributeAlias(idx, alias)

                # Max debit fields mass
                newName = bblInit.attrFluidMaxDebitMass(fl.code)
                alias = bblInit.aliasFluidMaxDebitMass(fl.alias)
                idx = layer.fieldNameIndex(newName)
                if idx >= 0:
                    layer.addAttributeAlias(idx, alias)

                # Max debit date fields mass
                newName = bblInit.attrFluidMaxDebitDateMass(fl.code)
                alias = bblInit.aliasFluidMaxDebitDateMass(fl.alias)
                idx = layer.fieldNameIndex(newName)
                if idx >= 0:
                    layer.addAttributeAlias(idx, alias)

                # Max debit fields volume
                newName = bblInit.attrFluidMaxDebitVol(fl.code)
                alias = bblInit.aliasFluidMaxDebitVol(fl.alias)
                idx = layer.fieldNameIndex(newName)
                if idx >= 0:
                    layer.addAttributeAlias(idx, alias)

                # Max debit date fields volume
                newName = bblInit.attrFluidMaxDebitDateVol(fl.code)
                alias = bblInit.aliasFluidMaxDebitDateVol(fl.alias)
                idx = layer.fieldNameIndex(newName)
                if idx >= 0:
                    layer.addAttributeAlias(idx, alias)





