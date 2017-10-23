
/*
C-------------------------------------------------------------------
C    Copyright (C) 2008-2013 Tigress Limited
C    All rights reserved.
C-------------------------------------------------------------------
 
*/

#include <tigress/tigdef.h>
#include <tigress/tem.h>
#include <tigress/tcm.h>

#include <mapping/bbl_ext.h>
#include "bbl_int.h"


static int reservoirNumbers[100];
static char reservoirIds[100][100];
static int reservoirCount;
static char *reservoirElementKeys = NULL;


static TigList(NAMES)* intersectReservoirs(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier);
static TigList(NAMES)* subtractReservoirs(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier);
static int isEqualReservoirs(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier);
static void readReservoirOrders(int *ier);
static int getReservoirOrder(char * reservoir, int *ier);
static int isLower(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier);
static int isUpper(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier);
static int find_reservoirs(void *item, void *arg, int *ier);
static void bblCalcReservoirMovingAndMultipleReservoirProduction(PROD_WELL *productionWell, char *startDate, char *finalDate, int *ier);
static void bblSplitPhaseFilter(char *phaseFilter, char **generalPhaseFilterPtr,
                                char **reconciledPhaseFilterPtr);
static int bbl_wellsymbol(PROD_WELL *prodWell, char *findat, char *cmpl_id, 
                          int *ier);
static void bblGetWellStrProperty(int sldnid, char *findat,
                                  char *propertyType, char *propertyValue, int *ier);



int ListEnum(void *item, void *arg, int *ier)
{
  int *count;

  count = (int*)arg;

  *count = *count + 1;

  return FALSE;
}


int bblIsNewDataModel() {
	return TRUE;
}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bbl_getreservoirs
CA
CA
CA  FUNCTION:  Fills list of reservoir names and return number of loaded reservoirs
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   long bbl_getreservoirs(ier)
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
C   26OCT05       Original version
C   17MAY13  PT   SCR 20319 Add new data model reading.
*/

int bbl_getreservoirs_old_mod(int *ier)
{
  Database *link;
  char name[40];  
  int Index;
  NAMES *nm;
  int count=0;

  if(tllHead(&reservoirs, ier)) {    
    tllFreeList(&reservoirs, TLL_FREE, ier);
    reservoirs = NULL;
  }

  link = PRJ_LINK;
  sqlcmd (link, "select distinct well_completion_id ");
  sqlcmd (link, "from   well_completion ");
  sqlcmd (link, "where  r_existence_kd_nm = 'actual' ");
  
  Index = 1;
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(name), name);
  
  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_getreservoirs: Failed to receive data row");
    return 0;
  }

  while(sqlnxt(link)){
    nm = malloc(sizeof(NAMES));
    memset(nm, 0, sizeof(NAMES));

    nm->selected = 0;
    strcpy(nm->name, name);

    tllAdd(&reservoirs, (char *)nm, ier);
    if (*ier != SUCCES) {
      ohnooo_(ier, "bbl_getreservoirs: tllAdd error");
      return 0;
    }

    count++;
  }

  return count;
}

int bbl_getreservoirs_new_mod(int *ier)
{
  Database *link;
  char name[40];  
  int Index;
  NAMES *nm;
  int count=0;

  if(tllHead(&reservoirs, ier)) {    
    tllFreeList(&reservoirs, TLL_FREE, ier);
    reservoirs = NULL;
  }

  link = PRJ_LINK;
  sqlcmd (link, "select reservoir_part_code ");
  sqlcmd (link, "from   reservoir_part ");
  sqlcmd (link, "where  entity_type_nm = 'RESERVOIR_ZONE' ");
  
  Index = 1;
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(name), name);
  
  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_getreservoirs: Failed to receive data row");
    return 0;
  }

  while(sqlnxt(link)){
    nm = malloc(sizeof(NAMES));
    memset(nm, 0, sizeof(NAMES));

    nm->selected = 0;
    strcpy(nm->name, name);

    tllAdd(&reservoirs, (char *)nm, ier);
    if (*ier != SUCCES) {
      ohnooo_(ier, "bbl_getreservoirs: tllAdd error");
      return 0;
    }

    count++;
  }

  return count;
}

int bbl_getreservoirs(int *ier) {
	if (bblIsNewDataModel())
		return bbl_getreservoirs_new_mod(ier);
	else
		return bbl_getreservoirs_old_mod(ier);
}

const char *bblGetReservoirsSqlFilter_new_mod(const char *reservoirNames, int *ier) {
	Database *link = PRJ_LINK;
	int sqlFilterSize = 0;
	char *reservoir_s;
	TigList(NAMES) reservoirKeyList = NULL;
	NAMES *nm;

	sqlcmd (link, "select wellbore_intv.geologic_ftr_s ");
	sqlcmd (link, "from earth_pos_rgn, wellbore_intv, topological_rel, reservoir_part ");
	sqlcmd (link, "where earth_pos_rgn_s = topological_rel.prim_toplg_obj_s ");
	sqlcmd (link, "and wellbore_intv_s = topological_rel.sec_toplg_obj_s " );
	sqlcmd (link, "and earth_pos_rgn.geologic_ftr_s = reservoir_part_s ");
	sqlcmd (link, "and entity_type_nm = 'RESERVOIR_ZONE' ");
	sqlcmd (link, "and reservoir_part_code in (%s)", reservoirNames);

	int col = 0;
	sqlbnd(link, ++col, SQL_CHARPTR, 0, &reservoir_s);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bblGetReservoirsSqlFilter: Failed to receive data row");
		return NULL;
	}

	while (sqlnxt(link))
	{
		nm = (NAMES *)malloc(sizeof(NAMES));
		memset(nm, 0, sizeof(NAMES));
		nm->selected = TRUE;
		strcpy(nm->name, reservoir_s);
		sqlFilterSize += strlen(reservoir_s) + 10;

		tllAdd(&reservoirKeyList, nm, ier);
		if (*ier != SUCCES) {
			ohnooo_(ier, "bblGetReservoirsSqlFilter: tllAdd error");
			return NULL;
		}

		free(reservoir_s);
	}

	reservoirElementKeys = realloc(reservoirElementKeys, sqlFilterSize);
	NamesToString(reservoirKeyList, reservoirElementKeys, "'", ",", "'");
	tllFreeList(&reservoirKeyList, TLL_FREE, ier);

	return reservoirElementKeys;
}

const char *bblGetReservoirsSqlFilter(const char *reservoirNames, int *ier) {
	if (bblIsNewDataModel())
		return bblGetReservoirsSqlFilter_new_mod(reservoirNames, ier);
	else
		return reservoirNames;
}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      find_wells
CA
CA
CA  FUNCTION:  tllFind callback function to find Production Well  by 
CA             given well sldnid
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   int find_wells(item, arg, ier)
CA
CA
CA  Argument    Use   Type    Description
CA  name
CA  --------    ---   ----    -----------
CA  item        I     void *  Item in list to test against.
CA  arg         I     void *  Extra user-supplied argument as
CA                            passed in to tllFind.
CA  ier         O     long *  Error Return code.
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   30JAN07       Original version
C   13MAY13  PT   SCR 20319 Check sldnid field of PROD_WELL instead of MAP_WELL
*/

