from __future__ import division

from struct import unpack_from
import re

import numpy

from tig_loader.config import Config
from tig_loader.test_utils import DB_PATH
from tig_loader.utils import StrictInit


config = Config(db_path=DB_PATH)


def go(queries):
    for connection in config.get_connections():
        gdb = connection.get_db()
        projects = [row[0] for row in gdb.execute('''
    SELECT
        p.PROJECT_NAME
    FROM
        GLOBAL.project p
    ORDER BY
        p.PROJECT_NAME
    ''')]

        print '>', connection.name
        for project in projects:
            first_project = True
            first_query = True
            for q in queries:
                if not re.match(q.filter, connection.name + '_' + project):
                    continue
                if first_project:
                    first_project = False
                    print '>>', project
                    db = connection.get_db(project)
                for row in db.execute(q.sql):
                    if first_query:
                        print connection.name, project, q.name
                        first_query = False
                    print row


class Q(StrictInit):
    name = None
    filter = '.*'
    sql = None

queries = []
0 and queries.append(Q(
    name='len(tig_map_x) != len(tig_map_y)',
    filter_projects='china petrel tagr chinar2 chinar_corr chinar_tmp kalamkas2'.split(),
    sql='''
SELECT
    DBMS_LOB.GETLENGTH(mss.TIG_MAP_X),
    DBMS_LOB.GETLENGTH(mss.TIG_MAP_Y),
    mss.*
FROM
    tig_map_subset mss
WHERE
    DBMS_LOB.GETLENGTH(mss.TIG_MAP_X) != DBMS_LOB.GETLENGTH(mss.TIG_MAP_Y)
''',
))
0 and queries.append(Q(
    name='len(tig_map_z) != 0',
    filter_projects='webtest1'.split(),
    sql='''
SELECT
    mss.*
FROM
    tig_map_subset mss
WHERE
    DBMS_LOB.GETLENGTH(mss.TIG_MAP_Z) != 0
''',
))
0 and queries.append(Q(
    name='surfaces use only TIG_MAP_PARAM_VRSHRT',
    sql='''
SELECT
    DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VINTS),
    DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VRSHRT),
    DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VRLONG),
    DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VCHAR),
    mssp.TIG_MAP_SET_NO,
    ms.TIG_MAP_SET_TYPE
FROM
    TIG_MAP_SUBSET_PARAM_VAL mssp,
    TIG_MAP_SET ms
WHERE
    mssp.TIG_MAP_SET_NO = ms.TIG_MAP_SET_NO
    AND(NOT DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VINTS) = 0
    OR NOT DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VRSHRT) != 0
    OR NOT DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VRLONG) = 0
    OR NOT DBMS_LOB.GETLENGTH(mssp.TIG_MAP_PARAM_VCHAR) = 0)
    AND ms.TIG_MAP_SET_TYPE = 4
''',
))
0 and queries.append(Q(
    name='TIG_MAP_SUBSET_GEOM_DATA is not used',
    sql='''
SELECT
    *
FROM
    TIG_MAP_SUBSET mss
WHERE
    DBMS_LOB.GETLENGTH(mss.TIG_MAP_SUBSET_GEOM_DATA) != 0
''',
))
0 and queries.append(Q(
    name='TIG_MAP_SUBSET_GEOM_DATA is not used',
    sql='''
SELECT
    *
FROM
    TIG_MAP_SUBSET mss
WHERE
    DBMS_LOB.GETLENGTH(mss.TIG_MAP_SUBSET_GEOM_DATA) != 0
''',
))
0 and queries.append(Q(
    name='TIG_VARIABLE types',
    sql='''
SELECT
    v.*
FROM
    tig_variable v
WHERE(v.TIG_VARIABLE_TYPE != 2)
    OR(NOT(v.TIG_VARIABLE_TIGRESS IN(0, 1)))
    OR(v.TIG_DESCRIPTION IS NOT NULL)
    OR(v.TIG_UNIT_NAME IS NOT NULL)
    OR(v.TIG_VARIABLE_ABBR IS NOT NULL)
''',
))
0 and queries.append(Q(
    name='intervals with multiple well_intervals',
    filter='everest_demo2007',
    sql='''
SELECT
    wh.TIG_LATEST_WELL_NAME,
    z.TIG_DESCRIPTION,
    i.TIG_INTERVAL_NAME,
    (SELECT
        COUNT( *)
    FROM
        tig_well_interval wi
    WHERE
        wi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
        AND wi.TIG_WELL_SLDNID = wh.DB_SLDNID
        AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    )
FROM
    tig_zonation z,
    tig_interval i,
    tig_well_history wh
WHERE(SELECT
        COUNT( *)
    FROM
        tig_well_interval wi
    WHERE
        wi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
        AND wi.TIG_WELL_SLDNID = wh.DB_SLDNID
        AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID) > 1
''',
))

