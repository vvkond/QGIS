/*
C-------------------------------------------------------------------
C    Copyright (C) 2012 Tigress Limited
C    All rights reserved.
C-------------------------------------------------------------------
 
*/

#include <tigress/tigdef.h>
#include <tigress/qry.h>
#include <tigress/tdm.h>
#include <tigress/mdb.h>
#include <tigress/zdm.h>


#include <mapping/bbl_ext.h>
#include "bbl_int.h"

typedef struct _reservoir_press_data {
	double pressure;
	double x;
	double y;
	double z;
	char reservoirName[41];
	char tigZonationName[41];
	char topZoneName[41];
	char baseZoneName[41];
	struct _well_press_data *parent;
} RESERVOIR_PRESS_DATA;


typedef struct _well_press_data {
	TigList(RESERVOIR_PRESS_DATA) pressureDataForWellReservoirs;
	double avgX;
	double avgY;
	double avgPressure;
	PROD_WELL *prodWell;
} WELL_PRESS_DATA;

typedef struct _press_map_data {
	TigList(WELL_PRESS_DATA) pressureDataForWells;
	CONTROL_POINT_SET *wellsCps;
	CONTROL_POINT_SET *borderCps;
	int cpWellsGroupKey;
	int cpWellsSetKey;
	int cpBorderGroupKey;
	int cpBorderSetKey;
	int pyGroupKey;
	int pySetKey;
	char groupName[GRPLEN];
	char setName[SETLEN];
	char borderGroupName[GRPLEN];
	char borderSetName[SETLEN];
} PRESS_MAP_DATA;


static void bblCreateSurface(int pyGroupKey, int pySetKey, int CPWellsGroupKey, int CPWellsSetKey,
                             int CPBorderGroupKey, int CPBorderSetKey, int numcols, int numrows,
                             double xMinAOI, double xMaxAOI, double yMinAOI, double yMaxAOI,
                             char *surfaceGroupName, char *surfaceSetName,
                             SURFACE_GROUP **surfaceGroup, SURFACE_SET **surfaceSet, int *ier);
static void bblAddControlPoint(CONTROL_POINT_SET **cps_ptr, char *groupName, char *setName, 
                               char *subsetName, double x, double y, double value,
                               int *groupKey, int *setKey, int *subsetKey, int *ier);
static int bblCalculateReservoirCoordinates(void *item, void *arg, int *ier);
static int bblCalculateCoordinatesOfWellReservoirs(void *item, void *arg, int *ier);
static int bblCreatePressureCP(void *item, void *arg, int *ier);
static void bblShowPressureSurface(PRESS_MAP_DATA *pressureMapData, int *ier);
static int bblFindReservoirPressData(void *resPressData, void *resName, int *ier);
static int bblReadPressure(void *item, void *arg, int *ier);
static void bblGetSurfaceAOI(PRESS_MAP_DATA *pressureMapData,
                             double *xMinAOI,
                             double *xMaxAOI,
                             double *yMinAOI,
                             double *yMaxAOI,
                             int *ier);
static void bblFreeWellPressureData(void *item, int *ier);

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblCreateSurface
CA
CA
CA  FUNCTION:  Create surface.
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
C   REVISED:
C
C   29MAY12  PT   SCR 20319 Original version
C   19NOV12  PT   SCR 20319 Add border control point set and group keys to
C                 parameter list.
C   13MAY13  PT   SCR 20319 Use mccGrid for gridding
C
C
*/