int find_wells(void *item, void *arg, int *ier)
{
  PROD_WELL *node;
  int *id;

  node = (PROD_WELL*)item;
  id = (int*)arg;
  
  return node->sldnid == *id;
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      LoadWell
CA
CA
CA  FUNCTION: tllForEach callback does create MAP_WELL and adds it into loaded_wells list
CA
CA
CA  APPLICATION/SUBSYSTEM:  Bubble maps
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   int LoadWell(void *item, void *arg, long *ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  item         I    char *  well_id
CA  arg          I    char *  unused argument
CA  ier          O    long *  Error return code
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   27OCT05       Original version
*/

int LoadWell(void *item, void *arg, int *ier)
{
  NAMES *nm;
  int iprcnt;

  if(!item) return FALSE;

  nm = (NAMES*)item;

  if(!GlobalCount) GlobalCount=1;
  iprcnt = 100.0 * GlobalIndex/(float)GlobalCount;
  mccipu_(&iprcnt, ier);
  GlobalIndex += 0.5;

  LoadWellByName(nm->name, ier);

  return FALSE;
}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      LoadWellByName
CA
CA
CA  FUNCTION:  By given name create MAP_WELL and adds it into loaded_wells list
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   void LoadWellByName(well_name, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  well_name    I    char *  well_id
CA  ier          O    long *  Error return code
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   27OCT05       Original version
C   11MAR12  PT   SCR 20319 Improve getting latitude and longitude.
C   18JUL12  PT   SCR 20319 Check latitude and longitude before reading well structure
C   16AUG12  PT   SCR 20319 Move symbolNumber and isCurrentReservoir calculation to bbl_readproduction
C   06DEC12  PT   SCR 20319 Read ebwdbCode
C   31JAN13  PT   SCR 20319 Use bblReadProdWellData for ebwdbCode reading.
C                 Add map well to the list of loaded wells if production well
C                 is already loaded.
C   26APR13  PT   SCR 20319 Move part of code to bblReadMapWell.
C   13MAY13  PT   SCR 20319 Set sldnid field of PROD_WELL
C   15MAY13  PT   SCR 20319 Use bblReadWellData instead of bblReadProdWellData
*/

void LoadWellByName(char *well_name, int *ier)
{
	MAP_WELL *wp;
	PROD_WELL *pwp;
	int id;

	tcmwid_(well_name, "", &id, ier);
	if (*ier != SUCCES) {
		ohnooo_(ier, "LoadWellByName: tcmwid error");
		*ier = SUCCES;
		return;
	}

	wp = bblReadMapWell(id, ier);
	ERROR_CHECK("LoadWellByName: bblReadMapWell failed")

	if (!wp)
		return;

	pwp = tllFind(&production_wells, &find_wells, &id, ier);

	if(!pwp) {
		pwp = (PROD_WELL*)malloc(sizeof(PROD_WELL));      
		if(!pwp) {
			*ier = LGLEV3;
			ohnooo_(ier, "LoadWellByName: Production well memory allocate error");
			return ;
		}

		memset(pwp, 0, sizeof(PROD_WELL));

		tllAdd(&production_wells, (char*)pwp, ier);
	}
	else {
		ohNooo(200000002,"LoadWellByName: Production well %s is found \n", wp->name);
	}

	pwp->well = wp;
	pwp->sldnid = wp->sldnid;
	bblReadWellData(wp->sldnid, NULL, NULL,  pwp->well->name, ier);
	ERROR_CHECK("LoadWellByName: bblReadWellData failed")
}


/*
C   07DEC12  PT   SCR 20319 Original version
C   31JAN13  PT   SCR 20319 Increase sizes of strings.
C   12FEB13  PT   SCR 20319 Rename ebwdbCode to epwdbCode.
C   15MAY13  PT   SCR 20319 Update prototype. Read APINumber
C   21MAY13  PT   SCR 20319 Add new data model reading.
C   03JUL13  PT   SCR 20319 Change 'section' property name to 'workshop section'
*/

void bblReadWellData_old_mod(int sldnid, char *workshop, char *section, char *name, int *ier)
{
    int delFlag = 0, getSet, parameterId;
    int iDummy;
    float fDummy;
    char geodeID[11], epwdbSipm[16], platformCode[21], clientName[21];
    char holeShortName[9];
    char epwdbCode[21], APINumber[21];
    char wellOperator[41], wellName[41];
    OBJECT *wellHistHandle;


    temget_( &sldnid, &wellHistHandle, ier);
    if (*ier != SUCCES) {
      ohnooo_(ier, "bblReadWellData: temget error");
      return;
    }


    /* get well history details to extract epwdbCode */
    getSet = 1;
    temwel_( &wellHistHandle, &getSet, &iDummy, &iDummy, &fDummy, geodeID,
             epwdbCode, platformCode, &iDummy, &iDummy, holeShortName,
             clientName, &fDummy, epwdbSipm, &iDummy, ier);
    if (*ier != SUCCES) {
      ohnooo_(ier, "bblReadWellData: temwel error");
      return;
    }
    tdmzap(epwdbCode, sizeof(epwdbCode)-1);


    /* get the API number */
    parameterId = 5; /*API_NO_ID_FLAG*/
    temwac_(&wellHistHandle, &getSet, &parameterId, APINumber, ier);
    if (*ier != SUCCES) {
      ohnooo_( ier, "bblReadWellData: temwac error");
      return;
    }
    tdmzap (APINumber, sizeof(APINumber)-1);



    /* get the well name */
    tcmwnm_( &sldnid, wellName, wellOperator, ier);
    if ( *ier != SUCCES ) 
    {
        ohnooo_(ier, "bblReadWellData: tcmwnm error");
        return;
    }
    tdmzap( wellName, sizeof(wellName)-1);


    temdel_(&wellHistHandle, &delFlag, ier);
    if (*ier != SUCCES) {
      ohnooo_(ier, "bblReadWellData: temdel error");
      return;
    }

    if (workshop)
      strcpy(workshop, epwdbCode);

    if (section)
      strcpy(section, APINumber);

    if (name)
      strcpy(name, wellName);
}

void bblReadWellData_new_mod(int sldnid, char *workshop, char *section, char *name, int *ier)
{
	char wellOperator[41], wellName[41];

	if (workshop) {
		bblGetWellStrProperty(sldnid, NULL, "workshop", workshop, ier);
		ERROR_CHECK("bblReadWellData: bblGetWellStrProperty failed")
	}

	if (section) {
		bblGetWellStrProperty(sldnid, NULL, "workshop section", section, ier);
		ERROR_CHECK("bblReadWellData: bblGetWellStrProperty failed")
	}

	/* get the well name */
	tcmwnm_( &sldnid, wellName, wellOperator, ier);
	if ( *ier != SUCCES ) 
	{
		ohnooo_(ier, "bblReadWellData: tcmwnm error");
		return;
	}
	tdmzap( wellName, sizeof(wellName)-1);

	if (name)
		strcpy(name, wellName);

}

void bblReadWellData(int sldnid, char *workshop, char *section, char *name, int *ier)
{
	if (bblIsNewDataModel())
		bblReadWellData_new_mod(sldnid, workshop, section, name, ier);
	else
		bblReadWellData_old_mod(sldnid, workshop, section, name, ier);
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bbl_getwellfond
CA
CA
CA  FUNCTION:  Read current production by given final date completion ids and wells ids
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   void bbl_getwellfond(findat, cmpl_id, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  findat       I    char *  Final date
CA  cmpl_id      I    char *  Reservoir name
CA  ier          O    long *  Error return code
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   22JUL04       Original version
C   14MAR13  PT   SCR 20319 Fix query for reading wells on reservoirs
C   05APR13  PT   SCR 20319 Make it work on sqlite: use sqlcxd/sqldcx
C   19APR13  PT   SCR 20319 Use mccGetParent to get parent widget for mccipr
C   21MAY13  PT   SCR 20319 Add new data model reading.
C
C
*/
int bbl_getwellfond_old_mod(char *findat, const char *cmpl_id, int *ier)
{
  Database *link;
  int Index;
  int count=0;
  NAMES *nm;
  char well_id[40];
  TigList(NAMES) wells=NULL;
  int iprcnt;  
  int parent;

  link = PRJ_LINK;

  parent = mccGetParent();
  
  mccipr_(&parent, _("Loading production wells"), ier);

  /*Get borehole count*/
  sqlcmd(link, " SELECT count(distinct WELL_COMPLETION.WELL_ID)");
  sqlcmd(link, "    FROM  well_completion,");
  sqlcmd(link, "    production_aloc,");
  sqlcmd(link, "    pfnu_prod_act_x");
  sqlcmd(link, "    WHERE PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S");
  sqlcmd(link, "      AND WELL_COMPLETION.WELL_COMPLETION_S  = PFNU_PROD_ACT_X.PFNU_S");
  sqlcmd(link, "      AND PRODUCTION_ALOC.START_TIME <= %s", sqlcxd(link, findat));
  sqlcmd(link, "      AND WELL_COMPLETION.WELL_COMPLETION_ID in (%s)", cmpl_id);

  sqlbnd(link, 1, SQL_INTEGER, 0, &GlobalCount);

  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_getwellfond: Failed to get row count");
    return 0;
  }

  while(sqlnxt(link)){
  }

  /*Get wells on reservoirs*/

  sqlcmd(link, " SELECT DISTINCT WELL_COMPLETION.WELL_ID");
  sqlcmd(link, "    FROM  well_completion,");
  sqlcmd(link, "    production_aloc,");
  sqlcmd(link, "    pfnu_prod_act_x,");
  sqlcmd(link, "      (SELECT");
  sqlcmd(link, "        WELL_COMPLETION.WELL_ID w_id,");
  sqlcmd(link, "        MAX(PRODUCTION_ALOC.START_TIME) max_time");
  sqlcmd(link, "      FROM  well_completion,");
  sqlcmd(link, "        production_aloc,");
  sqlcmd(link, "        pfnu_prod_act_x");
  sqlcmd(link, "      WHERE PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S");
  sqlcmd(link, "        AND WELL_COMPLETION.WELL_COMPLETION_S  = PFNU_PROD_ACT_X.PFNU_S");
  sqlcmd(link, "        AND PRODUCTION_ALOC.START_TIME <= %s", sqlcxd(link, findat));
  sqlcmd(link, "      GROUP BY WELL_COMPLETION.WELL_ID) md");
  sqlcmd(link, "    WHERE PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S");
  sqlcmd(link, "      AND WELL_COMPLETION.WELL_COMPLETION_S  = PFNU_PROD_ACT_X.PFNU_S");
  sqlcmd(link, "      AND PRODUCTION_ALOC.START_TIME = md.max_time");
  sqlcmd(link, "        AND PRODUCTION_ALOC.START_TIME <= %s", sqlcxd(link, findat));
  sqlcmd(link, "      AND WELL_COMPLETION.WELL_ID=md.w_id");
  sqlcmd(link, "      AND WELL_COMPLETION.WELL_COMPLETION_ID in (%s)", cmpl_id);

  Index = 1;
  sqlbnd(link, Index, SQL_CHARACTER, sizeof(well_id), well_id);

  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_getwellfond: Failed to receive data row");
    return 0;
  }
	
  GlobalIndex = 0.0;
  if(!GlobalCount) GlobalCount = 1;
  while(sqlnxt(link)){
    iprcnt = 100.0 * GlobalIndex/(float)GlobalCount;
    mccipu_(&iprcnt, ier);

    nm = malloc(sizeof(NAMES));
    strcpy(nm->name, well_id);
    
    tllAdd(&wells, (char*)nm, ier);
    count++;
    GlobalIndex += 0.5;
  }
  tllForEach(&wells, LoadWell, NULL, NULL, ier);
  mccipd_(ier);
   
  tllFreeList(&wells, TLL_FREE, ier);

  return count;
}

int bbl_getwellfond_new_mod(char *findat, const char *cmpl_id, int *ier)
{
	Database *link;
	int Index;
	int count=0;
	NAMES *nm;
	char well_id[40];
	TigList(NAMES) wells=NULL;
	int iprcnt;  
	int parent;

	link = PRJ_LINK;

	parent = mccGetParent();

	mccipr_(&parent, _("Loading production wells"), ier);

	/*Get borehole count*/
	sqlcmd(link, " SELECT count(distinct wellbore.WELL_ID)");
	sqlcmd(link, "    FROM  reservoir_part,");
	sqlcmd(link, "    wellbore_intv,");
	sqlcmd(link, "    wellbore,");
	sqlcmd(link, "    production_aloc,");
	sqlcmd(link, "    pfnu_prod_act_x");
	sqlcmd(link, "    WHERE PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S");
	sqlcmd(link, "      and production_aloc.bsasc_source = 'Reallocated Production'"); 
	sqlcmd(link, "      and reservoir_part.reservoir_part_s = pfnu_prod_act_x.pfnu_s");
	sqlcmd(link, "      AND PRODUCTION_ALOC.START_TIME <= %s", sqlcxd(link, findat));
	sqlcmd(link, "      and reservoir_part.reservoir_part_s in (%s)", cmpl_id);
	sqlcmd(link, "      and wellbore_intv.geologic_ftr_s = reservoir_part.reservoir_part_s");
	sqlcmd(link, "      and wellbore.wellbore_s=wellbore_intv.wellbore_s");

	sqlbnd(link, 1, SQL_INTEGER, 0, &GlobalCount);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bbl_getwellfond: Failed to get row count");
		return 0;
	}

	while(sqlnxt(link)){
	}

	/*Get wells on reservoirs*/

	sqlcmd(link, " SELECT DISTINCT wellbore.WELL_ID");
	sqlcmd(link, "    FROM  reservoir_part,");
	sqlcmd(link, "    wellbore_intv,");
	sqlcmd(link, "    wellbore,");
	sqlcmd(link, "    production_aloc,");
	sqlcmd(link, "    pfnu_prod_act_x,");
	sqlcmd(link, "      (SELECT");
	sqlcmd(link, "        wellbore.WELL_ID w_id,");
	sqlcmd(link, "        MAX(PRODUCTION_ALOC.START_TIME) max_time");
	sqlcmd(link, "      FROM  reservoir_part,");
	sqlcmd(link, "        wellbore_intv,");
	sqlcmd(link, "        wellbore,");
	sqlcmd(link, "        production_aloc,");
	sqlcmd(link, "        pfnu_prod_act_x");
	sqlcmd(link, "      WHERE PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S");
	sqlcmd(link, "        and production_aloc.bsasc_source = 'Reallocated Production'");
	sqlcmd(link, "        and reservoir_part.reservoir_part_s = pfnu_prod_act_x.pfnu_s");
	sqlcmd(link, "        and wellbore_intv.geologic_ftr_s = reservoir_part.reservoir_part_s");
	sqlcmd(link, "        and wellbore.wellbore_s=wellbore_intv.wellbore_s");
	sqlcmd(link, "        AND PRODUCTION_ALOC.START_TIME <= %s", sqlcxd(link, findat));
	sqlcmd(link, "      GROUP BY wellbore.WELL_ID) md");
	sqlcmd(link, "    WHERE PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S");
	sqlcmd(link, "      and production_aloc.bsasc_source = 'Reallocated Production'");
	sqlcmd(link, "      and reservoir_part.reservoir_part_s = pfnu_prod_act_x.pfnu_s");
	sqlcmd(link, "      AND PRODUCTION_ALOC.START_TIME = md.max_time");
	sqlcmd(link, "      AND PRODUCTION_ALOC.START_TIME <= %s", sqlcxd(link, findat));
	sqlcmd(link, "      AND wellbore.WELL_ID=md.w_id");
	sqlcmd(link, "      and reservoir_part.reservoir_part_s in (%s)", cmpl_id);
	sqlcmd(link, "      and wellbore_intv.geologic_ftr_s = reservoir_part.reservoir_part_s");
	sqlcmd(link, "      and wellbore.wellbore_s=wellbore_intv.wellbore_s");

	Index = 1;
	sqlbnd(link, Index, SQL_CHARACTER, sizeof(well_id), well_id);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bbl_getwellfond: Failed to receive data row");
		return 0;
	}

	GlobalIndex = 0.0;
	if(!GlobalCount) GlobalCount = 1;
	while(sqlnxt(link)){
		iprcnt = 100.0 * GlobalIndex/(float)GlobalCount;
		mccipu_(&iprcnt, ier);

		nm = malloc(sizeof(NAMES));
		strcpy(nm->name, well_id);

		tllAdd(&wells, (char*)nm, ier);
		count++;
		GlobalIndex += 0.5;
	}
	tllForEach(&wells, LoadWell, NULL, NULL, ier);
	mccipd_(ier);

	tllFreeList(&wells, TLL_FREE, ier);

	return count;
}

int bbl_getwellfond(char *findat, const char *cmpl_id, int *ier)
{
	if (bblIsNewDataModel())
		return bbl_getwellfond_new_mod(findat, cmpl_id, ier);
	else
		return bbl_getwellfond_old_mod(findat, cmpl_id, ier);
}


/*
C   22MAR12  PT   SCR 20319 Make res static.
*/

TigList(NAMES)* intersectReservoirs(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier) {
	static TigList(NAMES) res;
	TllList it1, it2;
	NAMES *name1, *name2, *name;
	res = NULL;
	it1 = *reservoirs1;
	while(it1) {
		name1 = (NAMES*)it1->element;
		if(name1->selected) {
			it2 = *reservoirs2;
			while(it2) {
				name2 = (NAMES*)it2->element;
				if (name2->selected && !strcmp(name1->name,name2->name)) {
					name = (NAMES*)malloc(sizeof(NAMES));
					name->selected = TRUE;
					strcpy(name->name, name1->name);
					tllAdd(&res,name,ier);
				}
				it2 = it2->next;
			}
		}
		it1 = it1->next;
	}
	return &res;
}

/*
C   22MAR12  PT   SCR 20319 Make res static.
*/

TigList(NAMES)* subtractReservoirs(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier) {
	static TigList(NAMES) res;
	TllList it1, it2;
	NAMES *name1, *name2, *name;
	int f;

	res = NULL;
	it1 = *reservoirs1;
	while(it1) {
		name1 = (NAMES*)it1->element;
		
		if(name1->selected) {
			it2 = *reservoirs2;
			f = FALSE;
			while(it2) {
				name2 = (NAMES*)it2->element;
				
				if (name2->selected && !strcmp(name1->name,name2->name)) {
					f = TRUE;					
				}
				it2 = it2->next;
			}
			if (!f) {
				name = (NAMES*)malloc(sizeof(NAMES));
				name->selected = TRUE;
				strcpy(name->name, name1->name);					
				tllAdd(&res,name,ier);
			}			
		}
		it1 = it1->next;
	}
	return &res;
}

int isEqualReservoirs(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier) {
	return (*subtractReservoirs(reservoirs1, reservoirs2, ier) == NULL &&
				*subtractReservoirs(reservoirs2, reservoirs1, ier) == NULL);
}


/*
C   21MAY13  PT   SCR 20319 Add new data model reading.
*/

void readReservoirOrders_old_mod(int *ier) {
	Database *link;
	int reservoirNumber, Index;
	char reservoirId[100];

	link  = PRJ_LINK;
	sqlcmd(link,"SELECT ");	
	sqlcmd(link,	"DTY.plast, DTY.PORDER ");
	sqlcmd(link,"FROM ");
	sqlcmd(link,	"DTY ");
	Index = 1;
	sqlbnd(link, Index++, SQL_CHARACTER,  sizeof(reservoirId), reservoirId);
	sqlbnd(link, Index++, SQL_INTEGER, 0, &reservoirNumber);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "readReservoirOrders: Failed to receive data row");		
		return;
	}
	reservoirCount = 0;
	while (sqlnxt(link)) {
		reservoirNumbers[reservoirCount] = reservoirNumber;
		strcpy(reservoirIds[reservoirCount],reservoirId);
		reservoirCount++;
	}
}

