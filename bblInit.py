# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from QgisPDS.utils import *
from qgis.core import QgsField 
from collections import namedtuple
from utils import edit_layer, cached_property
from calc_statistics import removeOutliers, removeOutliers2

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


#===============================================================================
# 
#===============================================================================
class Debit(MyStruct):
    value=0
    dt=''
    def __repr__(self):
        return u"'{}:{}'".format(self.dt.toString('yyyy.M.d'),self.value)
    def __str__(self):
        return self.__repr__()
    

#===============================================================================
# 
#===============================================================================
class ProdDebit(object):
    DEBIT_TYPE_MASS='mass'
    DEBIT_TYPE_VOL='vol'
    records_limit=5          #limit of stored items
    enable_bad_data_filter=False
    filter_koef=3
    debits=None
    def __init__(self,records_limit=3,enable_bad_data_filter=False,filter_koef=3,log_msg_on_bad_data_filtered=''):
        self.debits={
                self.DEBIT_TYPE_MASS:[]
                ,self.DEBIT_TYPE_VOL:[]
                }
        self.records_limit=records_limit
        self.enable_bad_data_filter=enable_bad_data_filter
        self.filter_koef=filter_koef
        self.log_msg_on_bad_data_filtered=log_msg_on_bad_data_filtered
        
    def sorted_func(self,valueOld,valueNew):
        #QgsMessageLog.logMessage(u"{}  {}".format(str(valueNew),str(valueOld)), tag="QgisPDS.debug")
        return valueNew.value>valueOld.value #function applied to value for sorting item[0]-key,item[1]-value
    
    def addDebit(self
                 ,debit # type: Debit
                 ,debit_type
                 ):
        
        if len(self.debits[debit_type])==0:
            self.debits[debit_type].append(debit)
        else:
            isInserted=False
            for idx,debit_old in enumerate(self.debits[debit_type]):
                if self.sorted_func(debit_old,debit):
                    self.debits[debit_type].insert(idx, debit)
                    isInserted=True
                    break
            if not isInserted and len(self.debits[debit_type])<self.records_limit: self.debits[debit_type].append(debit)
            self.debits[debit_type]=self.debits[debit_type][:self.records_limit]
        pass
    
    def bad_data_filter(self,items):
        res=removeOutliers([item.value for item in items],self.filter_koef)
        return [item for item in items if item.value in res]
#         if len(items)>=2:
#             for idx in range(len(items)-1):
#                 if items[idx+1].value>0 and items[idx].value/items[idx+1].value>=self.filter_koef:
#                     continue
#                 else:
#                     #if idx>0: QgsMessageLog.logMessage(u"\t{}".format(str(items[idx:] )), tag="QgisPDS.info")
#                     return items[idx:]
#             #QgsMessageLog.logMessage(u"\t{}".format(str([items[-1]] )), tag="QgisPDS.info")
#             return [items[-1]]
#         else:
#             #QgsMessageLog.logMessage(u"\t{}".format(str([items[0]] )), tag="QgisPDS.debug")
#             return [items[0]] 

    def bad_data_filter_and_print(self,debit_type,log_prefix):
        res=self.bad_data_filter([row for row in self.debits[debit_type]])
        if res[0].value!=self.debits[debit_type][0].value:
            QgsMessageLog.logMessage(u"{}".format(self.log_msg_on_bad_data_filtered), tag="QgisPDS.info")
            QgsMessageLog.logMessage(u"\t{}".format(log_prefix), tag="QgisPDS.info")
            QgsMessageLog.logMessage(u"\t\t {}".format(", ".join(map(str, [self.debits[debit_type][i] for i in range(len(self.debits[debit_type]))] )) ), tag="QgisPDS.info")
            QgsMessageLog.logMessage(u"\t\t-> {}".format(str(res)), tag="QgisPDS.info")
            pass
        return res
         
    
    @property
    def massValue(self):
        debit_type=self.DEBIT_TYPE_MASS
        if len(self.debits[debit_type])>0:
            if not self.enable_bad_data_filter:
                return  self.debits[debit_type][0].value
            else:
                res=self.bad_data_filter_and_print(debit_type,log_prefix="Mass")
                return res[0].value
        else: return None
                
    @property
    def massDebitDate(self):
        debit_type=self.DEBIT_TYPE_MASS
        if len(self.debits[debit_type])>0:
            if not self.enable_bad_data_filter:
                return  self.debits[debit_type][0].dt
            else:
                res=self.bad_data_filter([row for row in self.debits[debit_type]])
                return res[0].dt
        else: return None
    @property
    def volValue(self):
        debit_type=self.DEBIT_TYPE_VOL
        if len(self.debits[debit_type])>0:
            if not self.enable_bad_data_filter:
                return  self.debits[debit_type][0].value
            else:
                res=self.bad_data_filter_and_print(debit_type,log_prefix="Volume")
                return res[0].value
        else: return None
 
    @property
    def volDebitDate(self):
        debit_type=self.DEBIT_TYPE_VOL
        if len(self.debits[debit_type])>0:
            if not self.enable_bad_data_filter:
                return  self.debits[debit_type][0].dt
            else:
                res=self.bad_data_filter([row for row in self.debits[debit_type]])
                return res[0].dt
        else: return None

    
    