0 and queries.append(Q(
    name='intervals with multiple well_intervals',
    #filter='everest_demo2007',
    sql='''
SELECT
    wh.TIG_LATEST_WELL_NAME,
    z.TIG_DESCRIPTION,
    i.TIG_INTERVAL_NAME,
    (SELECT
        COUNT( *)
    FROM
        tig_well_interval wi
    WHERE
        wi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
        AND wi.TIG_WELL_SLDNID = wh.DB_SLDNID
        AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    )
FROM
    tig_zonation z,
    tig_interval i,
    tig_well_history wh
WHERE(SELECT
        COUNT( *)
    FROM
        tig_well_interval wi
    WHERE
        wi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
        AND wi.TIG_WELL_SLDNID = wh.DB_SLDNID
        AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID) > 1
''',
))


def g1():
    t = config.connections.by_unique_name['everest'].get_db('webtest1').fetch_assoc_all('''
SELECT
    ms.DB_CARTO_PRJTNDEF_SLDNID,
    ms.DB_INSTANCE_TIME_STAMP,
    ms.DB_NOTEPAD_SLDNID,
    ms.DB_SLDNID,
    ms.MASTER_GRID_SLDNID,
    ms.TIG_CLIP_X_MAX_LIMIT,
    ms.TIG_CLIP_X_MIN_LIMIT,
    ms.TIG_CLIP_Y_MAX_LIMIT,
    ms.TIG_CLIP_Y_MIN_LIMIT,
    ms.TIG_CLIP_Z_MAX_LIMIT,
    ms.TIG_CLIP_Z_MIN_LIMIT,
    ms.TIG_DESCRIPTION,
    ms.TIG_GLOBAL_DATA_FLAG,
    ms.TIG_INTERPRETER_SLDNID,
    ms.TIG_INTERVAL_SLDNID,
    ms.TIG_MAP_GROUP_NAME,
    ms.TIG_MAP_SET_NAME,
    ms.TIG_MAP_SET_NO,
    ms.TIG_MAP_SET_SOURCE_TYPE,
    ms.TIG_MAP_SET_TYPE,
    ms.TIG_MAP_X_MAX,
    ms.TIG_MAP_X_MIN,
    ms.TIG_MAP_Y_MAX,
    ms.TIG_MAP_Y_MIN,
    ms.TIG_MAP_Z_MAX,
    ms.TIG_MAP_Z_MIN,
    ms.TIG_SIMULTN_MODEL_NO,
    ms.TIG_X_PARALLEL_ROTATION,
    ms.TIG_X_PARA_ROTN_Y_COORD,
    ms.TIG_X_PARA_ROTN_Z_COORD,
    ms.TIG_X_SCALING_FACTOR,
    ms.TIG_X_SCAL_FACT_REF_POS,
    ms.TIG_X_TRANSLATION,
    ms.TIG_Y_PARALLEL_ROTATION,
    ms.TIG_Y_PARA_ROTN_X_COORD,
    ms.TIG_Y_PARA_ROTN_Z_COORD,
    ms.TIG_Y_SCALING_FACTOR,
    ms.TIG_Y_SCAL_FACT_REF_POS,
    ms.TIG_Y_TRANSLATION,
    ms.TIG_ZONATION_SLDNID,
    ms.TIG_Z_PARALLEL_ROTATION,
    ms.TIG_Z_PARA_ROTN_X_COORD,
    ms.TIG_Z_PARA_ROTN_Y_COORD,
    ms.TIG_Z_SCALING_FACTOR,
    ms.TIG_Z_SCAL_FACT_REF_POS,
    ms.TIG_Z_TRANSLATION,
    msp.DB_INSTANCE_TIME_STAMP AS DB_INSTANCE_TIME_STAMP1,
    msp.DB_NOTEPAD_SLDNID AS DB_NOTEPAD_SLDNID1,
    msp.DB_SLDNID AS DB_SLDNID1,
    msp.TIG_DESCRIPTION AS TIG_DESCRIPTION1,
    msp.TIG_GLOBAL_DATA_FLAG AS TIG_GLOBAL_DATA_FLAG1,
    msp.TIG_INTERPRETER_SLDNID AS TIG_INTERPRETER_SLDNID1,
    msp.TIG_MAP_SET_CP_SOURCE,
    msp.TIG_MAP_SET_NO AS TIG_MAP_SET_NO1,
    msp.TIG_MAP_SET_PARAMETER_NO,
    msp.TIG_MAP_SET_X_MAX,
    msp.TIG_MAP_SET_X_MIN,
    msp.TIG_MAP_SET_Y_MAX,
    msp.TIG_MAP_SET_Y_MIN,
    msp.TIG_MAP_VARIABLE_SLDNID,
    msp.TIG_PARAM_LONG_NAME,
    msp.TIG_PARAM_SHORT_NAME,
    mss.DB_INSTANCE_TIME_STAMP AS DB_INSTANCE_TIME_STAMP2,
    mss.DB_NOTEPAD_SLDNID AS DB_NOTEPAD_SLDNID2,
    mss.DB_SLDNID AS DB_SLDNID2,
    mss.TIG_COMPUTED_DEV_SLDNID,
    mss.TIG_DESCRIPTION AS TIG_DESCRIPTION2,
    mss.TIG_GLOBAL_DATA_FLAG AS TIG_GLOBAL_DATA_FLAG2,
    mss.TIG_INTERPRETER_SLDNID AS TIG_INTERPRETER_SLDNID2,
    mss.TIG_MAP_SET_NO AS TIG_MAP_SET_NO2,
    mss.TIG_MAP_SUBSET_GEOM,
    mss.TIG_MAP_SUBSET_GEOM_DATA,
    mss.TIG_MAP_SUBSET_NAME,
    mss.TIG_MAP_SUBSET_NO,
    mss.TIG_MAP_SUBSET_X_MAX,
    mss.TIG_MAP_SUBSET_X_MIN,
    mss.TIG_MAP_SUBSET_Y_MAX,
    mss.TIG_MAP_SUBSET_Y_MIN,
    mss.TIG_MAP_SUBSET_Z_MAX,
    mss.TIG_MAP_SUBSET_Z_MIN,
    mss.TIG_MAP_X,
    mss.TIG_MAP_Y,
    mss.TIG_MAP_Z,
    mss.TIG_WELL_IDENTIFIER,
    mssp.DB_NOTEPAD_SLDNID AS DB_NOTEPAD_SLDNID3,
    mssp.DB_SLDNID AS DB_SLDNID3,
    mssp.TIG_DESCRIPTION AS TIG_DESCRIPTION3,
    mssp.TIG_GLOBAL_DATA_FLAG AS TIG_GLOBAL_DATA_FLAG3,
    mssp.TIG_INTERPRETER_SLDNID AS TIG_INTERPRETER_SLDNID3,
    mssp.TIG_MAP_PARAM_VCHAR,
    mssp.TIG_MAP_PARAM_VINTS,
    mssp.TIG_MAP_PARAM_VRLONG,
    mssp.TIG_MAP_PARAM_VRSHRT,
    mssp.TIG_MAP_SET_NO AS TIG_MAP_SET_NO3,
    mssp.TIG_MAP_SET_PARAMETER_NO AS TIG_MAP_SET_PARAMETER_NO1,
    mssp.TIG_MAP_SUBSET_NO AS TIG_MAP_SUBSET_NO1,
    mssp.TIG_SUBSET_V_MAX,
    mssp.TIG_SUBSET_V_MIN,
    mssp.TIG_SUBSET_V_NULLS
FROM
    TIG_MAP_SET ms,
    TIG_MAP_SET_PARAM msp,
    TIG_MAP_SUBSET mss,
    TIG_MAP_SUBSET_PARAM_VAL mssp
WHERE
    ms.TIG_MAP_SET_NO = msp.TIG_MAP_SET_NO
    AND ms.TIG_MAP_SET_NO = mss.TIG_MAP_SET_NO
    AND ms.TIG_MAP_SET_NO = mssp.TIG_MAP_SET_NO
    AND mssp.TIG_MAP_SET_PARAMETER_NO = msp.TIG_MAP_SET_PARAMETER_NO
    AND mssp.TIG_MAP_SUBSET_NO = mss.TIG_MAP_SUBSET_NO
    AND ms.TIG_MAP_SET_NO = 15
''')

    for tt in t:
        #print tt
        rr = {}
        for k, v in tt.items():
            if hasattr(v, 'read'):
                rr[k] = len(v.read())
        print rr