void readReservoirOrders_new_mod(int *ier) {
	Database *link;
	int index;
	char reservoirId[41], reservoirNumber[41];

	link  = PRJ_LINK;

	sqlcmd(link, "select reservoir_part.reservoir_part_code, ");
	sqlcmd(link, " p_equipment_fcl.string_value ");
	sqlcmd(link, " from p_equipment_fcl, equipment_insl, ");
	sqlcmd(link, " reservoir_part ");
	sqlcmd(link, "where reservoir_part.entity_type_nm = 'RESERVOIR_ZONE' ");
	sqlcmd(link, " and equipment_insl.equipment_item_s = p_equipment_fcl.object_s ");
	sqlcmd(link, " and reservoir_part.reservoir_part_s = equipment_insl.facility_s ");
	sqlcmd(link, " and p_equipment_fcl.bsasc_source = 'order no'");

	index = 1;
	sqlbnd(link, index++, SQL_CHARACTER, sizeof(reservoirId), reservoirId);
	sqlbnd(link, index++, SQL_CHARACTER, sizeof(reservoirNumber), reservoirNumber);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "readReservoirOrders: Failed to receive data row");		
		return;
	}

	reservoirCount = 0;
	while (sqlnxt(link)) {
		reservoirNumbers[reservoirCount] = atoi(reservoirNumber);
		strcpy(reservoirIds[reservoirCount],reservoirId);
		reservoirCount++;
	}
}

void readReservoirOrders(int *ier) {
	if (bblIsNewDataModel())
		readReservoirOrders_new_mod(ier);
	else
		readReservoirOrders_old_mod(ier);
}

int getReservoirOrder(char * reservoir, int *ier) {
	int i;
	for(i=0; i<reservoirCount; i++)
	if (!strcmp(reservoirIds[i],reservoir)) 
		return reservoirNumbers[i];
	return 0;	
}

int isLower(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier) {
	TllList it1, it2;
	NAMES *name1, *name2;	
	it1 = *reservoirs1;
	while(it1) {
		name1 = (NAMES*)it1->element;
		if(name1->selected) {
			it2 = *reservoirs2;
			while(it2) {
				name2 = (NAMES*)it2->element;
				if (name2->selected && getReservoirOrder(name1->name, ier)<=getReservoirOrder(name2->name, ier)) {
					return FALSE;					
				}
				it2 = it2->next;
			}		
		}
		it1 = it1->next;
	}
	return TRUE;
}

int isUpper(TigList(NAMES)* reservoirs1, TigList(NAMES)* reservoirs2, int *ier) {
	TllList it1, it2;
	NAMES *name1, *name2;	
	it1 = *reservoirs1;
	while(it1) {
		name1 = (NAMES*)it1->element;
		if(name1->selected) {
			it2 = *reservoirs2;
			while(it2) {
				name2 = (NAMES*)it2->element;				
				if (name2->selected && (getReservoirOrder(name1->name, ier)>=getReservoirOrder(name2->name, ier)))
					return FALSE;
				it2 = it2->next;
			}		
		}
		it1 = it1->next;
	}
	return TRUE;
}


int find_reservoirs(void *item, void *arg, int *ier)
{
  NAMES *node;
  char *id;

  node = (NAMES*)item;
  id = (char*)arg;
  
  return !strcmp(node->name , id);
}


/*
C   04APR13  PT   SCR 20319 Set lastReservoirs even if only one reservoir.
C   05APR13  PT   SCR 20319 Make it work on sqlite: use sqlcxd/sqldcx
C   18APR13  PT   SCR 20319 Replace datadmg with tdmded. Remove unused code
C   06MAY13  PT   SCR 20319 Init prevFindat and prevProdEndTime.
C   21MAY13  PT   SCR 20319 Add new data model reading.
*/

