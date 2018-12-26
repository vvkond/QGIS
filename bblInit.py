# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from QgisPDS.utils import *
from qgis.core import QgsField 
from collections import namedtuple
from utils import edit_layer, cached_property

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



STYLE_DIR='styles'

USER_PROD_STYLE_DIR='user_prod_styles'
USER_FONDWELL_STYLE_DIR='user_fondwell_styles'
USER_FONDOBJ_STYLE_DIR='user_fondobject_styles'
USER_PROD_STYLE_DIR='user_prod_styles'
USER_PROD_RENDER_STYLE_DIR='user_prod_render_styles'
USER_DEVI_STYLE_DIR='user_devi_styles'
USER_WELL_STYLE_DIR='user_well_styles'
USER_FAULT_STYLE_DIR="user_fault_styles"
USER_CONTOUR_STYLE_DIR="user_contour_styles"
USER_POLYGON_STYLE_DIR="user_polygon_styles"
USER_SURF_STYLE_DIR="user_surface_styles"

PROD_RENDER_STYLE='prod_render'
PROD_STYLE='prod'
DEVI_STYLE='devi'
WELL_STYLE='well'
FAULT_STYLE="fault"
CONTOUR_STYLE="contour"
POLYGON_STYLE="polygon"
SURF_SYLE="surface"

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
    wRole="unknown"
    wStatus="unknown"
    wStatusInfo=""
    wStatusReason=""
    wInitialRole="unknown"


TableUnit = namedtuple('TableUnit', ['table', 'unit'])
#===============================================================================
# not used. Planed for QgsField.type association
#===============================================================================
FIELD_AND_TYPES={"string":QVariant.String
             ,"int":QVariant.Int
             ,"double":QVariant.Double
             ,"date":QVariant.String
             }
#===============================================================================
# 
#===============================================================================
class AttributeField():
    """
        @info: class for store one field info and return it as QgsField or as MemoryLayer field
        @see: https://qgis.org/api/classQgsField.html#ac0290b01ad74bb167dd0170775b5be47
    """
    field=None
    def __init__(self
                        ,field_name=None
                        ,field_type=None    # char, varchar, text, int, serial, double
                        ,comment=None
                        ,len=0
                        ,prec=0
                        ,alias=""
                 ):
        self.field=QgsField(name=field_name
                        #, type= FIELD_TYPES[self.field_type]
                        , typeName=field_type  # char, varchar, text, int, serial, double
                        , len=len
                        , prec=prec
                        , comment=comment
                        #, subType
                        )
        if alias is not None:self.field.setAlias(alias)        
    @cached_property
    def name(self):
        return self.field.name()
    @cached_property
    def memoryfield(self):
        return '&field={}:{}'.format(self.field.name(),self.field.typeName())