#===============================================================================
# 
#===============================================================================
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
    _alias=""
    def __init__(self
                        ,field_name=None
                        ,field_type=None    # char, varchar, text, int, serial, double
                        ,field_comment=None
                        ,field_len=0
                        ,field_prec=0
                        ,field_alias=""
                 ):
        self.field=QgsField(name=field_name
                        #, type= FIELD_TYPES[self.field_type]
                        , typeName=field_type  # char, varchar, text, int, serial, double. QVariant.Double,QVariant.Date,QVariant.String
                        , len=field_len
                        , prec=field_prec
                        , comment=field_comment
                        #, subType
                        )

        if field_alias is not None:
            if hasattr(self.field,'setAlias'):self.field.setAlias(field_alias)
            else: self._alias=field_alias        
    @cached_property
    def name(self):
        return self.field.name()
    @cached_property
    def memoryfield(self):
        return '&field={}:{}'.format(self.field.name(),self.field.typeName())
    @cached_property
    def alias(self):
        if hasattr(self.field,'alias'):
            return self.field.alias()
        else: 
            return self._alias    
            
#===============================================================================
# 
#===============================================================================
class Fields:
    """
         @info: store all fields for layers. Import it when define fields/columns for layer
    """
    WellId =           AttributeField( field_name=u'well_id'    ,field_type="string" ,field_alias=u"Скважина"                  ,field_len=30 ,field_prec=0)
    Latitude =         AttributeField( field_name=u'latitude'   ,field_type="double" ,field_alias=u"Широта"                    ,field_len=20 ,field_prec=6)
    Longitude =        AttributeField( field_name=u'longitude'  ,field_type="double" ,field_alias=u"Долгота"                   ,field_len=20 ,field_prec=6) 
    Days =             AttributeField( field_name=u'days'       ,field_type="double" ,field_alias=u"Кол-во дней работы"        ,field_len=20 ,field_prec=2)
    Sldnid =           AttributeField( field_name=u'sldnid'     ,field_type="int"    ,field_alias=u"ИД в БД"                   ,field_len=40 ,field_prec=0)
    Api =              AttributeField( field_name=u'api'        ,field_type="string" ,field_alias=u"Цех/Промысел"              ,field_len=20 ,field_prec=0)
    Operator =         AttributeField( field_name=u'operator'   ,field_type="string" ,field_alias=u"Оператор"                  ,field_len=20 ,field_prec=0)
    Country =          AttributeField( field_name=u'country'    ,field_type="string" ,field_alias=u"Страна"                    ,field_len=30 ,field_prec=0)
    Depth =            AttributeField( field_name=u'depth'      ,field_type="double" ,field_alias=u"Глубина"                   ,field_len=20 ,field_prec=3)
    ElevationPoint =   AttributeField( field_name=u'measuremen' ,field_type="string" ,field_alias=u"Точка отсчета альтитуды"   ,field_len=20 ,field_prec=0)    
    EleationvDatum =   AttributeField( field_name=u'datum'      ,field_type="string" ,field_alias=u"Датум"                     ,field_len=20 ,field_prec=0)    
    Elevation =        AttributeField( field_name=u'elevation'  ,field_type="double" ,field_alias=u"Альтитуда"                 ,field_len=20 ,field_prec=3)        
    OnOffShor =        AttributeField( field_name=u'on_offshor' ,field_type="string" ,field_alias=u"на суше/море"              ,field_len=20 ,field_prec=0)    
    SpudDate =         AttributeField( field_name=u'spud_date'  ,field_type="date"   ,field_alias=u"дата бурения"              ,field_len=50 ,field_prec=0)    
                                                                                                               
    SymbolId =         AttributeField( field_name=u'symbolid'   ,field_type="string" ,field_alias=u""                          ,field_len=400 ,field_prec=0)
    Symbol =           AttributeField( field_name=u'symbolcode' ,field_type="integer",field_alias=u""                          ,field_len=10 ,field_prec=0)
    SymbolName =       AttributeField( field_name=u'symbolname' ,field_type="string" ,field_alias=u""                          ,field_len=100 ,field_prec=0)
                                                                                                               
    TigWellSymbol =    AttributeField( field_name=u'symbol'     ,field_type="string" ,field_alias=u""                          ,field_len=50 ,field_prec=0)    
    TigLatestWellState=AttributeField( field_name=u'status'     ,field_type="string" ,field_alias=u""                          ,field_len=50 ,field_prec=0)
                                                                                                               
    WellRole =         AttributeField( field_name=u'wellrole'   ,field_type="string" ,field_alias=u'назначение'                ,field_len=50 ,field_prec=0)
    WellStatus =       AttributeField( field_name=u'wellstatus' ,field_type="string" ,field_alias=u"статус"                    ,field_len=50 ,field_prec=0)
    WellStatusReason = AttributeField( field_name=u'wsreason'   ,field_type="string" ,field_alias=u"причина смены статуса"     ,field_len=50 ,field_prec=0)
    WellStatusInfo =   AttributeField( field_name=u'wsinfo'     ,field_type="string" ,field_alias=u"уточнение статуса"         ,field_len=50 ,field_prec=0)
    WellInitRole =     AttributeField( field_name=u'initrole'   ,field_type="string" ,field_alias=u"первоначальное назначение" ,field_len=50 ,field_prec=0)
    LiftMethod =       AttributeField( field_name=u'liftmethod' ,field_type="string" ,field_alias=u"способ эксплуатации"       ,field_len=50 ,field_prec=0)
                                                                                                                          
    bubblesize =       AttributeField( field_name=u"bubblesize" ,field_type="double" ,field_alias=u""                          ,field_len=20 ,field_prec=5)
    #bubblefields =     AttributeField( field_name=u'bubbleflds' ,field_type="string",field_alias=u""                          ,field_len=20 ,field_prec=5)
    #labels =           AttributeField( field_name=u'bbllabels'  ,field_type="string",field_alias=u""                          ,field_len=20 ,field_prec=5)
    scaletype =        AttributeField( field_name=u"scaletype"  ,field_type="string" ,field_alias=u""                          ,field_len=50 ,field_prec=0)
    movingres =        AttributeField( field_name=u"movingres"  ,field_type="string" ,field_alias=u""                          ,field_len=50 ,field_prec=0)
    resstate =         AttributeField( field_name=u"resstate"   ,field_type="string" ,field_alias=u""                          ,field_len=50 ,field_prec=0)
    multiprod =        AttributeField( field_name=u"multiprod"  ,field_type="string" ,field_alias=u""                          ,field_len=50 ,field_prec=0)
                                                                                                                          
    startDate =        AttributeField( field_name=u'startdate'  ,field_type="date"   ,field_alias=u"дата начала"               ,field_len=50 ,field_prec=0)
                                                                                                                          
    IsGlobal =         AttributeField( field_name=u'global_pri' ,field_type="string" ,field_alias=u""                          ,field_len=20 ,field_prec=0)    
    Owner    =         AttributeField( field_name=u'owner'      ,field_type="string" ,field_alias=u"владелец данных"           ,field_len=20 ,field_prec=0)    
    CreatedDT =        AttributeField( field_name=u'created'    ,field_type="DateTime",field_alias=u"дата создания"            ,field_len=50 ,field_prec=0)
    Project =          AttributeField( field_name=u'project'    ,field_type="string"  ,field_alias=u"проект"                   ,field_len=30 ,field_prec=0)
                                                                                                                          
    lablx =            AttributeField( field_name=u"lablx"      ,field_type="double"  ,field_alias=u""                         ,field_len=20 ,field_prec=5)
    lably =            AttributeField( field_name=u"lably"      ,field_type="double"  ,field_alias=u""                         ,field_len=20 ,field_prec=5)
    labloffx =         AttributeField( field_name=u"labloffx"   ,field_type="double"  ,field_alias=u""                         ,field_len=20 ,field_prec=5)
    labloffy =         AttributeField( field_name=u"labloffy"   ,field_type="double"  ,field_alias=u""                         ,field_len=20 ,field_prec=5)
    labloffset =       AttributeField( field_name=u"labloffset" ,field_type="double"  ,field_alias=u""                         ,field_len=20 ,field_prec=5)
    lablwidth =        AttributeField( field_name=u"lablwidth"  ,field_type="double"  ,field_alias=u""                         ,field_len=20 ,field_prec=5)
    lablcolor =        AttributeField( field_name=u"lablcol"    ,field_type="string"  ,field_alias=u""                         ,field_len=20 ,field_prec=0)    
    lablbuffcolor =    AttributeField( field_name=u"bufcol"     ,field_type="string"  ,field_alias=u""                         ,field_len=20 ,field_prec=0)    
    lablbuffwidth  =   AttributeField( field_name=u"bufwidth"   ,field_type="double"  ,field_alias=u""                         ,field_len=20 ,field_prec=5)
    lablfont =         AttributeField( field_name=u"font"       ,field_type="string"  ,field_alias=u""                         ,field_len=20 ,field_prec=0)    
        