void bblCalcReservoirMovingAndMultipleReservoirProduction(PROD_WELL *productionWell, char *startDate, char *finalDate, int *ier) {
	Database *link;
	int Index;
	double prevFindat = -999.9, findat;
	char reservoirId[100], prodEndTime[100], prevProdEndTime[100] = "";
	int fmt_flg = 0;
	
	TigList(NAMES) resvs = NULL;
	TigList(NAMES) prevResvs = NULL;

	TigList(NAMES) multipleReservoirProductionResvs = NULL;
	NAMES *multipleReservoirProductionResv;

	productionWell->reservoirState = NO_MOVING;
	
	readReservoirOrders(ier);
	if (*ier != SUCCES) {
		ohnooo_ (ier, "calcReservoirMoving: readReservoirOrders failed");
		*ier = SUCCES;		
		return;
	}

	link  = PRJ_LINK;

	if (bblIsNewDataModel()) {

	sqlcmd(link, "SELECT ");	
	sqlcmd(link, "reservoir_part.reservoir_part_code, ");
	sqlcmd(link, "%s ", sqldcx(link,"PRODUCTION_ALOC.prod_end_time"));
	sqlcmd(link, "FROM ");
	sqlcmd(link, "reservoir_part, ");
	sqlcmd(link, "wellbore_intv, ");
	sqlcmd(link, "wellbore, ");
	sqlcmd(link, "well, ");
	sqlcmd(link, "tig_well_history, ");
	sqlcmd(link, "PFNU_PROD_ACT_X, ");
	sqlcmd(link, "PRODUCTION_ALOC ");
	sqlcmd(link, "WHERE ");
	sqlcmd(link, " production_aloc.PRODUCTION_ALOC_S = pfnu_prod_act_x.PRODUCTION_ACT_S ");
	sqlcmd(link, " and production_aloc.bsasc_source = 'Reallocated Production'");
	sqlcmd(link, " and reservoir_part.reservoir_part_s = pfnu_prod_act_x.pfnu_s");
	sqlcmd(link, " and wellbore_intv.geologic_ftr_s = reservoir_part.reservoir_part_s");
	sqlcmd(link, " and wellbore.wellbore_s=wellbore_intv.wellbore_s");
	sqlcmd(link, " and well.well_s=wellbore.well_s");
	sqlcmd(link, " and tig_well_history.tig_latest_well_name=well.well_id");
	sqlcmd(link, " and tig_well_history.DB_SLDNID = %d", productionWell->sldnid); /*-- well key*/
	sqlcmd(link, " AND PRODUCTION_ALOC.prod_start_time <= %s ",sqlcxd(link, finalDate)); /*-- end date*/
	sqlcmd(link, "order by prod_end_time, reservoir_part_code");

	} else {

	sqlcmd(link,"SELECT ");	
	sqlcmd(link,	"wc.well_completion_id reservoir_id, ");
	sqlcmd(link,	"%s dt ", sqldcx(link,"PRODUCTION_ALOC.prod_end_time"));
	sqlcmd(link,"FROM ");
	sqlcmd(link,	"WELL_COMPLETION wc, ");
	sqlcmd(link,	"PFNU_PROD_ACT_X, ");
	sqlcmd(link,	"PRODUCTION_ALOC, ");
	sqlcmd(link,	"P_FLUID_CMPN_RTO, P_ALLOC_FACTOR, ");
	sqlcmd(link,	"ALOC_FLW_STRM, ");
	sqlcmd(link,	"FLW_STRM_ALOC_FCT, ");
	sqlcmd(link,	"PFNU_PORT ");
	sqlcmd(link,"WHERE ");
	sqlcmd(link,		"production_aloc.PRODUCTION_ALOC_S = pfnu_prod_act_x.PRODUCTION_ACT_S ");
	sqlcmd(link,	"AND pfnu_prod_act_x.PFNU_S = wc.WELL_COMPLETION_S ");
	sqlcmd(link,	"AND PRODUCTION_ALOC.PRODUCTION_ALOC_S = P_FLUID_CMPN_RTO.ACTIVITY_S ");
	sqlcmd(link,	"AND well_id = '%s' ", productionWell->well->name); /*-- well key*/
	sqlcmd(link,	"AND PRODUCTION_ALOC.prod_start_time <= %s ",sqlcxd(link, finalDate)); /*-- end date*/
	sqlcmd(link,	"AND P_ALLOC_FACTOR.ACTIVITY_S = PRODUCTION_ALOC.PRODUCTION_ALOC_S ");
	sqlcmd(link,	"AND P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S ");
	sqlcmd(link,	"AND FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S = ALOC_FLW_STRM.ALOC_FLW_STRM_S ");
	sqlcmd(link,	"AND ALOC_FLW_STRM.PFNU_PORT_S = PFNU_PORT.PFNU_PORT_S ");
	sqlcmd(link,	"AND PFNU_PORT.PFNU_S = wc.WELL_COMPLETION_S ");
	sqlcmd(link,	"AND ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID='pipeline' ");
	sqlcmd(link,	"AND NOT P_ALLOC_FACTOR.DATA_VALUE in ('12','14','158','34','36', '46', '50', '159', '168',  '177') ");
	sqlcmd(link,"order by prod_end_time, reservoir_id");

	}

	Index = 1;
	sqlbnd(link, Index++, SQL_CHARACTER,  sizeof(reservoirId), reservoirId);
	sqlbnd(link, Index++, SQL_CHARACTER, 	sizeof(prodEndTime), prodEndTime);
	
	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "calcReservoirMoving: Failed to receive data row");
		*ier = SUCCES;		
		return;
	}

	while(1)	{
		int sqlnxtOut;

		sqlnxtOut = sqlnxt(link);
		
		
		if (!sqlnxtOut || strcmp(prevProdEndTime,prodEndTime)) {
			char str[100];

			if (prevResvs) {
				if (*intersectReservoirs(&resvs,&reservoirs,ier) != NULL  && 
				       !isEqualReservoirs(&prevResvs,&resvs,ier)) {

					NamesToString(prevResvs, str,"","+","");

					if (isEqualReservoirs(&prevResvs,&reservoirs,ier)) {
						productionWell->reservoirState = NO_MOVING;
					}
					else
					if (isUpper(&prevResvs,subtractReservoirs(&resvs,&prevResvs,ier), ier)) {
						productionWell->reservoirState = FROM_UPPER_RESERVOIR;
						productionWell->movingReservoir = (char*)malloc((strlen(str)+1)*sizeof(char));
						strcpy(productionWell->movingReservoir, str);
					} else
					if (isLower(&prevResvs,subtractReservoirs(&resvs,&prevResvs,ier), ier)) {
						productionWell->reservoirState = FROM_LOWER_RESERVOIR;
						productionWell->movingReservoir = (char*)malloc((strlen(str)+1)*sizeof(char));
						strcpy(productionWell->movingReservoir, str);
					}
				}
				if (*intersectReservoirs(&resvs,&reservoirs,ier) == NULL && *intersectReservoirs(&prevResvs,&reservoirs,ier) != NULL) {
					NamesToString(resvs, str,"","+","");

					if (isUpper(&resvs,subtractReservoirs(&prevResvs,&resvs,ier),ier)) {
						productionWell->reservoirState = TO_UPPER_RESERVOIR;
						productionWell->movingReservoir = (char*)malloc((strlen(str)+1)*sizeof(char));
						strcpy(productionWell->movingReservoir, str);
					} else
					if (isLower(&resvs,subtractReservoirs(&prevResvs,&resvs,ier),ier)) {
						productionWell->reservoirState = TO_LOWER_RESERVOIR;
						productionWell->movingReservoir = (char*)malloc((strlen(str)+1)*sizeof(char));
						strcpy(productionWell->movingReservoir, str);
					}
				}				
			}
			prevResvs = resvs;
			resvs = NULL;
		}
		if (!sqlnxtOut) break;
		NAMES *resv;
		resv = (NAMES *)malloc(sizeof(NAMES));
		strcpy(resv->name,	reservoirId);		
		resv->selected = TRUE;
		tllAdd(&resvs,resv,ier);
		strcpy(prevProdEndTime,prodEndTime);

		tdmded_(prodEndTime, &fmt_flg, &findat, ier);
		ERROR_CHECK("calcReservoirMoving: tdmded failed")
		
		if (findat != prevFindat) {
			multipleReservoirProductionResvs = NULL;
		}
		multipleReservoirProductionResv = tllFind(&multipleReservoirProductionResvs, &find_reservoirs, reservoirId, ier);
		if (!multipleReservoirProductionResv) {
			multipleReservoirProductionResv = (NAMES *)malloc(sizeof(NAMES));
			strcpy(multipleReservoirProductionResv->name,	reservoirId);		
			multipleReservoirProductionResv->selected = TRUE;
			tllAppend(&multipleReservoirProductionResvs,multipleReservoirProductionResv,ier);
		}		
		prevFindat = findat;		
	}

	productionWell->lastReservoirs = multipleReservoirProductionResvs;

	*ier = SUCCES;
}


/*
C   10APR13  PT   SCR 20319 Original version
C   11APR13  PT   SCR 20319 Fix produced water and condensate phase codes.
*/

void bblSplitPhaseFilter(char *phaseFilter, char **generalPhaseFilterPtr,
                         char **reconciledPhaseFilterPtr) {
  char *phaseFilterPos;
  char *generalPhaseFilter = NULL;
  char *reconciledPhaseFilter = NULL;

  phaseFilterPos = phaseFilter;

  while (phaseFilterPos) {
    char *phaseFilterNextPos = NULL;
    char curPhase[BBL_NAME_LENGTH];
    int len;

    phaseFilterPos = strchr(phaseFilterPos, '\'');

    if (phaseFilterPos) {
      phaseFilterPos++;
      phaseFilterNextPos = strchr(phaseFilterPos, '\'');
    }

    if (phaseFilterPos && phaseFilterNextPos) {
      len = phaseFilterNextPos - phaseFilterPos;

      phaseFilterNextPos++;

      strncpy(curPhase, phaseFilterPos, len);
      curPhase[len] = '\0';

      if (!strcmp(curPhase, "crude oil") && !strcmp(bblTypesSetup[BBL_OIL].unitSet, "Volume"))
         strcpy(curPhase, "oilvol");

      else if (!strcmp(curPhase, "produced water") && !strcmp(bblTypesSetup[BBL_OIL].unitSet, "Volume"))
         strcpy(curPhase, "watvol");

      else if (!strcmp(curPhase, "condensate") && !strcmp(bblTypesSetup[BBL_CONDENSATE].unitSet, "Volume"))
         strcpy(curPhase, "convol");


      if (!strcmp(curPhase, "oilvol") || !strcmp(curPhase, "watvol") ||
          !strcmp(curPhase, "convol") || !strcmp(curPhase, "free gas")) {

        if(!generalPhaseFilter) {
          generalPhaseFilter = malloc(strlen(phaseFilter)+1);
          sprintf(generalPhaseFilter, "'%s'", curPhase);
        }
        else {
          strcat(generalPhaseFilter, ",'");
          strcat(generalPhaseFilter, curPhase);
          strcat(generalPhaseFilter, "'");
        }

      } else {

        if(!reconciledPhaseFilter) {
          reconciledPhaseFilter = malloc(strlen(phaseFilter)+1);
          sprintf(reconciledPhaseFilter, "'%s'", curPhase);
        }
        else {
          strcat(reconciledPhaseFilter, ",'");
          strcat(reconciledPhaseFilter, curPhase);
          strcat(reconciledPhaseFilter, "'");
        }

      }

    }

    phaseFilterPos = phaseFilterNextPos;

  }

  *generalPhaseFilterPtr = generalPhaseFilter;
  *reconciledPhaseFilterPtr = reconciledPhaseFilter;

}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bbl_readproduction
CA
CA
CA  FUNCTION: Read production for given borehole
CA
CA
CA  APPLICATION/SUBSYSTEM:  Bubble maps
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   void bbl_readproduction()
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  ier         O     long *  Error return:
CA                               SUCCES = successful completion
CA                               280863301 = Failed to receive data row
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   26OCT05       Original version
C   18JUL12  RMY  SCR 20746 Use %f format for doubles.
C   16AUG12  PT   SCR 20319 Move symbolNumber and isCurrentReservoir calculation from LoadWellByName
C   14MAR13  PT   SCR 20319 Remove isCurrentReservoir call.
C   04APR13  PT   SCR 20319 Pass well structure to bbl_wellsymbol instead of well name
C                 Reset error code if mccipu failed.
C   05APR13  PT   SCR 20319 Make it work on sqlite: use sqlcxd/sqldcx, remove 
C                 unnecessary brackets from sql query
C   10APR13  PT   SCR 20319 Split phase filter into general and reconciled
C   11APR13  PT   SCR 20319 Add volumeVals and massVals fields to PRODUCTION
C                 structure instead of vals field.
C   18APR13  PT   SCR 20319 Replace datadmg with tdmded.
C   15MAY13  PT   SCR 20319 Modify lift method reading.
C   16MAY13  PT   SCR 20319 Move initial well role reading to bbl_wellsymbol
C   17MAY13  PT   SCR 20319 Add new data model reading.
C   03JUL13  PT   SCR 20319 Ignore lift method if there is no production data
*/