#===============================================================================
# 
#===============================================================================
class Fields:
    """
         @info: store all fields for layers. Import it when define fields/columns for layer
    """
    WellId =           AttributeField( field_name=u'well_id'    ,field_type="string" )
    Latitude =         AttributeField( field_name=u'latitude'   ,field_type="double" )
    Longitude =        AttributeField( field_name=u'longitude'  ,field_type="double" ) 
    Days =             AttributeField( field_name=u'days'       ,field_type="double" )
    Sldnid =           AttributeField( field_name=u'sldnid'     ,field_type="int"    )
    Api =              AttributeField( field_name=u'api'        ,field_type="string" )
    Operator =         AttributeField( field_name=u'operator'   ,field_type="string" )
    Country =          AttributeField( field_name=u'country'    ,field_type="string" )
    Depth =            AttributeField( field_name=u'depth'      ,field_type="double" )
    ElevationPoint =   AttributeField( field_name=u'measuremen' ,field_type="string" )    
    EleationvDatum =   AttributeField( field_name=u'datum'      ,field_type="string" )    
    Elevation =        AttributeField( field_name=u'elevation'  ,field_type="double" )        
    OnOffShor =        AttributeField( field_name=u'on_offshor' ,field_type="string" )    
    SpudDate =         AttributeField( field_name=u'spud_date'  ,field_type="date"   )    
        
    SymbolId =         AttributeField( field_name=u'symbolid'   ,field_type="string" )
    Symbol =           AttributeField( field_name=u'symbolcode' ,field_type="integer")
    SymbolName =       AttributeField( field_name=u'symbolname' ,field_type="string" )
    
    TigWellSymbol =    AttributeField( field_name=u'symbol'     ,field_type="string" )    
    TigLatestWellState=AttributeField( field_name=u'status'     ,field_type="string" )

    WellRole =         AttributeField( field_name=u'wellrole'   ,field_type="string" )
    WellStatus =       AttributeField( field_name=u'wellstatus' ,field_type="string" )
    WellStatusReason = AttributeField( field_name=u'wsreason'   ,field_type="string" )
    WellStatusInfo =   AttributeField( field_name=u'wsinfo'     ,field_type="string" )
    WellInitRole =     AttributeField( field_name=u'initrole'   ,field_type="string" )
    LiftMethod =       AttributeField( field_name=u'liftmethod' ,field_type="string" )
    
    bubblesize =       AttributeField( field_name=u"bubblesize" ,field_type="double" )
    #bubblefields =     AttributeField( field_name=u'bubbleflds' ,field_type="string" )
    #labels =           AttributeField( field_name=u'bbllabels'  ,field_type="string" )
    scaletype =        AttributeField( field_name=u"scaletype"  ,field_type="string" )
    movingres =        AttributeField( field_name=u"movingres"  ,field_type="string" )
    resstate =         AttributeField( field_name=u"resstate"   ,field_type="string" )
    multiprod =        AttributeField( field_name=u"multiprod"  ,field_type="string" )
    
    startDate =        AttributeField( field_name=u'startdate'  ,field_type="date"   )

    IsGlobal =         AttributeField( field_name=u'global_pri' ,field_type="string" )    
    Owner    =         AttributeField( field_name=u'owner'      ,field_type="string" )    
    CreatedDT =        AttributeField( field_name=u'created'    ,field_type="DateTime")
    Project =          AttributeField( field_name=u'project'    ,field_type="string" )

    lablx =            AttributeField( field_name=u"lablx"      ,field_type="double" )
    lably =            AttributeField( field_name=u"lably"      ,field_type="double" )
    labloffx =         AttributeField( field_name=u"labloffx"   ,field_type="double" )
    labloffy =         AttributeField( field_name=u"labloffy"   ,field_type="double" )
    labloffset =       AttributeField( field_name=u"labloffset" ,field_type="double" )
    lablwidth =        AttributeField( field_name=u"lablwidth"  ,field_type="double" )
    lablcolor =        AttributeField( field_name=u"lablcol"    ,field_type="string" )    
    lablbuffcolor =    AttributeField( field_name=u"buflcol"    ,field_type="string" )    
    lablbuffwidth  =   AttributeField( field_name=u"bufwidth"   ,field_type="double" )
    lablfont =         AttributeField( field_name=u"font"       ,field_type="string" )    
        


    
FieldsForLabels=[
            Fields.lablx 
            ,Fields.lably       
            ,Fields.labloffx 
            ,Fields.labloffy    
            ,Fields.labloffset 
            ,Fields.lablwidth       
            ,Fields.lablcolor
            ,Fields.lablbuffcolor
            ,Fields.lablbuffwidth
            ,Fields.lablfont
            ]
    
FieldsWellLayer=[
            Fields.WellId
            ,Fields.Latitude
            ,Fields.Longitude
            ,Fields.Sldnid
            ,Fields.Api
            ,Fields.Operator
            ,Fields.Country
            ,Fields.Depth
            ,Fields.ElevationPoint
            ,Fields.Elevation
            ,Fields.EleationvDatum
            ,Fields.OnOffShor
            ,Fields.TigLatestWellState
            ,Fields.TigWellSymbol
            ,Fields.SpudDate
            ,Fields.IsGlobal
            ,Fields.Owner
            ,Fields.CreatedDT
            ,Fields.Project
            ]
    
#===============================================================================
# 
#===============================================================================
def set_QgsPalLayerSettings_datadefproperty(
                        palyr
                        ,prop
                       ,active=True
                       ,useExpr=False
                       ,expr=None
                       ,field=None
                       ):
    palyr.setDataDefinedProperty(prop, active, useExpr, expr, field)    
