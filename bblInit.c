
/*
C-------------------------------------------------------------------
C    Copyright (C) 2008-2013 Tigress Limited
C    All rights reserved.
C-------------------------------------------------------------------
 
*/


#define BBL_MAIN

#include <tigress/tigdef.h>
#include <tigress/gradef.h>
#include <tigress/tlldef.h>


#include <mapping/bbl_ext.h>
#include "bbl_int.h"

FLUID_CODES FluidCodes[CODE_NAME_COUNT] = {
  {0, "Crude oil", "crude oil", "Volume of oil produced over a period of time", 0, 0, 0, 0, 0, 1, 0, LGFIRE, LGBLCK, GCPSOL},
  {0, "Natural gas", "natural gas", "Volume of gas produced over a period of time", 0, 0, 0, 0, 1, 0, 0, LGYELO, LGBLCK, GCPSOL},
  {0, "Produced water","produced water", "Volume of water produced over a period of time", 0, 0, 0, 1, 0, 0, 0, LGBLUE, LGBLCK, GCPSOL},  
  {0, "Condensate","condensate", "Volume of condensate produced over a period of time", 0, 0, 0, 0, 1, 0, 1, LGGRAY, LGBLCK, GCPSOL},
  {0, "Injected gas", "injected gas", "Volume of gas injected over a period of time", 0, 1, 0, 0, 0, 0, 0, LGYELO, LGBLCK, GCPSOL},
  {0, "Injected water", "injected water", "Volume of water injected over a period of time", 0, 1, 0, 0, 0, 0, 0, LGBLUE, LGBLCK, GCPSOL},
  {0, "Lift gas", "lift gas", "Volume of oil produced over a period of time by lift gas method", 0, 0, 0, 0, 0, 0, 0, LGYELO, LGBLCK, GCPSOL},
  {0, "Free gas", "free gas", "Volume of free gas produced over a period of time", 0, 0, 0, 0, 1, 0, 0, LGYELO, LGBLCK, GCPSOL},
};

int upArrowWells[UP_ARROW_WELLS_COUNT] = {73,74,75,76,79,80,83,84,95,96,97,98,109,110,119,120,121,122,127,
                       128,129,130,131,132,133,134,139,140,141,142,148,149,150,151,152,
                       158,159,160,161,162,163,164,165,166,167,173,174,175,176,177,179,
                       182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,
                       198,199,200,201,203,209,211,212};

int downArrowWells[DOWN_ARROW_WELLS_COUNT] = {73,74,83,84,107,108,119,120,121,122,127,128,129,130,148,149,
                         150,151,152,158,159,160,161,162,179,182,183,184,185,186,187,
                         188,189,190,191,193,195,196,197,198,199,200,201,203,209,211,212};

BBL_TYPE_SETUP bblTypesSetup[BBL_TYPES_NUMBER] = {
	{"Liquid bubble", "Liquid production ratio 1 cm sq.", 100.0, "t. per day", "Mass", "tonne", "cu m", 2, {2, 0}},
	{"Injection bubble", "Injection ratio 1 cm sq.", 50.0, "m cub. per day", "Volume", "tonne", "cu m", 2, {4, 5}},
	{"Gas bubble", "Gas production ratio 1 cm sq.", 50.0, "m cub. per day", "Volume", "tonne", "cu m", 3, {1, 6, 7}},
	{"Condensate bubble", "Condensate production ratio 1 cm sq.", 50.0, "t. per day", "Mass", "tonne", "cu m", 1, {3}},
};

BBL_LIFT_METHOD bblLiftMethods[BBL_LIFT_METHODS_NUMBER] = {
	{"flowing", TRUE, FALSE},
	{"centrifugal pump", FALSE, TRUE},
	{"diaphragm pump", FALSE, TRUE},
	{"sucker-rod pump", FALSE, TRUE},
	{"jet pump", FALSE, TRUE},
	{"plunger pump", FALSE, TRUE},
	{"gas lift", FALSE, FALSE},
	{"spiral pump", FALSE, TRUE},
	{"RED pump", FALSE, TRUE},
};