int bbl_readproduction_old_mod(void *item, void *arg, int *ier)
{
  PROD_WELL *wp;
  Database *link;
  int Index;
  double prod, days;
  char start_time[15], end_time[15];
  char pseudo[45], prev_pseudo[45], status[41];
  PRODUCTION *Product;
  double stadat, findat;
  int NeedProd, i, PhaseIndex;
  int iprcnt;  
  char *reconciledPhaseFilter;
  char *generalPhaseFilter;
  char liftMethodShort[41] = "";
  char liftMethod[41];
  char *liftMethodShortCodes[] = {"ECN", "FON", "EDN", "SHGN",
                                  "STR", "PLN", "GLF", "UVN", "RED"};
  char *liftMethodCodes[] = {"centrifugal pump", "flowing", "diaphragm pump", "sucker-rod pump",
                             "jet pump", "plunger pump", "gas lift", "spiral pump", "RED pump"};

  /* Split phase filter into general and reconciled */

  bblSplitPhaseFilter(BubbleSetup.PhaseFilter, &generalPhaseFilter, &reconciledPhaseFilter);

  if(!GlobalCount) GlobalCount=1;
  iprcnt = 100.0 * GlobalIndex/(float)GlobalCount;
  mccipu_(&iprcnt, ier);
  if(*ier != SUCCES) {
    ohnooo_(ier, "bbl_readproduction: mccipu failed");
    *ier = SUCCESSFUL;
  }
  GlobalIndex ++; 

  link  = PRJ_LINK;

  wp = (PROD_WELL*)item;  

  if(!wp) {
    *ier = 10000;
    ohnooo_ (ier, "bbl_readproduction: Invalid well pointer");
    return FALSE;
  }

  bblCalcReservoirMovingAndMultipleReservoirProduction(wp, BubbleSetup.stadat_text, BubbleSetup.findat_text,ier);

  if (reconciledPhaseFilter) {
  
  /*read production*/
  sqlcmd(link, " select product.data_value,");
  sqlcmd(link, " %s,", sqldcx(link,"product.start_time"));
  sqlcmd(link, " %s,", sqldcx(link,"product.end_time"));
  sqlcmd(link, " product.fl_pseudo_cmpn_id, product.r_cmpl_sta_name, product.prod_time");
  sqlcmd(link, " from");
  sqlcmd(link, " (select p_std_vol_lq.data_value,");
  sqlcmd(link, " aloc_flw_strm.fl_pseudo_cmpn_id fl_pseudo_cmpn_id,");
  sqlcmd(link, " well_cmpl_sta.r_cmpl_sta_name r_cmpl_sta_name,");
  sqlcmd(link, " p_std_vol_lq.start_time start_time,");
  sqlcmd(link, " p_std_vol_lq.end_time end_time,");
  sqlcmd(link, " p_pfnu_port_time.data_value prod_time");
  sqlcmd(link, " from aloc_flw_strm,p_std_vol_lq, pfnu_prod_act_x,");
                sqlcmd(link, " production_aloc,tig_well_history,");
                sqlcmd(link, " well_completion,well_cmpl_sta,well,p_pfnu_port_time");
        sqlcmd(link, " where production_aloc.production_aloc_s=pfnu_prod_act_x.production_act_s and");
                 sqlcmd(link, " well_cmpl_sta.caused_by_s = pfnu_prod_act_x.production_act_s and");
                 sqlcmd(link, " production_aloc.production_aloc_s=p_std_vol_lq.activity_s and");
		 sqlcmd(link, " p_pfnu_port_time.ACTIVITY_S=PRODUCTION_ALOC.PRODUCTION_ALOC_s and");
                 sqlcmd(link, " p_pfnu_port_time.data_value is not null and");
                 sqlcmd(link, " well.well_s=well_completion.well_s and");
                 sqlcmd(link, " well_completion.well_completion_s=well_cmpl_sta.well_completion_s and");
                 sqlcmd(link, " well_completion.well_completion_s=pfnu_prod_act_x.pfnu_s and");
                 sqlcmd(link, " aloc_flw_strm.aloc_flw_strm_s = p_std_vol_lq.object_s  and");
                 sqlcmd(link, " tig_well_history.tig_latest_well_name=well.well_id and");
                 sqlcmd(link, " p_std_vol_lq.data_value > 0 and");
                 sqlcmd(link, " well_completion.well_completion_id in (%s) and", BubbleSetup.reservoir);
                 sqlcmd(link, " tig_well_history.DB_SLDNID = %d", wp->well->sldnid);
  sqlcmd(link, " union all");
  sqlcmd(link, " select p_std_vol_gas.data_value,");
  sqlcmd(link, " aloc_flw_strm.fl_pseudo_cmpn_id fl_pseudo_cmpn_id,");
  sqlcmd(link, " well_cmpl_sta.r_cmpl_sta_name r_cmpl_sta_name,");
  sqlcmd(link, " p_std_vol_gas.start_time start_time,");
  sqlcmd(link, " p_std_vol_gas.end_time end_time,");
  sqlcmd(link, " p_pfnu_port_time.data_value prod_time");
  sqlcmd(link, " from aloc_flw_strm,p_std_vol_gas, pfnu_prod_act_x,");
                sqlcmd(link, " production_aloc,tig_well_history,");
                sqlcmd(link, " well_completion,well_cmpl_sta,well,p_pfnu_port_time");
        sqlcmd(link, " where production_aloc.production_aloc_s=pfnu_prod_act_x.production_act_s and");
                 sqlcmd(link, " well_cmpl_sta.caused_by_s = pfnu_prod_act_x.production_act_s and");
                 sqlcmd(link, " production_aloc.production_aloc_s=p_std_vol_gas.activity_s and");
		 sqlcmd(link, " p_pfnu_port_time.ACTIVITY_S=PRODUCTION_ALOC.PRODUCTION_ALOC_s and");
                 sqlcmd(link, " p_pfnu_port_time.data_value is not null and");
                 sqlcmd(link, " well.well_s=well_completion.well_s and");
                 sqlcmd(link, " well_completion.well_completion_s=well_cmpl_sta.well_completion_s and");
                 sqlcmd(link, " well_completion.well_completion_s=pfnu_prod_act_x.pfnu_s and");
                 sqlcmd(link, " aloc_flw_strm.aloc_flw_strm_s = p_std_vol_gas.object_s  and");
                 sqlcmd(link, " tig_well_history.tig_latest_well_name=well.well_id and");
                 sqlcmd(link, " p_std_vol_gas.data_value > 0 and");
                 sqlcmd(link, " well_completion.well_completion_id in (%s) and", BubbleSetup.reservoir);
                 sqlcmd(link, " tig_well_history.DB_SLDNID = %d) product", wp->well->sldnid);
  if(reconciledPhaseFilter)
    sqlcmd(link, " where product.fl_pseudo_cmpn_id in (%s)", reconciledPhaseFilter);
  sqlcmd(link, " order by product.start_time, product.end_time");

  free(reconciledPhaseFilter);

  Index = 1;
  sqlbnd(link, Index++, SQL_DOUBLE, 0, &prod);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(start_time), start_time);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(end_time), end_time);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(pseudo), pseudo);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(status), status);
  sqlbnd(link, Index++, SQL_DOUBLE, 0, &days);

  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_readproduction_lq: Failed to receive data row");
    return FALSE;
  }

  strcpy(prev_pseudo, "----------");
  Product = NULL;
  while(sqlnxt(link)){
    int fmt_flg = 0;

    tdmded_(start_time, &fmt_flg, &stadat, ier);
    ERROR_CHECK_RETURN("bbl_readproduction: tdmded (1) failed", FALSE)

    tdmded_(end_time, &fmt_flg, &findat, ier);
    ERROR_CHECK_RETURN("bbl_readproduction: tdmded (2) failed", FALSE)

    if((stadat >= BubbleSetup.stadat && stadat <= BubbleSetup.findat) 
       || (findat >= BubbleSetup.stadat && findat <= BubbleSetup.findat)) {

      NeedProd = 1;
      if(Product) 
	     NeedProd = Product->stadat!=stadat || Product->findat!=findat;

      if(!Product || NeedProd) {
	     Product = (PRODUCTION*)malloc(sizeof(PRODUCTION));      

	     if(!Product) {                                          
	       *ier = 3;                                       
	       ohnooo_(ier, "bbl_readproduction_lq: Product memory allocation error"); 
	       return FALSE;                                       
	     }
	
	     Product->stadat = stadat;
	     Product->findat = findat;                               
	     Product->days = days/86400.0;/* from sec to days */        
	     strcpy(liftMethodShort, status);

	     Product->volumeVals = malloc(CODE_NAME_COUNT * sizeof(*Product->volumeVals));
	     Product->massVals = malloc(CODE_NAME_COUNT * sizeof(*Product->massVals));
	     for(i=0; i<CODE_NAME_COUNT; i++) {
	       Product->volumeVals[i] = 0;
	       Product->massVals[i] = 0;
	     }
	
	     tllAdd(&wp->Prods, (char*)Product, ier);           
        }

      /* Find the phase index beeng loaded */
      PhaseIndex = -1;
      for(i=0; i<CODE_NAME_COUNT; i++) {
	     if(!strcmp(FluidCodes[i].code, pseudo)) {
	     PhaseIndex = i;
	     break;
	     }
      }

      if(PhaseIndex < 0) {
	     *ier = 3;                                       
	     ohNooo(*ier, "bbl_readproduction_lq: Phase <%s> is not found", pseudo); 
	     return FALSE; 
      }

      if (!strcmp(pseudo, "crude oil") ||
          !strcmp(pseudo, "produced water") ||
          !strcmp(pseudo, "condensate"))
         Product->massVals[PhaseIndex] += prod*1000.0;/*convert tonnes to kgs*/
      else
         Product->volumeVals[PhaseIndex] += prod;
      ohNooo(200000002, "%s %f %s %s %s %s", wp->well->name, prod, start_time, end_time, pseudo, status);		 
    }
  }
  
  }
  
  if (generalPhaseFilter) { 

  
  sqlcmd(link, " select p_std_vol_lq.data_value,");
  sqlcmd(link, " %s,", sqldcx(link,"p_std_vol_lq.start_time"));
  sqlcmd(link, " %s,", sqldcx(link,"p_std_vol_lq.end_time"));
  sqlcmd(link, " p_std_vol_lq.bsasc_source,");
  sqlcmd(link, " well_cmpl_sta.r_cmpl_sta_name,");
  sqlcmd(link, " p_pfnu_port_time.data_value");
  sqlcmd(link, " from pfnu_port,");
  sqlcmd(link, " aloc_flw_strm,");
  sqlcmd(link, " p_std_vol_lq,");
  sqlcmd(link, " well,well_completion,tig_well_history,");
  sqlcmd(link, " production_aloc, p_pfnu_port_time, well_cmpl_sta");
  sqlcmd(link, " where");
  sqlcmd(link, " tig_well_history.db_sldnid = %d and", wp->well->sldnid);
  sqlcmd(link, " tig_well_history.tig_latest_well_name=well.well_id and");
  sqlcmd(link, " well.well_s=well_completion.well_s and");
  sqlcmd(link, " well_completion.well_completion_id in (%s) and", BubbleSetup.reservoir);
  sqlcmd(link, " well_completion.well_completion_s = pfnu_port.pfnu_s and");
  sqlcmd(link, " pfnu_port.pfnu_port_s = aloc_flw_strm.pfnu_port_s and");
  sqlcmd(link, " aloc_flw_strm.aloc_flw_strm_s = p_std_vol_lq.object_s and");
  sqlcmd(link, " production_aloc.production_aloc_s=p_std_vol_lq.activity_s and");
  sqlcmd(link, " p_pfnu_port_time.activity_s=production_aloc.production_aloc_s and");
  sqlcmd(link, " p_pfnu_port_time.data_value>0 and");
  sqlcmd(link, " p_std_vol_lq.start_time=well_cmpl_sta.start_time and");
  sqlcmd(link, " well_cmpl_sta.well_completion_s = well_completion.well_completion_s and");
  sqlcmd(link, " well_cmpl_sta.caused_by_s is not null and");
  if (generalPhaseFilter)
  sqlcmd(link, " p_std_vol_lq.bsasc_source in (%s)",generalPhaseFilter);
  sqlcmd(link, " union all");
  sqlcmd(link, " select p_std_vol_gas.data_value,");
  sqlcmd(link, " %s,", sqldcx(link,"p_std_vol_gas.start_time"));
  sqlcmd(link, " %s,", sqldcx(link,"p_std_vol_gas.end_time"));
  sqlcmd(link, " p_std_vol_gas.bsasc_source,");
  sqlcmd(link, " well_cmpl_sta.r_cmpl_sta_name,");
  sqlcmd(link, " p_pfnu_port_time.data_value");
  sqlcmd(link, " from pfnu_port,");
  sqlcmd(link, " aloc_flw_strm,");
  sqlcmd(link, " p_std_vol_gas,");
  sqlcmd(link, " well,well_completion,tig_well_history,");
  sqlcmd(link, " production_aloc, p_pfnu_port_time, well_cmpl_sta");
  sqlcmd(link, " where");
  sqlcmd(link, " tig_well_history.db_sldnid = %d and", wp->well->sldnid);
  sqlcmd(link, " tig_well_history.tig_latest_well_name=well.well_id and");
  sqlcmd(link, " well.well_s=well_completion.well_s and");
  sqlcmd(link, " well_completion.well_completion_id in (%s) and", BubbleSetup.reservoir);
  sqlcmd(link, " well_completion.well_completion_s = pfnu_port.pfnu_s and");
  sqlcmd(link, " pfnu_port.pfnu_port_s = aloc_flw_strm.pfnu_port_s and");
  sqlcmd(link, " aloc_flw_strm.aloc_flw_strm_s = p_std_vol_gas.object_s and");
  sqlcmd(link, " production_aloc.production_aloc_s=p_std_vol_gas.activity_s and");
  sqlcmd(link, " p_pfnu_port_time.activity_s=production_aloc.production_aloc_s and");
  sqlcmd(link, " p_pfnu_port_time.data_value>0 and");
  sqlcmd(link, " p_std_vol_gas.start_time=well_cmpl_sta.start_time and");
  sqlcmd(link, " well_cmpl_sta.well_completion_s = well_completion.well_completion_s and");
  sqlcmd(link, " well_cmpl_sta.caused_by_s is not null and");
  if (generalPhaseFilter)
  sqlcmd(link, " p_std_vol_gas.bsasc_source in (%s)",generalPhaseFilter);

  free(generalPhaseFilter);

  Index = 1;
  sqlbnd(link, Index++, SQL_DOUBLE, 0, &prod);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(start_time), start_time);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(end_time), end_time);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(pseudo), pseudo);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(status), status);
  sqlbnd(link, Index++, SQL_DOUBLE, 0, &days);
  
  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_readproduction_lq: Failed to receive data row");
    return FALSE;
  }
  
  Product = NULL;
  
  while(sqlnxt(link)){
    int fmt_flg = 0;

    tdmded_(start_time, &fmt_flg, &stadat, ier);
    ERROR_CHECK_RETURN("bbl_readproduction: tdmded (1) failed", FALSE)

    tdmded_(end_time, &fmt_flg, &findat, ier);
    ERROR_CHECK_RETURN("bbl_readproduction: tdmded (2) failed", FALSE)

    if((stadat >= BubbleSetup.stadat && stadat <= BubbleSetup.findat) 
       || (findat >= BubbleSetup.stadat && findat <= BubbleSetup.findat)) {
       
      NeedProd = 1;
      if(Product) 
	     NeedProd = Product->stadat!=stadat || Product->findat!=findat;

      if(!Product || NeedProd) {
	     Product = (PRODUCTION*)malloc(sizeof(PRODUCTION));      

	     if(!Product) {                                          
	       *ier = 3;                                       
	       ohnooo_(ier, "bbl_readproduction_lq: Product memory allocation error"); 
	       return FALSE;                                       
	     }
	
	     Product->stadat = stadat;
	     Product->findat = findat;                               
	     Product->days = days/86400.0;/* from sec to days */        
	     strcpy(liftMethodShort, status);

	     Product->volumeVals = malloc(CODE_NAME_COUNT * sizeof(*Product->volumeVals));
	     Product->massVals = malloc(CODE_NAME_COUNT * sizeof(*Product->massVals));
	     for(i=0; i<CODE_NAME_COUNT; i++) {
	       Product->volumeVals[i] = 0;
	       Product->massVals[i] = 0;
	     }
	
	     tllAdd(&wp->Prods, (char*)Product, ier);           
        }

      if (!strcmp(pseudo, "oilvol"))
         strcpy(pseudo, "crude oil");
      else if (!strcmp(pseudo, "watvol"))
         strcpy(pseudo, "produced water");
      else if (!strcmp(pseudo, "convol"))
         strcpy(pseudo, "condensate");

      /* Find the phase index beeng loaded */
      PhaseIndex = -1;
      for(i=0; i<CODE_NAME_COUNT; i++) {
	     if(!strcmp(FluidCodes[i].code, pseudo)) {
	     PhaseIndex = i;
	     break;
	     }
      }
       
      if(PhaseIndex < 0) {
	     *ier = 3;                                       
	     ohNooo(*ier, "bbl_readproduction_lq: Phase <%s> is not found", pseudo); 
	     return FALSE; 
      }

      Product->volumeVals[PhaseIndex] += prod;
      ohNooo(200000002, "%s %f %s %s %s %s", wp->well->name, prod, start_time, end_time, pseudo, status);		 

    }    
  }
  
  }

  /* get lift method index */

  liftMethod[0] = '\0';
  for(i = 0; i < sizeof(liftMethodShortCodes)/ sizeof(liftMethodShortCodes[0]); i++)
    if (!strcmp(liftMethodShortCodes[i], liftMethodShort))
      strcpy(liftMethod, liftMethodCodes[i]);

  wp->liftMethod = -1;
  for(i = 0; i < BBL_LIFT_METHODS_NUMBER; i++)
    if (!strcmp(liftMethod, bblLiftMethods[i].code))
      wp->liftMethod = i;

  /* get symbol number */

  wp->symbolNumber = bbl_wellsymbol(wp, BubbleSetup.findat_text, BubbleSetup.reservoir, ier) + WELL_SYMBOL_OFFSET;

  return FALSE;
}