def setLayerFieldsAliases(layer,force=False):
    '''
        @summary: for qgis 2.14 backward support. 
    ''' 
    if hasattr(QgsField, 'setAlias') and not force:pass
    else:
        all_fields=Fields.__dict__
        for _,field in all_fields.items():
            if isinstance(field,AttributeField) and field.alias!="":
                #QgsMessageLog.logMessage(u"{}  {}".format(str(field),type(field)), tag="QgisPDS.debug")
                #QgsMessageLog.logMessage(u"\t{} {}".format(field.name,field.alias), tag="QgisPDS.debug")
                idx = layer.fieldNameIndex(field.name)
                if idx >= 0:
                    layer.addAttributeAlias(idx, field.alias)
                    #QgsMessageLog.logMessage(u"\t+{}".format(idx), tag="QgisPDS.debug")
    
    
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
    
FieldsProdLayer=[
            Fields.WellId
            ,Fields.Latitude
            ,Fields.Longitude
            ,Fields.SymbolId
            ,Fields.SymbolName
            ,Fields.Symbol
            ,Fields.WellRole
            ,Fields.WellStatus
            ,Fields.WellStatusReason
            ,Fields.WellStatusInfo
            ,Fields.WellInitRole
            ,Fields.startDate
            ,Fields.Days
            ,Fields.LiftMethod
            ,Fields.bubblesize
            ,Fields.scaletype
            ,Fields.movingres
            ,Fields.resstate
            ,Fields.multiprod
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
        return fluidCode + u" (макс. дебит по массе тонн)"
    
    @staticmethod
    def aliasFluidMaxDebitDateMass(fluidCode):
        return fluidCode + u" (дата макс. дебита по массе)"

    @staticmethod
    def aliasFluidMaxDebitVol(fluidCode):
        return fluidCode + u" (макс. дебит по объему м3)"

    @staticmethod
    def aliasFluidMaxDebitDateVol(fluidCode):
        return fluidCode + u" (дата макс. дебита по объему)"
    #===========================================================================
    # 
    #===========================================================================
    @staticmethod
    def checkFieldExists(layer, fieldName, fieldType, fieldLen=20, fieldPrec=5):
        provider = layer.dataProvider()
        newIdx = layer.fieldNameIndex(fieldName)
        if newIdx < 0:
            if layer.isEditable(): layer.commitChanges()            
            with edit_layer(layer):
                provider.addAttributes([QgsField(fieldName, fieldType, QString(""), fieldLen, fieldPrec)])
    #===========================================================================
    # 
    #===========================================================================
    @staticmethod
    def checkQgsFieldExists(layer, qgsfield): 
        provider = layer.dataProvider()
        newIdx = layer.fieldNameIndex(qgsfield.name())
        if newIdx < 0:
            if layer.isEditable(): layer.commitChanges()            
            with edit_layer(layer):
                provider.addAttributes([field])                
    #===========================================================================
    # 
    #===========================================================================
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
        #features = layer.getFeatures()
        #for feature in features:
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
                            [Fields.WellRole.name,Fields.WellRole.alias              ]
                            ,[Fields.WellStatus.name,Fields.WellStatus.alias         ]
                            ,[Fields.WellStatusInfo.name,Fields.WellStatusInfo.alias ]
                            ,[Fields.WellStatusReason.name,Fields.WellStatusReason.alias]
                            ,[Fields.WellInitRole.name,Fields.WellInitRole.alias     ]
                             #[u'wellrole'  ,u'назначение'           ]
                            #,[u'wellstatus',u'статус'               ]
                            #,[u'wsinfo'    ,u'уточнение статуса'    ]
                            #,[u'wsreason'  ,u'причина смены статуса']
                            #,[u'initrole'  ,u'первоначальное назначение']
                            ]:
            idx = layer.fieldNameIndex(name)
            if idx >= 0:
                layer.addAttributeAlias(idx, alias)
                



