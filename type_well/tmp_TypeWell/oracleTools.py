


import pandas.io.sql as psql
import cx_Oracle as odb
import os,sys
import gettext
import logging

#--- create logger
module_logger = logging.getLogger('pyReporter.oratools')
#===============================================================================
#---########CONST BLOCK##########################
#===============================================================================
PATH_SCRIPT=os.path.dirname(os.path.realpath(__file__))
PATH_SQL_SCRIPTS=PATH_SCRIPT
t = gettext.bindtextdomain('pyReporter', PATH_SCRIPT)
gettext.textdomain('pyReporter')
_ = gettext.gettext


#===============================================================================
#---join values to string. By default to "('val1','val2','val3')" 
#===============================================================================
def join2str(val_list
             ,firstS="("
             ,lastS=")"
             ,preS="'"
             ,afterS="'"
             ,joinerS=","
             ):
    res="{firstS}{val}{lastS}".format(firstS=firstS,lastS=lastS,val="{joinerS}".format(joinerS=joinerS).join(map(lambda x:"{preS}{x}{afterS}".format(x=x,preS=preS,afterS=afterS),val_list)))
    return res

#===============================================================================
#--- Connect to Oracle DB and return 'connection' object 
#===============================================================================
def connect_to_db(host='envy64'
                  ,port=1521
                  ,inst='PDS252'
                  ,user='system'
                  ,pwd='manager'
                  ,schema=None
                  ):
    #--- connection settings
    dsn_tns = odb.makedsn(host, port, inst)
    dsn_user='{usr}/{pwd}@'.format(usr=user,pwd=pwd)
    #--- coonecting to DB
    module_logger.info( _("Connecting to:{}_{}_{}").format(host,port,inst))
    try:
        conn=odb.connect(dsn_user+dsn_tns)
        module_logger.info( _("Connected"))
    except odb.DatabaseError,info:
        module_logger.info( _("Logon  Error:{}").format(info))
        module_logger.info( sys.exc_info())
        sys.exit(-1)
    if not schema is None:
        module_logger.info( _("Set schema:{}").format(schema))
        conn.current_schema=schema
    return conn  
#===============================================================================
#--- Connect to Oracle DB and return 'connection' object 
#===============================================================================
def connect_to_db_tns(
                      db_name=r"envy64_PDS252"
                      ,user='system'
                      ,pwd='manager'
                      ,schema=None
                      ,tns_f_path=None
                  ):
    #--- coonecting to DB
    if (not tns_f_path is None) and (tns_f_path!="") and (os.path.exists(os.path.join(tns_f_path,"tnsnames.ora"))):
        os.environ["TNS_ADMIN"] = tns_f_path
    module_logger.info( _("Use '{}'").format(os.environ["TNS_ADMIN"]))
    module_logger.info( _("Connecting to:{}").format(db_name))
    try:
        conn=odb.connect(user, pwd, db_name)
        module_logger.info( _("Connected"))
    except odb.DatabaseError,info:
        module_logger.info( _("Logon  Error:"),info)
        for env in ["PATH","LD_LIBRARY_PATH","ORACLE_HOME","TNS_ADMIN"]:
            try:
                module_logger.info( "{}={}".format(env,os.environ[env]))
            except:pass
        module_logger.info( sys.exc_info())
        sys.exit(-1)
    except:
        module_logger.info( _("Connect error"))
        for env in ["PATH","LD_LIBRARY_PATH","ORACLE_HOME","TNS_ADMIN"]:
            try:
                module_logger.info( "{}={}".format(env,os.environ[env]))
            except:pass
        module_logger.info( sys.exc_info())
        sys.exit(-1)

    if not schema is None:
        module_logger.info( _("Set schema:{}").format(schema))
        conn.current_schema=schema
    return conn  
#===============================================================================
#--- execute sql and dont return result
#===============================================================================
def sqlExecuteWithoutResult(sqlStr,cursor):
    try:
        cursor.execute(sqlStr)
    except:
        module_logger.error( _("Error while executing: {}").format(sqlStr))
        module_logger.error( sys.exc_info())
        return -1
    return 0
    
#===============================================================================
#--- execute sql and return result
#===============================================================================
def sqlExecuteWithResult(sqlStr,cursor):
    """
        @return: pandas data frame 
    """
    res_DF=None
    module_logger.debug( _("Executing: {}").format(sqlStr))
    try:
        res_DF=psql.read_sql(sql=sqlStr, con=cursor.connection)#, index_col, coerce_float, params, parse_dates, columns)
        #res_DF=psql.frame_query(sqlStr, cursor.connection)
        module_logger.debug( _("Successfully executed"))
    except:
        module_logger.error( _("Error while executing"))
        module_logger.error( sys.exc_info())
        return -1
    return res_DF
#===============================================================================
#--- make Union sql by splitting 'listOfFilters'
#===============================================================================
def sql2UnionFormat(sqlStr,listOfFilters,filtersLimit=2):
    """
        @param: sqlStr
                    string with '{}' for 'format' command to insert 'listOfFilters'
                    like "select distinct WELL_ID from V_PROD_PARAM where WELL_ID in {}"
        @param: listOfFilters
                    list of value to insert to sql str
        @return: new sql
         
    """
    step=filtersLimit
    sub_sqls=[]
    for sub_list in [listOfFilters[x:x+step] for x in xrange(0, len(listOfFilters), step)]:
        sub_str=join2str(val_list=sub_list)
        sub_sqls.append("({})".format(sqlStr.format(sub_str)))
    return " union all ".join(sub_sqls)
        