int bbl_readproduction_new_mod(void *item, void *arg, int *ier)
{
	PROD_WELL *wp;
	Database *link;
	int index;
	double prod, time, stadat, findat;
	PRODUCTION *Product;
	int NeedProd, i, PhaseIndex, ignoreLiftMethod;
	int iprcnt;
	char liftMethod[41];
	char start_time[20], end_time[20];
	char componentId[41], unitSet[41];
	char * prodTables[] = {"p_std_vol_lq", "p_std_vol_gas", "p_q_mass_basis"};
	char * unitSets[] = {"Volume", "Volume", "Mass"};

	if(!GlobalCount) GlobalCount=1;
	iprcnt = 100.0 * GlobalIndex/(float)GlobalCount;
	mccipu_(&iprcnt, ier);
	if(*ier != SUCCES) {
		ohnooo_(ier, "bbl_readproduction: mccipu failed");
		*ier = SUCCESSFUL;
	}
	GlobalIndex ++; 

	link  = PRJ_LINK;

	wp = (PROD_WELL*)item;  

	if(!wp) {
		*ier = LGLEV3;
		ohnooo_ (ier, "bbl_readproduction: Invalid well pointer");
		return FALSE;
	}

	bblCalcReservoirMovingAndMultipleReservoirProduction(wp, BubbleSetup.stadat_text, BubbleSetup.findat_text,ier);
	ERROR_CHECK_RETURN("bbl_readproduction: bblCalcReservoirMovingAndMultipleReservoirProduction failed",FALSE)

	for(i = 0; i < sizeof(prodTables)/sizeof(prodTables[0]); i++) {

		if (i != 0)
			sqlcmd(link, " union all ");

		sqlcmd(link, " select production.data_value,");
		sqlcmd(link, " production.start_time,");
		sqlcmd(link, " production.end_time,");
		sqlcmd(link, " %s,", sqldcx(link,"production.start_time"));
		sqlcmd(link, " %s,", sqldcx(link,"production.end_time"));
		sqlcmd(link, " production.bsasc_source,");
		sqlcmd(link, " '%s',", unitSets[i]);
		sqlcmd(link, " p_pfnu_port_time.data_value");
		sqlcmd(link, " from %s production,", prodTables[i]);
		sqlcmd(link, " pfnu_prod_act_x, production_aloc, tig_well_history,");
		sqlcmd(link, " reservoir_part, wellbore_intv, wellbore, well, p_pfnu_port_time");

		sqlcmd(link, " where ");

		sqlcmd(link, " production.data_value is not null and");
		sqlcmd(link, " p_pfnu_port_time.data_value is not null and");

		sqlcmd(link, " production.activity_s = production_aloc.production_aloc_s and ");
		sqlcmd(link, " p_pfnu_port_time.activity_s = production_aloc.production_aloc_s and ");

		sqlcmd(link, " production_aloc.production_aloc_s = pfnu_prod_act_x.production_act_s and ");
		sqlcmd(link, " production_aloc.bsasc_source = 'Reallocated Production' and reservoir_part.reservoir_part_s = pfnu_prod_act_x.pfnu_s and");

		sqlcmd(link, " reservoir_part.reservoir_part_s in (%s) and", reservoirElementKeys);
		sqlcmd(link, " wellbore_intv.geologic_ftr_s = reservoir_part.reservoir_part_s and");
		sqlcmd(link, " wellbore.wellbore_s=wellbore_intv.wellbore_s and");
		sqlcmd(link, " well.well_s=wellbore.well_s and");
		sqlcmd(link, " tig_well_history.tig_latest_well_name=well.well_id and");
		sqlcmd(link, " tig_well_history.DB_SLDNID = %d", wp->sldnid);

		if (BubbleSetup.PhaseFilter)
			sqlcmd(link, " and production.bsasc_source in (%s)",BubbleSetup.PhaseFilter);

	}

	sqlcmd(link, " order by start_time, end_time");


	index = 1;
	sqlbnd(link, index++, SQL_DOUBLE, 0, &prod);
	index++;
	index++;
	sqlbnd(link, index++, SQL_CHARACTER, sizeof(start_time), start_time);
	sqlbnd(link, index++, SQL_CHARACTER, sizeof(end_time), end_time);
	sqlbnd(link, index++, SQL_CHARACTER, sizeof(componentId), componentId);
	sqlbnd(link, index++, SQL_CHARACTER, sizeof(unitSet), unitSet);
	sqlbnd(link, index++, SQL_DOUBLE, 0, &time);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bbl_readproduction: Failed to receive data row");
		return FALSE;
	}

	ignoreLiftMethod = TRUE;

	Product = NULL;

	while(sqlnxt(link)){
		int fmt_flg = 0;

		tdmded_(start_time, &fmt_flg, &stadat, ier);
		ERROR_CHECK_RETURN("bbl_readproduction: tdmded (1) failed", FALSE)

		tdmded_(end_time, &fmt_flg, &findat, ier);
		ERROR_CHECK_RETURN("bbl_readproduction: tdmded (2) failed", FALSE)

		if((stadat >= BubbleSetup.stadat && stadat <= BubbleSetup.findat) 
		   || (findat >= BubbleSetup.stadat && findat <= BubbleSetup.findat)) {

			ignoreLiftMethod = FALSE;

			NeedProd = TRUE;
			if(Product) 
				NeedProd = Product->stadat!=stadat || Product->findat!=findat;

			if(!Product || NeedProd) {
				Product = (PRODUCTION*)malloc(sizeof(PRODUCTION));

				if(!Product) {
					*ier = LGLEV3;
					ohnooo_(ier, "bbl_readproduction: Product memory allocation error"); 
					return FALSE;
				}

				Product->stadat = stadat;
				Product->findat = findat;                               
				Product->days = time/86400.0;/* from sec to days */        

				Product->volumeVals = malloc(CODE_NAME_COUNT * sizeof(*Product->volumeVals));
				Product->massVals = malloc(CODE_NAME_COUNT * sizeof(*Product->massVals));
				for(i=0; i<CODE_NAME_COUNT; i++) {
					Product->volumeVals[i] = 0;
					Product->massVals[i] = 0;
				}

				tllAdd(&wp->Prods, (char*)Product, ier);           
			}

			/* Find the phase index beeng loaded */
			PhaseIndex = -1;
			for(i=0; i<CODE_NAME_COUNT; i++) {
				if(!strcmp(FluidCodes[i].code, componentId)) {
					PhaseIndex = i;
					break;
				}
			}

			if(PhaseIndex < 0) {
				*ier = LGLEV1;                                       
				ohNooo(*ier, "bbl_readproduction_lq: Phase <%s> is not found", componentId); 
				return FALSE; 
			}

			if (!strcmp(unitSet,"Mass"))
				Product->massVals[PhaseIndex] += prod;
			else
				Product->volumeVals[PhaseIndex] += prod;

			ohNooo(200000002, "%s %s %f %f %s %s %s", wp->well->name, unitSet, time, prod, start_time, end_time, componentId);

		}
	}

	/* get lift method index */

	if (ignoreLiftMethod) {

		wp->liftMethod = -1;

	} else {

		bblGetWellStrProperty(wp->sldnid, BubbleSetup.findat_text, "lift method", liftMethod, ier);
		ERROR_CHECK_RETURN("bbl_readproduction: bblGetWellStrProperty failed",FALSE)

		wp->liftMethod = -1;
		for(i = 0; i < BBL_LIFT_METHODS_NUMBER; i++)
			if (!strcmp(liftMethod, bblLiftMethods[i].code))
				wp->liftMethod = i;

	}

	/* get symbol number */

	wp->symbolNumber = bbl_wellsymbol(wp, BubbleSetup.findat_text, BubbleSetup.reservoir, ier);

	return FALSE;
}