#===============================================================================
# 
#===============================================================================
def layer_to_labeled(layer_QgsPalLayerSettings):
    """
        @info: set property QgsPalLayerSettings of layer to enable EasyLabel
        @example:
                palyr = QgsPalLayerSettings()
                palyr.readFromLayer(layer)            #---read from layer
                palyr.fieldName = Fields.WellId.name  #---enable label by column
                palyr=layer_to_labeled(palyr)         #---enable EasyLabel
                palyr.writeToLayer(layer)             #---store to layer
        @see:
            https://qgis.org/api/2.18/classQgsPalLayerSettings.html
            https://qgis.org/api/2.18/classQgsRuleBasedRendererV2.html
        
    """
    from qgis.core import QgsPalLayerSettings
    palyr=layer_QgsPalLayerSettings    
    palyr.enabled = True
    palyr.placement = QgsPalLayerSettings.OverPoint
    palyr.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.OffsetXY
                                       , active=True, useExpr=True
                                       , expr='format(\'%1,%2\', "{}" , "{}")'.format(Fields.labloffx.name,Fields.labloffy.name)
                                       , field=None
                                       )
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.Size
                                       , active=True, useExpr=False
                                       , expr=None
                                       , field=Fields.lablwidth.name
                                       )
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.PositionX
                                       , active=True, useExpr=False
                                       , expr=None
                                       , field=Fields.lablx.name
                                       )
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.PositionY
                                       , active=True, useExpr=False
                                       , expr=None
                                       , field=Fields.lably.name
                                       )
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.Color
                                       , active=True, useExpr=False
                                       , expr=None
                                       , field=Fields.lablcolor.name
                                       )
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.Family
                                       , active=True, useExpr=False
                                       , expr=None
                                       , field=Fields.lablfont.name
                                       )
    
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.BufferDraw
                                       , active=True, useExpr=True
                                       , expr='"{}" is not Null'.format(Fields.lablbuffcolor.name)
                                       , field=None
                                       )
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.BufferColor
                                       , active=True, useExpr=False
                                       , expr=None
                                       , field=Fields.lablbuffcolor.name
                                       )
    set_QgsPalLayerSettings_datadefproperty(palyr, QgsPalLayerSettings.BufferSize
                                       , active=True, useExpr=False
                                       , expr=None
                                       , field=Fields.lablbuffwidth.name
                                       )
    palyr.labelOffsetInMapUnits = False
    return palyr    