def g2():
    t = config.connections.by_unique_name['everest'].get_db('webtest1').fetch_assoc_all('''
SELECT
    ms.TIG_MAP_SET_NO,
    msp.TIG_MAP_SET_PARAMETER_NO,
    mss.TIG_MAP_SUBSET_NO,
    ms.TIG_MAP_SET_NAME,
    msp.TIG_PARAM_LONG_NAME,
    mss.TIG_MAP_SUBSET_NAME,
    mss.TIG_MAP_X,
    mss.TIG_MAP_Y,
    mss.TIG_MAP_Z,
    mssp.TIG_MAP_PARAM_VRSHRT
FROM
    TIG_MAP_SET ms,
    TIG_MAP_SET_PARAM msp,
    TIG_MAP_SUBSET mss,
    TIG_MAP_SUBSET_PARAM_VAL mssp
WHERE
    ms.TIG_MAP_SET_NO = msp.TIG_MAP_SET_NO
    AND ms.TIG_MAP_SET_NO = mss.TIG_MAP_SET_NO
    AND ms.TIG_MAP_SET_NO = mssp.TIG_MAP_SET_NO
    AND mssp.TIG_MAP_SET_PARAMETER_NO = msp.TIG_MAP_SET_PARAMETER_NO
    AND mssp.TIG_MAP_SUBSET_NO = mss.TIG_MAP_SUBSET_NO
    AND ms.TIG_MAP_SET_TYPE = 4
    and msp.TIG_PARAM_LONG_NAME='BotTVD'
''')
    for tt in t:
        print tt
        X = numpy.fromstring(tt['TIG_MAP_X'].read(), '>d').astype('d')
        print X
        Y = numpy.fromstring(tt['TIG_MAP_Y'].read(), '>d').astype('d')
        print Y
        print numpy.fromstring(tt['TIG_MAP_Z'].read(), '>d').astype('d')
        dd = numpy.fromstring(tt['TIG_MAP_PARAM_VRSHRT'].read(), '>f')
        print X[0], X[1], X[2], (X[1] - X[0]) / X[2], (Y[1] - Y[0]) / Y[2]
        print dd.size, dd