void bblCreateSurface(int pyGroupKey, int pySetKey, int CPWellsGroupKey, int CPWellsSetKey,
                      int CPBorderGroupKey, int CPBorderSetKey, int numcols, int numrows,
                      double xMinAOI, double xMaxAOI, double yMinAOI, double yMaxAOI,
                      char *surfaceGroupName, char *surfaceSetName,
                      SURFACE_GROUP **surfaceGroup, SURFACE_SET **surfaceSet, int *ier) {

	int gridCPGroupKeys[3], gridCPSetKeys[3];
	int gridPyGroupKeys[2], gridPySetKeys[2];
	int surfaceGroupKey, surfaceSetKey;

	GRID_DEFINITION gridDef;

	/* Set grid definition structure */

	gridDef.numcols=numcols;
	gridDef.numrows=numrows;

	gridDef.xMinimum = xMinAOI;
	gridDef.xMaximum = xMaxAOI;
	gridDef.yMinimum = yMinAOI;
	gridDef.yMaximum = yMaxAOI;

	gridDef.xIncrement = (gridDef.xMaximum - gridDef.xMinimum) / (gridDef.numcols - 1);
	gridDef.yIncrement = (gridDef.yMaximum - gridDef.yMinimum) / (gridDef.numrows - 1);

	/*Set arrays of control point group and set keys*/

	gridCPGroupKeys[0] = CPWellsGroupKey;
	gridCPGroupKeys[1] = CPBorderGroupKey;
	gridCPGroupKeys[2] = 0;
	gridCPSetKeys[0] = CPWellsSetKey;
	gridCPSetKeys[1] = CPBorderSetKey;
	gridCPSetKeys[2] = 0;

	/*Set arrays of polygon group and set keys*/

	gridPyGroupKeys[0] = pyGroupKey; gridPyGroupKeys[1] = 0;
	gridPySetKeys[0] = pySetKey; gridPySetKeys[1] = 0;

	/* Do gridding */

	mccGrid( &gridDef, gridCPGroupKeys, gridCPSetKeys,
	          NULL, NULL,
	          gridPyGroupKeys, gridPySetKeys,
	          surfaceGroupName,  surfaceSetName,
	          &surfaceGroupKey, &surfaceSetKey, ier );
	ERROR_CHECK( "bblCreateSurface: mccGrid failed")



	/* Get surface group and set structures*/

	*surfaceGroup = mdafsg( surfaceGroupKey, ier );
	ERROR_CHECK( "bblCreateSurface: mdafsg failed")

	*surfaceSet = mdafss( surfaceGroupKey, surfaceSetKey, ier );
	ERROR_CHECK( "bblCreateSurface: mdafss failed")

	(*surfaceSet)->parameter = PRESS;
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblAddControlPoint
CA
CA
CA  FUNCTION:  Add control point to control point set.
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
C   REVISED:
C
C   29MAY12  PT   SCR 20319 Original version
C
C
*/

void bblAddControlPoint(CONTROL_POINT_SET **cps_ptr, char *groupName, char *setName, 
                        char *subsetName, double x, double y, double value,
                        int *groupKey, int *setKey, int *subsetKey, int *ier) {
	CONTROL_POINT_SET *cps;
	CP_SUBSET *cpssp;
	CP_SUBSET_VALUES *cpssvp;

	cps = *cps_ptr;

	/* create conrol point subset */

	cpssp = mdancpss( 1, subsetKey, ier );
	ERROR_CHECK( "mgaAddControlPoint: mdancpss failed")

	(void) strcpy( cpssp->subsetName, subsetName );

	cpssp->visible = FALSE;
	cpssvp = cpssp->current;
	cpssvp->status = MSSV_EDITED;

	cpssvp->nControlPoints = 1;
	cpssvp->xControlPoint[0] = x;
	cpssvp->yControlPoint[0] = y;
	cpssvp->vControlPoint[0] = value;

	/* set the minimum and maximum values for the subset */

	mdazcpssv( cpssvp, ier );
	ERROR_CHECK( "mgaAddControlPoint: mdazcpssv failed")

	/* create conrol point set if it has not been created yet */

	if (!cps) {
		cps = mcc_mkcps(groupName, setName, TRUE, groupKey, setKey, ier);
		ERROR_CHECK( "mgaAddControlPoint: mcc_mkcps failed")

		cps->source = WELL;

		*cps_ptr = cps;
	}

	/* link the subset into list for the set */

	mdalcpss( cps, cpssp, ier );
	ERROR_CHECK( "mgaAddControlPoint: mdalcpss failed")

}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblCalculateReservoirCoordinates
CA
CA
CA  FUNCTION:  Calculate coordinates of well reservoir (tll version).
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
CA  LINKAGE:   int bblCalculateReservoirCoordinates(item, arg, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  item        I     void *  Reservoir pressure data pointer
CA  arg         I     void *  Null
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
C   29MAY12  PT   SCR 20319 Original version
C
C
*/

int bblCalculateReservoirCoordinates(void *item, void *arg, int *ier) {
	int *zonationSldList, numZonations, numMultiWellsZonations;
	int multiWellZonationSldnid, zoneInd, zonationSldnid, topZoneSldnid;
	PROD_WELL *wp;
	RESERVOIR_PRESS_DATA *reservoirPressData = (RESERVOIR_PRESS_DATA *)item;

	wp = reservoirPressData->parent->prodWell;

	zdmGetZonSldnids(reservoirPressData->tigZonationName, &zonationSldList, &numZonations, ier);
	if (*ier != SUCCESSFUL) {
		ohnooo_ (ier, "bblCalculateReservoirCoordinates: zdmGetZonSldnids failed");
		return FALSE;
	}

	numMultiWellsZonations = 0;

	for(zoneInd = 0; zoneInd < numZonations; zoneInd++) {
		int num_relevant_wells;

		/* Load Zonation */
		zdmLoadZonation (zonationSldList[zoneInd], ier);
		if (*ier != SUCCES) {
			ohnooo_ (ier, "bblCalculateReservoirCoordinates: zdmLoadZonation error");
			*ier = SUCCES;
			continue;
		}

		/* Get number of wells */
		zdmNumWells(zonationSldList[zoneInd], &num_relevant_wells, ier);
		if (*ier != SUCCES) {
			ohnooo_ (ier, "bblCalculateReservoirCoordinates: zdmGetWells error");
			return FALSE;
		}

		if (num_relevant_wells > 1) {
			numMultiWellsZonations++;
			multiWellZonationSldnid = zonationSldList[zoneInd];
		}

		/* free zonation */
		zdmFreeZonation(zonationSldList[zoneInd], ier);
		ERROR_CHECK_RETURN("bblCalculateReservoirCoordinates: zdmFreeZonation error", FALSE)

	}

	reservoirPressData->x = DPINDT;
	reservoirPressData->y = DPINDT;
	reservoirPressData->z = DPINDT;

	if (numZonations <= 0) {
		ohNooo(200000002, "Could not find zonation with name: <%s>", reservoirPressData->tigZonationName);
	} else if (numMultiWellsZonations > 1) {
		ohNooo(200000002, "More than one multi-well zonations with name: <%s>", reservoirPressData->tigZonationName);
	} else {

		if (numMultiWellsZonations <= 0)
			zonationSldnid = zonationSldList[0];
		else
			zonationSldnid = multiWellZonationSldnid;

		zdmGetIntervalSldnid(zonationSldnid, reservoirPressData->topZoneName, &topZoneSldnid, ier);
		if (*ier != SUCCESSFUL) {
			ohnooo_ (ier, "bblCalculateReservoirCoordinates: zdmGetIntervalSldnid failed");
			return FALSE;
		}

		bblIntersectWellWithZone(zonationSldnid, topZoneSldnid, wp->well, 
		                         &reservoirPressData->x, &reservoirPressData->y, 
		                         &reservoirPressData->z, ier);
		ERROR_CHECK_RETURN("bblCalculateReservoirCoordinates: bblIntersectWellWithZone failed", FALSE)

	}

	/* free zonation sldnid list */

	if (numZonations)
		free(zonationSldList);

	return FALSE;
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblCalculateCoordinatesOfWellReservoirs
CA
CA
CA  FUNCTION:  Calculate coordinates of well reservoirs (tll version).
CA             Get well average coordintanes and pressure value.
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
CA  LINKAGE:   int bblCalculateCoordinatesOfWellReservoirs(item, arg, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  item        I     void *  Well pressure data pointer
CA  arg         I     void *  Null
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
C   29MAY12  PT   SCR 20319 Original version
C
C
*/

int bblCalculateCoordinatesOfWellReservoirs(void *item, void *arg, int *ier) {
	TllList it;
	int i, cnt = 1;
	double minz;	
	RESERVOIR_PRESS_DATA *min = NULL, *curReservoirPressData;
	int firstPoint = TRUE, onePoint = FALSE;
	double prevX, prevY, prevZ, prevPres, curX, curY, curZ, curPres, sumZ, dZ, sumX, sumY, sumPres;
	WELL_PRESS_DATA *wellPressData = (WELL_PRESS_DATA *)item;

	tllForEach(&wellPressData->pressureDataForWellReservoirs, bblCalculateReservoirCoordinates, NULL, NULL, ier);

	wellPressData->avgPressure = DPINDT;
	wellPressData->avgX = DPINDT;
	wellPressData->avgY = DPINDT;

	/* Do not sort empty list */

	if (!wellPressData->pressureDataForWellReservoirs)
		return FALSE;

	/* Sort well reservoir list by depth */
  
	for(i=0;i<cnt;i++) {
		it = wellPressData->pressureDataForWellReservoirs;		
		minz=DPINDT; 
		min = NULL;
		cnt = 0;
		while (it) {
			
			curReservoirPressData = (RESERVOIR_PRESS_DATA*)it->element;	   
     
			if ((!min || curReservoirPressData->z<minz) && cnt>=i) {
				min =  curReservoirPressData;
				minz = curReservoirPressData->z;
			}
			cnt++;
			it = it->next;
		}  
		tllRemove(&wellPressData->pressureDataForWellReservoirs,min,ier);
		tllAdd(&wellPressData->pressureDataForWellReservoirs,min,ier);     
	}

	/* Calculate average values */

	sumX = 0;
	sumY = 0;
	sumZ = 0;
	sumPres = 0;

	for ( it=(wellPressData->pressureDataForWellReservoirs); it; it=it->next ) { \
		RESERVOIR_PRESS_DATA * reservoirPressData = (RESERVOIR_PRESS_DATA *)it->element;

		curPres = reservoirPressData->pressure;
		curX = reservoirPressData->x;
		curY = reservoirPressData->y;
		curZ = reservoirPressData->z;

		if (curPres < DPCHEK && curX < DPCHEK && curY < DPCHEK && curZ < DPCHEK ) {

			if (!firstPoint) {
				dZ = curZ - prevZ;
				if (dZ == 0.0) dZ = 0.1;
				sumZ += dZ;

				sumX += dZ * (curX + prevX)/2;
				sumY += dZ * (curY + prevY)/2;
				sumPres += dZ * (curPres + prevPres)/2;

				onePoint = FALSE;
			} else {
				firstPoint = FALSE;
				onePoint = TRUE;
			}
			prevPres = reservoirPressData->pressure;
			prevX = reservoirPressData->x;
			prevY = reservoirPressData->y;
			prevZ = reservoirPressData->z;
		
		}

	}

	if (onePoint) {
		wellPressData->avgPressure = prevPres;
		wellPressData->avgX = prevX;
		wellPressData->avgY = prevY;
	}
	else if (sumZ == 0.0) {
		wellPressData->avgPressure = DPINDT;
		wellPressData->avgX = DPINDT;
		wellPressData->avgY = DPINDT;
	}
	else {
		wellPressData->avgPressure = sumPres / sumZ;
		wellPressData->avgX = sumX / sumZ;
		wellPressData->avgY = sumY / sumZ;
	}

	return FALSE;
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblCreatePressureCP
CA
CA
CA  FUNCTION:  Create pressure control point (tll version).
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
CA  LINKAGE:   int bblCreatePressureCP(item, arg, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  item        I     void *  Well pressure data pointer
CA  arg         I     void *  Pressure map data
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
C   29MAY12  PT   SCR 20319 Original version
C   19NOV12  PT   SCR 20319 Split control point set into two sets: wells 
C                 and border
C
C
*/

int bblCreatePressureCP(void *item, void *arg, int *ier) {
	int subsetKey;
	PROD_WELL *wp;	
	WELL_PRESS_DATA *wellPressData = (WELL_PRESS_DATA *)item;
	PRESS_MAP_DATA *pressureMapData = (PRESS_MAP_DATA *)arg;

	wp = wellPressData->prodWell;

	if (wellPressData->avgPressure < DPCHEK) {

		bblAddControlPoint(&pressureMapData->wellsCps, pressureMapData->groupName, pressureMapData->setName, 
		                   wp->well->name, wellPressData->avgX,
		                   wellPressData->avgY, wellPressData->avgPressure,
		                   &pressureMapData->cpWellsGroupKey, &pressureMapData->cpWellsSetKey, &subsetKey, ier);
		if (*ier != SUCCESSFUL) {
			ohnooo_ (ier, "bbl_readproduction: bblAddControlPoint failed");
			return FALSE;
		}

	}

	return FALSE;
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblShowPressureSurface
CA
CA
CA  FUNCTION:  Create and display pressure surface.
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
C   REVISED:
C
C   29MAY12  PT   SCR 20319 Original version
C   19NOV12  PT   SCR 20319 Split control point set into two sets: wells 
C                 and border
C   13MAY13  PT   SCR 20319 Remove data displaying.
C
C
*/

void bblShowPressureSurface(PRESS_MAP_DATA *pressureMapData, int *ier) {
	SURFACE_GROUP *surfaceGroup;
	SURFACE_SET *surfaceSet;
	double xMinAOI, xMaxAOI, yMinAOI, yMaxAOI;
	int numcols, numrows;

	if (!pressureMapData->wellsCps)
		return;

	bblGetSurfaceAOI(pressureMapData, &xMinAOI, &xMaxAOI, &yMinAOI, &yMaxAOI, ier);
	ERROR_CHECK("bblShowPressureSurface: bblGetSurfaceAOI error")


	xMinAOI = floor(xMinAOI/500)*500;
	xMaxAOI = ceil(xMaxAOI/500)*500;
	numcols = (xMaxAOI - xMinAOI)/50 + 1;

	yMinAOI = floor(yMinAOI/500)*500;
	yMaxAOI = ceil(yMaxAOI/500)*500;
	numrows = (yMaxAOI - yMinAOI)/50 + 1;

	bblCreateSurface(pressureMapData->pyGroupKey, pressureMapData->pySetKey,
	                 pressureMapData->cpWellsGroupKey, pressureMapData->cpWellsSetKey,
	                 pressureMapData->cpBorderGroupKey, pressureMapData->cpBorderSetKey,
	                 numcols, numrows,
	                 xMinAOI, xMaxAOI, yMinAOI, yMaxAOI,
	                 pressureMapData->groupName, pressureMapData->setName,
	                 &surfaceGroup, &surfaceSet, ier);
	ERROR_CHECK("bblShowPressureSurface: bblCreateSurface error")
}

/*
C
C   18JUL12  PT   SCR 20319 Original version
C   19NOV12  PT   SCR 20319 Split control point set into two sets: wells 
C                 and border
C
*/

void bblUseBorderPolygon(PRESS_MAP_DATA *pressureMapData, int *ier) {
	int groupKey, setKey, i, pointIndex;
	double x, y, pressure;
	POLYGON_SET *sp;
	POLYGON_SUBSET *currentSubset;
	POLYGON_SUBSET_VALUES *currentValue;

	int alreadyLoaded;

	if (BubbleSetup.pressurePolygonSldnid > 0) {

		mdbGetMapSetKeyAndParamKey( BubbleSetup.pressurePolygonSldnid, &groupKey, &setKey, ier); 
		ERROR_CHECK( "bblUseBorderPolygon: mdbGetMapSetKeyAndParamKey failed")

		sp = mdafps( groupKey, setKey, ier );
		alreadyLoaded = (sp != NULL);

		if (!alreadyLoaded) {
			sp = mdbraps(groupKey, setKey, ier);
			ERROR_CHECK( "bblUseBorderPolygon: mdbrass failed")
		}

		pointIndex = 0;
		currentSubset = sp->first;
		while(currentSubset) {
			currentValue = currentSubset->polygonValues;
			while(currentValue) {
				
				for(i = 0; i < currentValue->nPolygonPoints; i++) {
					int subsetKey;
					char subsetName[100];

					pointIndex++;
					sprintf(subsetName, "Border%d", pointIndex);

					x = currentValue->xPolygonPoint[i];
					y = currentValue->yPolygonPoint[i];
					pressure = BubbleSetup.borderPressureValue;
					bblAddControlPoint(&pressureMapData->borderCps, pressureMapData->borderGroupName, pressureMapData->borderSetName,
					                   subsetName, x, y, pressure,
					                   &pressureMapData->cpBorderGroupKey, &pressureMapData->cpBorderSetKey, &subsetKey, ier);
					ERROR_CHECK( "bblUseBorderPolygon: bblAddControlPoint failed")
				}
				currentValue = currentValue->next;
			}
			currentSubset = currentSubset->next;
		}

		pressureMapData->pyGroupKey = groupKey;
		pressureMapData->pySetKey = setKey;

	} else {
		pressureMapData->pyGroupKey = 0;
		pressureMapData->pySetKey = 0;
	}


}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblCreatePressureMap
CA
CA
CA  FUNCTION:  Create pressure map.
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
C   REVISED:
C
C   29MAY12  PT   SCR 20319 Original version
C   19NOV12  PT   SCR 20319 Split control point set into two sets: wells 
C                 and border
C
C
*/

void bblCreatePressureMap(int *ier) {
	PRESS_MAP_DATA pressureMapData;

	/* set group name and set name for wells control point set */
	snprintf(pressureMapData.groupName,sizeof(pressureMapData.groupName),"Pressure %s",BubbleSetup.findat_text);
	snprintf(pressureMapData.setName,sizeof(pressureMapData.setName),BubbleSetup.reservoir);

	/* set group name and set name for border control point set */
	snprintf(pressureMapData.borderGroupName,sizeof(pressureMapData.borderGroupName),"Pressure %s",BubbleSetup.findat_text);
	snprintf(pressureMapData.borderSetName,sizeof(pressureMapData.borderSetName),"Border %s",BubbleSetup.reservoir);

	/* init pressure map data */
	pressureMapData.pressureDataForWells = NULL;
	pressureMapData.wellsCps = NULL;
	pressureMapData.borderCps = NULL;
	pressureMapData.cpBorderGroupKey = 0;
	pressureMapData.cpBorderSetKey = 0;
	pressureMapData.pyGroupKey = 0;
	pressureMapData.pySetKey = 0;

	/* read pressure from data base */
	tllForEach(&production_wells, bblReadPressure, NULL, &pressureMapData, ier);
	ERROR_CHECK("bblCreatePressureMap: tllForEach error")

	tllForEach(&pressureMapData.pressureDataForWells, bblCalculateCoordinatesOfWellReservoirs, NULL, &pressureMapData, ier);
	ERROR_CHECK("bblCreatePressureMap: tllForEach error")

	/* create control point set */
	tllForEach(&pressureMapData.pressureDataForWells, bblCreatePressureCP, NULL, &pressureMapData, ier);
	ERROR_CHECK("bblCreatePressureMap: tllForEach error")

	/* add points on border polygon to control point set */
	bblUseBorderPolygon(&pressureMapData, ier);
	ERROR_CHECK("bblCreatePressureMap: bblShowPressureSurface error")

	/* create surface */
	bblShowPressureSurface(&pressureMapData, ier);
	ERROR_CHECK("bblCreatePressureMap: bblShowPressureSurface error")

	/* free pressure map data */

	tllFreeList(&pressureMapData.pressureDataForWells, bblFreeWellPressureData, ier);
	ERROR_CHECK("bblCreatePressureMap: tllFreeList error")

}

/*
C
C   18JUL12  PT   SCR 20319 Original version
C
*/

int bblFindReservoirPressData(void *resPressData, void *resName, int *ier)
{
	*ier = SUCCES;
	return !strcmp(((RESERVOIR_PRESS_DATA*)resPressData)->reservoirName , (char *) resName);
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblReadPressure
CA
CA
CA  FUNCTION:  Read pressure data from database (tll version).
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
CA  LINKAGE:   int bblReadPressure(item, arg, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  item        I     void *  Production well pointer
CA  arg         I     void *  Pressure map data
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
C   29MAY12  PT   SCR 20319 Original version
C   05APR13  PT   SCR 20319 Make it work on sqlite: use sqlcxd/sqldcx
C   18APR13  PT   SCR 20319 Replace datadmg with tdmded.
C
C
*/

int bblReadPressure(void *item, void *arg, int *ier) {
	PROD_WELL *wp;
	Database *link;
	int Index;
	double pres;
	char start_time[15], end_time[15];

	double stadat, findat;

	int iprcnt;

	char tigZonationName[41], topZoneName[41], baseZoneName[41], reservoirName[41];

	WELL_PRESS_DATA *well_press_data;
	PRESS_MAP_DATA *pressureMapData;

	pressureMapData = (PRESS_MAP_DATA *)arg;

	if(!GlobalCount) GlobalCount=1;
	iprcnt = 100.0 * GlobalIndex/(float)GlobalCount;
	mccipu_(&iprcnt, ier);
	if(*ier != SUCCES) {
		ohnooo_(ier, "bbl_readproduction: mccipu failed");
		*ier = SUCCES;
	}
	GlobalIndex ++; 


	link  = PRJ_LINK;

	wp = (PROD_WELL*)item;  

	if(!wp) {
		*ier = 10000;
		ohnooo_ (ier, "bbl_readproduction: Invalid well pointer");
		return FALSE;
	}


	sqlcmd(link, " select p_trpr.data_value, ");
	sqlcmd(link, " reservoir_part.tig_zonation_key, ");
	sqlcmd(link, " reservoir_part.tig_top_zone_key, ");
	sqlcmd(link, " reservoir_part.tig_base_zone_key, ");
	sqlcmd(link, " reservoir_part.reservoir_part_code, ");
	sqlcmd(link, " %s, ", sqldcx(link,"surv_meas.start_time"));
	sqlcmd(link, " %s ", sqldcx(link,"surv_meas.end_time"));

	sqlcmd(link, " from other_prod_act, pfnu_prod_act_x, reservoir_part, wellbore_intv, wellbore, well, tig_well_history,");
	sqlcmd(link, " wtst_meas surv_meas, wtst_meas surv_data, p_trpr");

	sqlcmd(link, " where");

	sqlcmd(link, " p_trpr.bsasc_source = 'Max Shut In' and");
	sqlcmd(link, " p_trpr.activity_s = surv_meas.wtst_meas_s and");

	sqlcmd(link, " surv_meas.containing_act_s = surv_data.wtst_meas_s and");

	sqlcmd(link, " surv_data.wtst_meas_s = other_prod_act.containing_act_s  and");
	sqlcmd(link, " other_prod_act.other_prod_act_s = pfnu_prod_act_x.production_act_s and ");
	sqlcmd(link, " other_prod_act.bsasc_source = 'SpecialSurveyData' and reservoir_part.reservoir_part_s=pfnu_prod_act_x.pfnu_s and");

	sqlcmd(link, " p_trpr.data_value > 0 and"); 

	sqlcmd(link, " reservoir_part.reservoir_part_code in (%s) and", BubbleSetup.reservoir);
	sqlcmd(link, " wellbore_intv.geologic_ftr_s = reservoir_part.reservoir_part_s and");
	sqlcmd(link, " wellbore.wellbore_s=wellbore_intv.wellbore_s and");
	sqlcmd(link, " well.well_s=wellbore.well_s and");
	sqlcmd(link, " tig_well_history.tig_latest_well_name=well.well_id and");
	sqlcmd(link, " tig_well_history.DB_SLDNID = %d", wp->well->sldnid);
	sqlcmd(link, " order by surv_meas.start_time, surv_meas.end_time");
  

	Index = 1;
	sqlbnd(link, Index++, SQL_DOUBLE, 0, &pres);
	sqlbnd(link, Index++, SQL_CHARACTER, sizeof(tigZonationName), tigZonationName);
	sqlbnd(link, Index++, SQL_CHARACTER, sizeof(topZoneName), topZoneName);
	sqlbnd(link, Index++, SQL_CHARACTER, sizeof(baseZoneName), baseZoneName);
	sqlbnd(link, Index++, SQL_CHARACTER, sizeof(reservoirName), reservoirName);
	sqlbnd(link, Index++, SQL_CHARACTER, sizeof(start_time), start_time);
	sqlbnd(link, Index++, SQL_CHARACTER, sizeof(end_time), end_time);


	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bbl_readproduction: Failed to receive data row");
		return FALSE;
	}



	well_press_data = (WELL_PRESS_DATA *)malloc(sizeof(WELL_PRESS_DATA));
	memset(well_press_data, 0, sizeof(WELL_PRESS_DATA));

	well_press_data->prodWell = wp;

	tllAdd(&pressureMapData->pressureDataForWells, well_press_data, ier);
	ERROR_CHECK_RETURN("bbl_readproduction: tllAdd error",FALSE)


	while(sqlnxt(link)){
		int fmt_flg = 0;

		tdmded_(start_time, &fmt_flg, &stadat, ier);
		ERROR_CHECK_RETURN("bblReadPressure: tdmded (1) failed", FALSE)

		tdmded_(end_time, &fmt_flg, &findat, ier);
		ERROR_CHECK_RETURN("bblReadPressure: tdmded (2) failed", FALSE)

		if((stadat >= BubbleSetup.stadat && stadat <= BubbleSetup.findat) 
		   || (findat >= BubbleSetup.stadat && findat <= BubbleSetup.findat)) {
			RESERVOIR_PRESS_DATA *reservoirPressData;

			reservoirPressData = (RESERVOIR_PRESS_DATA *)
			              tllFind(&well_press_data->pressureDataForWellReservoirs,
			              bblFindReservoirPressData, reservoirName, ier);
			ERROR_CHECK_RETURN("bbl_readproduction: tllFind returned error",FALSE)


			if (!reservoirPressData) {
				reservoirPressData = (RESERVOIR_PRESS_DATA *)malloc(sizeof(RESERVOIR_PRESS_DATA));

				tllAdd(&well_press_data->pressureDataForWellReservoirs, reservoirPressData, ier);
				ERROR_CHECK_RETURN("bbl_readproduction: tllAdd error",FALSE)

			}

			
			memset(reservoirPressData, 0, sizeof(RESERVOIR_PRESS_DATA));

			reservoirPressData->parent = well_press_data;

			reservoirPressData->pressure = pres;

			strcpy(reservoirPressData->tigZonationName, tigZonationName);
			strcpy(reservoirPressData->topZoneName, topZoneName);
			strcpy(reservoirPressData->baseZoneName, baseZoneName);
			strcpy(reservoirPressData->reservoirName, reservoirName);

			ohNooo(200000002, "Read pressure data: %s %s %lf %s %s", wp->well->name, reservoirName, pres, start_time, end_time);

		}
	}
 
	return FALSE;
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblGetSurfaceAOI
CA
CA
CA  FUNCTION:  Get area of interest for pressure surface.
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
C   REVISED:
C
C   29MAY12  PT   SCR 20319 Original version
C   19NOV12  PT   SCR 20319 Split control point set into two sets: wells 
C                 and border
C
C
*/

void bblGetSurfaceAOI(PRESS_MAP_DATA *pressureMapData,
                      double *xMinAOI,
                      double *xMaxAOI,
                      double *yMinAOI,
                      double *yMaxAOI,
                      int *ier) {

	/* find the minimum and maximum x and y in a list of wells control points */
	mdaLimitCP(pressureMapData->cpWellsGroupKey, pressureMapData->cpWellsSetKey, xMinAOI, xMaxAOI, yMinAOI, yMaxAOI, ier);
	ERROR_CHECK("bblGetSurfaceAOI: mdaLimitCP error")

	if (pressureMapData->borderCps) {
		double xMinBorder, xMaxBorder, yMinBorder, yMaxBorder;

		/* find the minimum and maximum x and y in a list of border control points */
		mdaLimitCP(pressureMapData->cpBorderGroupKey, pressureMapData->cpBorderSetKey,
		           &xMinBorder, &xMaxBorder, &yMinBorder, &yMaxBorder, ier);
		ERROR_CHECK("bblGetSurfaceAOI: mdaLimitCP error")

		if (*xMinAOI > xMinBorder)
			*xMinAOI = xMinBorder;

		if (*xMaxAOI < xMaxBorder)
			*xMaxAOI = xMaxBorder;

		if (*yMinAOI > yMinBorder)
			*yMinAOI = yMinBorder;

		if (*yMaxAOI < yMaxBorder)
			*yMaxAOI = yMaxBorder;
	}

	/* cater for the case of only one well */
	if ( (*xMaxAOI - *xMinAOI) < TINY ) {
		*xMinAOI -= 5000.0;
		*xMaxAOI += 5000.0;
	}
		
	if ( (*yMaxAOI - *yMinAOI) < TINY ) {
		*yMinAOI -= 5000.0;
		*yMaxAOI += 5000.0;
	}
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblFreeWellPressureData
CA
CA
CA  FUNCTION:  Free well pressure data (tll version).
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
CA  LINKAGE:   int bblFreeWellPressureData(item, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  item        I     void *  Well pressure data pointer to be freed
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
C   18JUL12  PT   SCR 20319 Original version
C
C
*/

void bblFreeWellPressureData(void *item, int *ier)
{
	WELL_PRESS_DATA *data;

	data = (WELL_PRESS_DATA *) item;

	tllFreeList(&data->pressureDataForWellReservoirs, TLL_FREE, ier);
	ERROR_CHECK("bblCreatePressureMap: tllFreeList error")

	free(data);
}