int bbl_readproduction(void *item, void *arg, int *ier)
{
	if (bblIsNewDataModel())
		return bbl_readproduction_new_mod(item, arg, ier);
	else
		return bbl_readproduction_old_mod(item, arg, ier);
}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bbl_getproduction_period
CA
CA
CA  FUNCTION:  Select production period from table p_std_vol_lq.
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   void bbl_getproduction_period(OnlyProduction, startdate, enddate, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  startdate    O    char *  Min value of production date.
CA  enddate      O    char *  Max value of production date.
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   26DEC03       Original version
C   05APR13  PT   SCR 20319 Make it work on sqlite: use sqlcxd/sqldcx, remove 
C                 unnecessary brackets from sql query
*/
void bbl_getproduction_period(int OnlyProduction, char *startdate, char *enddate, int *ier)
{
  char start_time[BBL_DATE_LENGTH], end_time[BBL_DATE_LENGTH];
  int Index;
  Database *link;
                                                                                                                                  
  link  = PRJ_LINK;
                                                                                                                                  
  if(OnlyProduction) {
    sqlcmd(link, " select %s,", sqldcx(link,"min(start_time)"));
    sqlcmd(link, " %s from p_std_vol_lq", sqldcx(link,"max(end_time)"));
  }
  else {
    sqlcmd(link, " select %s start_date,", sqldcx(link,"min(start_date)"));
           sqlcmd(link, " %s end_date", sqldcx(link,"max(end_date)"));
    sqlcmd(link, " from");
       sqlcmd(link, " (select min(start_time) start_date,");
              sqlcmd(link, " max(end_time) end_date from p_std_vol_lq");
       sqlcmd(link, " union");
       sqlcmd(link, " select  min(wtst_meas.start_time) start_date,");
                sqlcmd(link, " max(wtst_meas.end_time) end_date");
       sqlcmd(link, " from wtst_meas)");
  }
                                                                                                                                  
                                                                                                                                  
  Index = 1;
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(start_time), start_time);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(end_time), end_time);
                                                                                                                                  
  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_getproduction_period: Failed to receive data row");
    return;
  }
                                                                                                                                  
  while(sqlnxt(link)){
    strcpy(startdate, start_time);
    strcpy(enddate, end_time);
  }

  bblDateWithoutTime(startdate);
  bblDateWithoutTime(enddate);
}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bbl_wellsymbol
CA
CA
CA  FUNCTION:  Return well symbol code by given well id
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   int bbl_wellsymbol(wellid)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  wellid       I    char *  Id of well.
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   26DEC03       Original version
C   04APR13  PT   SCR 20319 Return special symbols for injecting wells
C                 converted from producing and producing wells converted from 
C                 injecting.
C   05APR13  PT   SCR 20319 Make it work on sqlite: use sqlcxd/sqldcx
C   16MAY13  PT   SCR 20319 Read initial well role
C   20MAY13  PT   SCR 20319 Add new data model reading.
C   15JUL15  PT   Issue #3 Use standard piezometric symbol
*/