def dbg_all_projections():
    sql = '''
SELECT
    cp.DB_SLDNID AS "cp.DB_SLDNID",
    cp.DB_CARTO_PROJECTION_NAME AS "cp.DB_CARTO_PROJECTION_NAME",
    cp.DB_CARTO_REFERENCE_CODE AS "cp.DB_CARTO_REFERENCE_CODE",
    cpd.DB_SLDNID,
    cpd.DB_CARTO_USER_NAME,
    cpd.DB_COMMENT,
    cpd.DB_CARTO_PROJECTN_SLDNID,
    cpd.DB_CARTO_DATUM_SLDNID,
    cpd.DB_CARTO_SPHEROID_SLDNID,
    cpd.DB_CARTO_PARAMS_SLDNID,
    cpd.DB_CARTO_EXTERNAL_UNITS,
    cpd.DB_CARTO_DEF_PARAMS_TYPE,
    cpd.DB_CARTO_DEF_PARAMETERS,
    cpd.DB_CARTO_TYPE
FROM
    db_carto_projection_defs cpd,
    (SELECT
        *
    FROM
        db_carto_projections
    UNION
    SELECT
        *
    FROM
        GLOBAL.db_carto_projections
    ) cp
WHERE
    cp.DB_SLDNID = cpd.DB_CARTO_PROJECTN_SLDNID
'''
    all_rows = {}
    errors = []
    for connection in config.get_connections():
        try:
            gdb = connection.get_db()
            projects = [row[0] for row in gdb.execute('''SELECT p.PROJECT_NAME FROM GLOBAL.project p ORDER BY p.PROJECT_NAME''')]
        except Exception as e:
            errors.append([connection.name, e])
            continue
        print '>', connection.name
        for project in projects:
            print '>>', project
            db = connection.get_db(project)
            for row in db.execute_assoc(sql):
                row['DB_CARTO_DEF_PARAMETERS'] = row['DB_CARTO_DEF_PARAMETERS'].read()
                row['!c'] = connection.name
                row['!p'] = project
                k = tuple(row.items())
                if k not in all_rows:
                    all_rows[k] = 0
                all_rows[k] += 1
            db.disconnect()
        gdb.disconnect()
    for p, e in errors:
        print p, e
    for k in all_rows:
        print sorted(k)