BBL_SYMBOL bblSymbols[BBL_SYMBOLS_NUMBER] = {
	{"oil producing", "active stock", 81},
	{"water injecting", "active stock", 83},
	{"gas producing", "active stock", 220},
	{"water-supply", "active stock", 103},
	{"water absorbing", "active stock", 105},
	{"oil producing", "suspended stock", 147},
	{"water injecting", "suspended stock", 152},
	{"gas producing", "suspended stock", 221},
	{"water-supply", "suspended stock", 230},
	{"water absorbing", "suspended stock", 239},
	{"oil producing", "waiting completion stock", 117},
	{"water injecting", "waiting completion stock", 121},
	{"gas producing", "waiting completion stock", 222},
	{"water-supply", "waiting completion stock", 231},
	{"water absorbing", "waiting completion stock", 240},
	{"oil producing", "completion stock", 118},
	{"water injecting", "completion stock", 122},
	{"gas producing", "completion stock", 223},
	{"water-supply", "completion stock", 232},
	{"water absorbing", "completion stock", 241},
	{"oil producing", "QC stock", 85},
	{"water injecting", "QC stock", 85},
	{"gas producing", "QC stock", 85},
	{"water-supply", "QC stock", 85},
	{"water absorbing", "QC stock", 85},
	{"oil producing", "piezometric stock", 89},
	{"water injecting", "piezometric stock", 89},
	{"gas producing", "piezometric stock", 89},
	{"water-supply", "piezometric stock", 89},
	{"water absorbing", "piezometric stock", 89},
	{"oil producing", "conservation stock", 145},
	{"water injecting", "conservation stock", 150},
	{"gas producing", "conservation stock", 224},
	{"water-supply", "conservation stock", 233},
	{"water absorbing", "conservation stock", 242},
	{"oil producing", "abandonment stock", 181},
	{"water injecting", "abandonment stock", 185},
	{"gas producing", "abandonment stock", 225},
	{"water-supply", "abandonment stock", 234},
	{"water absorbing", "abandonment stock", 243},
	{"oil producing", "waiting abandonment stock", 181},
	{"water injecting", "waiting abandonment stock", 185},
	{"gas producing", "waiting abandonment stock", 225},
	{"water-supply", "waiting abandonment stock", 235},
	{"water absorbing", "waiting abandonment stock", 244},
	{"oil producing", "inactive stock", 202},
	{"water injecting", "inactive stock", 203},
	{"gas producing", "inactive stock", 227},
	{"water-supply", "inactive stock", 237},
	{"water absorbing", "inactive stock", 246},
	{"oil producing", "proposed stock", 82},
	{"water injecting", "proposed stock", 84},
	{"gas producing", "proposed stock", 228},
	{"water-supply", "proposed stock", 104},
	{"water absorbing", "proposed stock", 106},
	{"oil producing", "drilling stock", 116},
	{"water injecting", "drilling stock", 120},
	{"gas producing", "drilling stock", 229},
	{"water-supply", "drilling stock", 238},
	{"water absorbing", "drilling stock", 247},
	{"oil producing", "test stock", 126},
	{"water injecting", "test stock", 126},
	{"gas producing", "test stock", 126},
	{"water-supply", "test stock", 126},
	{"water absorbing", "test stock", 126},
	{"oil producing", "exploration abandonment stock", 188},
	{"water injecting", "exploration abandonment stock", 188},
	{"gas producing", "exploration abandonment stock", 188},
	{"water-supply", "exploration abandonment stock", 188},
	{"water absorbing", "exploration abandonment stock", 188},
};

BBL_CONVERTED_SYMBOL bblConvertedSymbols[BBL_CONV_SYMBOLS_NUMBER] = {
	{"water injecting", "oil producing", "active stock", 211}, /* producing well converted from injecting */
	{"water injecting", "oil producing", "suspended stock", 211},
	{"oil producing", "water injecting", "active stock", 212},
	{"oil producing", "water injecting", "suspended stock", 212}, /* injecting well converted from producing */
};

BBL_DRAW_STYLE bblDrawStyle = {1.0, GCCLGY, GCCRED};



/*
C   24JAN13  PT   SCR 20319 Original version
*/

int bblProductionEnabled()
{
	/* check if TIG_MAP_ENABLE_PRODUCTION variable is set */
	return ( getenv("TIG_MAP_ENABLE_PRODUCTION") != NULL );

}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblInit
CA
CA
CA  FUNCTION:  Initializes bubble plot system
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   void bblInit(long *ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  ier         O     long *  Error return:
CA                               SUCCES = successful completion
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   17DEC05  VK   Original version
C   17AUG12  PT   SCR 20544 Add temporary functions for creation and dump 
C                 basemap extra column.
C   25JAN13  PT   SCR 20544 Move temporary functions for creation and dump 
C                 basemap extra column to mmeBaseMap.c
C   01MAR13  PT   SCR 20319 Init bblLegendHead. Remove bblInitProdStatusList
C   14MAY13  PT   SCR 20319 Remove initialisation of unused variables
*/

void bblInit(int *ier)
{

  tutloc_("libprodbubbles", ier) ;

  /* Initialize legend variable */
  TheLegend.patterns = NULL;
  TheLegend.symbols = NULL;
  bblTitleHead = NULL;
  bblLegendHead = NULL;

  productionDisplayed = FALSE;
  coordinatesFromZonesCalculated = FALSE;

  LoadBubbleSetup(ier);
  loadDefaultTitleDetail(&title.detail,ier);
  loadDefaultLegendDetail(&legend.detail,ier);

}