int bbl_wellsymbol_old_mod(PROD_WELL *prodWell, char *findat, char *cmpl_id, int *ier)
{  
  Database *link;
  double data_val = 0, current_well_role;
  char initial_well_role[41];
  int Index;

  link  = PRJ_LINK;
                   
  sqlcmd(link, " SELECT P_ALLOC_FACTOR.DATA_VALUE, P_FLUID_CMPN_RTO.DATA_VALUE, ");
  sqlcmd(link, " tig_well_history.tig_latest_well_state_no ");
                sqlcmd(link, " FROM ALOC_FLW_STRM ALOC_FLW_STRM, ");
                sqlcmd(link, " FLW_STRM_ALOC_FCT FLW_STRM_ALOC_FCT, ");
                sqlcmd(link, " P_ALLOC_FACTOR P_ALLOC_FACTOR,");
		sqlcmd(link, " PFNU_PORT PFNU_PORT,");
                sqlcmd(link, " PFNU_PROD_ACT_X PFNU_PROD_ACT_X,");
                sqlcmd(link, " PRODUCTION_ALOC PRODUCTION_ALOC, ");
                sqlcmd(link, " WELL WELL, tig_well_history,");
                sqlcmd(link, " WELL_COMPLETION WELL_COMPLETION, P_FLUID_CMPN_RTO ");
           sqlcmd(link, " WHERE PRODUCTION_ALOC.PRODUCTION_ALOC_S = PFNU_PROD_ACT_X.PRODUCTION_ACT_S");
                sqlcmd(link, " AND PRODUCTION_ALOC.PRODUCTION_ALOC_S = P_FLUID_CMPN_RTO.ACTIVITY_S");
                sqlcmd(link, " AND WELL.WELL_S = WELL_COMPLETION.WELL_S AND");
                sqlcmd(link, " WELL_COMPLETION.WELL_COMPLETION_S = PFNU_PROD_ACT_X.PFNU_S AND");
		sqlcmd(link, " PFNU_PORT.PFNU_S = WELL_COMPLETION.WELL_COMPLETION_S AND");
                sqlcmd(link, " P_ALLOC_FACTOR.ACTIVITY_S = PRODUCTION_ALOC.PRODUCTION_ALOC_S AND");
                sqlcmd(link, " P_ALLOC_FACTOR.OBJECT_S = FLW_STRM_ALOC_FCT.FLW_STRM_ALOC_FCT_S AND");
                sqlcmd(link, " FLW_STRM_ALOC_FCT.INLET_ALOC_FLW_STRM_S = ALOC_FLW_STRM.ALOC_FLW_STRM_S AND");
		sqlcmd(link, " ALOC_FLW_STRM.PFNU_PORT_S = PFNU_PORT.PFNU_PORT_S AND");
                sqlcmd(link, " P_FLUID_CMPN_RTO.BSASC_SOURCE='gas-oil ratio' AND ");
		sqlcmd(link, " ((tig_well_history.db_sldnid = %d) AND", prodWell->sldnid);
		sqlcmd(link, " (tig_well_history.tig_latest_well_name=WELL.WELL_ID) AND");
                sqlcmd(link, " (ALOC_FLW_STRM.FL_PSEUDO_CMPN_ID='pipeline') AND");
                  sqlcmd(link, " (WELL_COMPLETION.WELL_COMPLETION_ID in (%s)) AND", cmpl_id);
                  sqlcmd(link, " (PRODUCTION_ALOC.START_TIME <= %s))", sqlcxd(link, findat));
	   sqlcmd(link, " ORDER BY PRODUCTION_ALOC.START_TIME ");

  Index = 1;
  sqlbnd(link, Index++, SQL_DOUBLE, 0, &data_val);
  sqlbnd(link, Index++, SQL_DOUBLE, 0, &current_well_role);
  sqlbnd(link, Index++, SQL_CHARACTER, sizeof(initial_well_role), initial_well_role);

  if(!sqlexc (link)) {
    *ier = 280863301;
    ohnooo_ (ier, "bbl_wellsymbol: Failed to receive data row");
    return 0;
  }

  while(sqlnxt(link)){
  }

	/* check if producing well converted from injecting */

	if ((initial_well_role[1] == 'i') &&
	    ((data_val == 11) || 
	     (data_val == 77)) )
		 data_val = 211 - WELL_SYMBOL_OFFSET;

	/* check if injecting well converted from producing */

	if ((initial_well_role[1] == 'p') &&
	    ((data_val == 13) || 
	     (data_val == 82)) )
		 data_val = 212 - WELL_SYMBOL_OFFSET;

	return data_val;
}

int bbl_wellsymbol_new_mod(PROD_WELL *prodWell, char *findat, int *ier)
{
	char wellRole[41], wellStatus[41], initialWellRole[41];
	int i;

	bblGetWellStrProperty(prodWell->sldnid, findat, "initial well role", initialWellRole, ier);
	ERROR_CHECK_RETURN("bbl_wellsymbol: bblGetWellStrProperty failed",0)

	bblGetWellStrProperty(prodWell->sldnid, findat, "current well role", wellRole, ier);
	ERROR_CHECK_RETURN("bbl_wellsymbol: bblGetWellStrProperty failed",0)

	bblGetWellStrProperty(prodWell->sldnid, findat, "well status", wellStatus, ier);
	ERROR_CHECK_RETURN("bbl_wellsymbol: bblGetWellStrProperty failed",0)

	/* check converted wells */

	for(i = 0; i < BBL_CONV_SYMBOLS_NUMBER; i++) {
		if (!strcmp(bblConvertedSymbols[i].initialWellRole, initialWellRole) &&
		    !strcmp(bblConvertedSymbols[i].currentWellRole, wellRole) &&
		    !strcmp(bblConvertedSymbols[i].wellStatus, wellStatus)) {
			return bblConvertedSymbols[i].symbol;
		}
	}

	for(i = 0; i < BBL_SYMBOLS_NUMBER; i++) {
		if (!strcmp(bblSymbols[i].wellRole, wellRole) &&
		    !strcmp(bblSymbols[i].wellStatus, wellStatus)) {
			return bblSymbols[i].symbol;
		}
	}

	return 70;
}

int bbl_wellsymbol(PROD_WELL *prodWell, char *findat, char *cmpl_id, int *ier)
{
	if (bblIsNewDataModel())
		return bbl_wellsymbol_new_mod(prodWell, findat, ier);
	else
		return bbl_wellsymbol_old_mod(prodWell, findat, cmpl_id, ier);
}


/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblGetWellStrProperty
CA
CA
CA  FUNCTION:  Read string well property
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
CA  LINKAGE:   void bblGetWellStrProperty(sldnid, findat, propertyType, propertyValue, ier)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA  sldnid       I    long    Well sldnid.
CA  findat       I    char *  Final date. NULL value is possible
CA  propertyType I    char *  Type of property
CA  propertyValue     char[41]
CA               O            Value of property
CA  ier          O    long *  Error return:
CA                               SUCCES = successful completion
CA                               280863301 = Failed to receive data row
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   17MAY13  PT   SCR 20319 Original version
C   21MAY13  PT   SCR 20319 Update prototype.
C
C
*/


void bblGetWellStrProperty(int sldnid, char *findat,
                           char *propertyType, char *propertyValue, int *ier)
{
	Database *link;
	int index;
	char value[41];

	link  = PRJ_LINK;

	sqlcmd(link, " select p_equipment_fcl.string_value ");
	sqlcmd(link, " from p_equipment_fcl, equipment_insl, ");
	sqlcmd(link, " well, tig_well_history ");
	sqlcmd(link, " where ");
	sqlcmd(link, " equipment_insl.equipment_item_s = p_equipment_fcl.object_s and");
	sqlcmd(link, " well.well_s = equipment_insl.facility_s and");
	sqlcmd(link, " tig_well_history.tig_latest_well_name = well.well_id and");
	sqlcmd(link, " tig_well_history.db_sldnid = %d and", sldnid);
	sqlcmd(link, " p_equipment_fcl.bsasc_source = '%s'", propertyType);
	if (findat)
		sqlcmd(link, " and p_equipment_fcl.start_time <= %s", sqlcxd(link, findat));
	sqlcmd(link, " order by p_equipment_fcl.start_time ");

	index = 1;
	sqlbnd(link, index++, SQL_CHARACTER, sizeof(value), value);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bblGetWellStrProperty: Failed to receive data row");
		return;
	}

	value[0] = '\0';

	while(sqlnxt(link)){
	}

	strcpy(propertyValue, value);

}



/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bbl_GetSymbolDesc
CA
CA
CA  FUNCTION:  Return well symbol description by given symbol id
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Victor Kondrashov
C
CA  LINKAGE:   int bbl_GetSymbolDesc(id, desc)
CA
CA
CA  ARGUMENT
CA    NAME      USE   TYPE    DESCRIPTION
CA  --------    ---   ----    -----------
CA     id        I    long    Id of symbol.
CA    desc       O    char *  Returned symbol description
CA
CA
CA  RESTRICTIONS:  none
CA
CA
C
C
C   REVISED:
C
C   24SEP07       Original version
C   18MAY11  PT   SCR 20319 Use tutGetUid instead of getuid.
C   05APR13  PT   SCR 20319 Use temsds to getting well symbol description
C   24DEC14  PT   SCR 20319 Use GPT_getwds for getting well symbol description
*/

int bbl_GetSymbolDesc(int id, char *desc)
{
	const char *sym_desc;

	if ((sym_desc = GPT_getwds(id)) != NULL) {
		strncpy(desc, sym_desc, 254);
		desc[254] = '\0';
		return TRUE;
	}

	return FALSE;
}

/*
C --- MODULE NUMBER:  000000
C
CA  NAME:      bblLoadWellsForPressureMap
CA
CA
CA  FUNCTION:  Read all wells for pressure map
CA
CA
CA  APPLICATION/SUBSYSTEM:  Mapping: Production bubbles (bbl) INTERNAL
CA
CA
C   AUTHOR:    Pavel Tomin
C
C   REVISED:
C
C   17JUL12  PT   SCR 20319 Original version
C   19APR13  PT   SCR 20319 Use mccGetParent to get parent widget for mccipr
*/
int bblLoadWellsForPressureMap(int *ier)
{
	Database *link;
	int Index;
	int count=0;
	NAMES *nm;
	char well_id[40];
	TigList(NAMES) wells=NULL;
	int iprcnt;  
	int parent;

	link = PRJ_LINK;

	parent = mccGetParent();
  
	mccipr_(&parent, _("Loading production wells"), ier);
	ERROR_CHECK_RETURN( "bblLoadWellsForPressureMap: mccipd failed", FALSE)

	/*Get well count*/
	sqlcmd(link, " SELECT count(distinct WELL.WELL_ID)");
	sqlcmd(link, "    FROM  well");


	sqlbnd(link, 1, SQL_INTEGER, 0, &GlobalCount);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bblLoadWellsForPressureMap: Failed to get row count");
		return 0;
	}

	while(sqlnxt(link)){
	}

	/*Get wells*/

	sqlcmd(link, " SELECT DISTINCT WELL.WELL_ID");
	sqlcmd(link, "    FROM  well");


	Index = 1;
	sqlbnd(link, Index, SQL_CHARACTER, sizeof(well_id), well_id);

	if(!sqlexc (link)) {
		*ier = 280863301;
		ohnooo_ (ier, "bblLoadWellsForPressureMap: Failed to receive data row");
		return 0;
	}
	
	GlobalIndex = 0.0;
	if(!GlobalCount) GlobalCount = 1;
	while(sqlnxt(link)){
		iprcnt = 100.0 * GlobalIndex/(float)GlobalCount;
		mccipu_(&iprcnt, ier);
		ERROR_CHECK_RETURN( "bblLoadWellsForPressureMap: mccipd failed", FALSE)

		nm = malloc(sizeof(NAMES));
		strcpy(nm->name, well_id);
    
		tllAdd(&wells, (char*)nm, ier);
		count++;

		GlobalIndex += 0.5;
	}
	tllForEach(&wells, LoadWell, NULL, NULL, ier);
	ERROR_CHECK_RETURN( "bblLoadWellsForPressureMap: tllForEach failed", FALSE)
	
	mccipd_(ier);
	ERROR_CHECK_RETURN( "bblLoadWellsForPressureMap: mccipd failed", FALSE)

	pxnbin_(ier);
	*ier = SUCCESSFUL;
   
	tllFreeList(&wells, TLL_FREE, ier);
	ERROR_CHECK_RETURN( "bblLoadWellsForPressureMap: tllFreeList failed", FALSE)

	return count;
}