def read_zonation_params(params):
    d = params.read()
    _pos = [0]

    def read_int():
        ret = unpack_from('>i', d, _pos[0])[0]
        _pos[0] += 4
        return ret

    def read_string(count):
        ret = unpack_from('>{}s'.format(count), d, _pos[0])[0]
        _pos[0] += count
        return ret

    def read_float():
        ret = unpack_from('>f', d, _pos[0])[0]
        _pos[0] += 4
        return ret

    zonsld = read_int()
    TIG_VARIABLE_SHORT_NAME_LEN = 8
    TIG_VARIABLE_CHAR_DFLT_LEN = 80
    SQL_INTEGER = 1
    SQL_FLOAT = 2
    SQL_CHARACTER = 4
    well_count = read_int()
    for _i in xrange(well_count):
        well_sld = read_int()
        wint_ct = read_int()
        for _j in xrange(wint_ct):
            wint_sld = read_int()
            para_ct = read_int()
            for _k in xrange(para_ct):
                type = read_int()
                name = read_string(TIG_VARIABLE_SHORT_NAME_LEN).strip()
                if type == SQL_FLOAT:
                    value = read_float()
                elif type == SQL_INTEGER:
                    value = read_int()
                elif type == SQL_CHARACTER:
                    value = read_string(TIG_VARIABLE_CHAR_DFLT_LEN)
                else:
                    raise Exception('bad type {}'.format(type))
                yield zonsld, well_sld, wint_sld, name, type, value


def dbg_zonation_params():
    _, _, params = config.connections.by_unique_name['everest'].get_db('webtest1').fetch('''
SELECT
    z.DB_SLDNID,
    z.TIG_DESCRIPTION,
    z.TIG_ZONATION_PARAMS
FROM
    tig_zonation z
WHERE
    z.DB_SLDNID = 17
''')
    for t in read_zonation_params(params):
        zonation_id, well_id, well_interval_id, parameter_name, parameter_type, parameter_value = t
        if well_id in (33,):  #(1, 7, 33):
            print t


#go(queries)
#g2()
#dbg_all_projections()
#dbg_zonation_params()