#===============================================================================
# 
#===============================================================================
class bblInit:

    fluidCodes = [  MyStruct(name= QCoreApplication.translate('bblInit', u'Crude oil'),
                                 code="oil", componentId="crude oil", alias=u'Сырая нефть',
                                 backColor=QColor(Qt.darkRed),   lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                 inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_lq",   u"Volume"), 
                                    TableUnit(u"p_q_mass_basis", u"Mass")
                                ]                                 
                                ,subComponentIds=None 
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Natural gas'),
                                 code="ngas", componentId="natural gas", alias=u'Природный газ',
                                 backColor=QColor(Qt.darkYellow), lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                 inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_gas",  u"Volume"), 
                                ]                                 
                                ,subComponentIds=None
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Produced water'),
                                code="pw", componentId="produced water", alias=u'Добыча вода',
                                backColor=QColor(Qt.blue),      lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_lq",   u"Volume"), 
                                    TableUnit(u"p_q_mass_basis", u"Mass")
                                ]                                 
                                ,subComponentIds=None
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Condensate'),
                                code="cond", componentId="condensate", alias=u'Конденсат',
                                backColor=QColor(Qt.gray),      lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_lq",   u"Volume"), 
                                    TableUnit(u"p_q_mass_basis", u"Mass")
                                ]                                 
                                ,subComponentIds=None   
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Injected gas'),
                                code="igas", componentId="injected gas", alias=u'Закачка газа',
                                backColor=QColor(Qt.yellow),    lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_gas",  u"Volume"), 
                                ]                                 
                                ,subComponentIds=None    
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Injected water'),
                                code="iw", componentId="injected water", alias=u'Закачка воды',
                                backColor=QColor(0, 160, 230),  lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_lq",   u"Volume"), 
                                    TableUnit(u"p_q_mass_basis", u"Mass")
                                ]                                 
                                ,subComponentIds=None
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Lift gas'),
                                code="lgas", componentId="lift gas", alias=u'Газлифт',
                                backColor=QColor(Qt.yellow),    lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_gas",  u"Volume"), 
                                ]                                 
                                ,subComponentIds=None
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Free gas'),
                                code="fgas", componentId="free gas", alias=u'Свободный газ',
                                backColor=QColor(Qt.darkYellow), lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_gas",  u"Volume"), 
                                ]                                 
                                ,subComponentIds=None
                    ),
                    MyStruct(name=QCoreApplication.translate('bblInit', u'Produced fluid'),
                                code="pfl", componentId=None , alias=u'Добыча жидкости',
                                backColor=QColor(Qt.blue),      lineColor=QColor(Qt.black), labelColor=QColor(Qt.black),
                                inPercent=0
                                 ,sourceTables=[
                                    TableUnit(u"p_std_vol_lq",   u"Volume"), 
                                    TableUnit(u"p_q_mass_basis", u"Mass")
                                ]                                 
                                ,subComponentIds=["produced water","crude oil"]
                    ),
                    ]

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
                    "1LIQUID_PRODUCTION"     : StandardDiagram(name=u"Диаграмма жидкости",   scale=300000,  unitsType=0, units=0, fluids=[1, 0, 1, 0, 0, 0, 0, 0, 0]),
                    "2LIQUID_INJECTION"      : StandardDiagram(name=u"Диаграмма закачки",    scale=300000,  unitsType=0, units=0, fluids=[0, 0, 0, 0, 1, 1, 0, 0, 0]),
                    "3GAS_PRODUCTION"        : StandardDiagram(name=u"Диагмамма газа",       scale=3000000, unitsType=1, units=0, fluids=[0, 1, 0, 0, 0, 0, 0, 0, 0]),
                    "4CONDENSAT_PRODUCTION"  : StandardDiagram(name=u"Диаграмма конденсата", scale=3000000, unitsType=0, units=0, fluids=[0, 0, 0, 1, 0, 0, 0, 0, 0])
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
    def isFondLayer(layer):
        return (layer.customProperty("qgis_pds_type") == "pds_fond")

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
    def checkFieldExists(layer, fieldName, fieldType, fieldLen=20, fieldPrec=5):
        provider = layer.dataProvider()
        newIdx = layer.fieldNameIndex(fieldName)
        if newIdx < 0:
            if layer.isEditable(): layer.commitChanges()            
            with edit_layer(layer):
                provider.addAttributes([QgsField(fieldName, fieldType, QString(""), fieldLen, fieldPrec)])

    @staticmethod
    def updateOldProductionStructure(layer):
        needCopyData = False
        provider = layer.dataProvider()

        def copyValue(feature, newName, oldName, alias):
            idx = layer.fieldNameIndex(newName)
            if idx >= 0:
                val=None
                try:
                    val = feature.attribute(oldName)
                    if val:
                        layer.changeAttributeValue(feature.id(), idx, float(val))
                except KeyError:
                    pass
                layer.addAttributeAlias(idx, alias)
                
        if layer.isEditable(): layer.commitChanges() 
        with edit_layer(layer):
            for fl in bblInit.fluidCodes:
                #Check mass fields
                newName = bblInit.attrFluidMass(fl.code)
                oldName =None
                if fl.componentId is not None:
                    oldName = bblInit.attrFluidMassOld(fl.componentId)
                newIdx = layer.fieldNameIndex(newName)
                if newIdx < 0:
                    provider.addAttributes([QgsField(newName, QVariant.Double, QString(""), 20, 5)])
                    needCopyData = True

                #Check volume fields
                newName = bblInit.attrFluidVolume(fl.code)
                if fl.componentId is not None:                
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

            #Check wellrole fields
            newName = u'wellrole'
            oldName =None
            newIdx = layer.fieldNameIndex(newName)
            if newIdx < 0:
                provider.addAttributes([QgsField(newName, QVariant.String, QString(""), 20, 5)])
            #Check wellstatus fields
            newName = u'wellstatus'
            oldName =None
            newIdx = layer.fieldNameIndex(newName)
            if newIdx < 0:
                provider.addAttributes([QgsField(newName, QVariant.String, QString(""), 20, 5)])
            #Check wellstatusinfo fields
            newName = u'wsinfo'
            oldName =None
            newIdx = layer.fieldNameIndex(newName)
            if newIdx < 0:
                provider.addAttributes([QgsField(newName, QVariant.String, QString(""), 20, 5)])
            #Check wellstatusreason fields
            newName = u'wsreason'
            oldName =None
            newIdx = layer.fieldNameIndex(newName)
            if newIdx < 0:
                provider.addAttributes([QgsField(newName, QVariant.String, QString(""), 20, 5)])
            #Check initrole fields
            newName = u'initrole'
            oldName =None
            newIdx = layer.fieldNameIndex(newName)
            if newIdx < 0:
                provider.addAttributes([QgsField(newName, QVariant.String, QString(""), 20, 5)])



        if needCopyData:
            if layer.isEditable(): layer.commitChanges()
            with edit_layer(layer):
                features = layer.getFeatures()
                for feature in features:
                    for fl in bblInit.fluidCodes:
                        if fl.componentId is None:continue                        
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

            #other fields
            for name,alias in [
                                 [u'wellrole'  ,u'назначение'           ]
                                ,[u'wellstatus',u'статус'               ]
                                ,[u'wsinfo'    ,u'уточнение статуса'    ]
                                ,[u'wsreason'  ,u'причина смены статуса']
                                ,[u'initrole'  ,u'первоначальное назначение']
                                ]:
                idx = layer.fieldNameIndex(name)
                if idx >= 0:
                    layer.addAttributeAlias(idx, alias)
                



