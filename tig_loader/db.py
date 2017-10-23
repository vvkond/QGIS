from datetime import datetime
from functools import total_ordering
from itertools import izip
from os import environ
from os.path import abspath
from time import sleep
import logging
import sqlite3

environ['NLS_LANG'] = '.AL32UTF8'
import cx_Oracle


@total_ordering
class Expando(object):
    def __init__(self, names, row):
        self.__dict__.update(izip(names, row))

    def __repr__(self):
        return repr(self.__dict__)

    def __lt__(self, other):
        return self.__dict__ > other.__dict__


def make_fetch(execute):
    def fn(self, *args, **kwargs):
        for row in execute(self, *args, **kwargs):
            return row
    return fn


def make_fetch_all(execute):
    def fn(self, *args, **kwargs):
        return list(execute(self, *args, **kwargs))
    return fn


class Base(object):

    @property
    def connection(self):
        raise NotImplementedError()

    def cursor(self):
        raise NotImplementedError()

    def __del__(self):
        self.disconnect()

    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        self.disconnect()

    def fn_assoc(self, names, row):
        assoc_row = dict(zip(names, row))
        assert len(names) == len(assoc_row), 'duplicate column names'
        return assoc_row

    def fn_obj(self, names, row):
        return Expando(names, row)

    def fn_scalar(self, _names, row):
        return row[0]

    def execute(self, sql, **kwargs):
        assert all(value is None or isinstance(value, (unicode, int, datetime)) for value in kwargs.itervalues()), repr(kwargs)
        return self._execute(sql, **kwargs)

    def execute_fn(self, fn, sql, *args, **kwargs):
        cursor = self.execute(sql, *args, **kwargs)
        names = zip(*cursor.description)[0]
        #names = [desc[0] for desc in cursor.description]
        for row in cursor:
            yield fn(names, row)

    def execute_assoc(self, sql, *args, **kwargs):
        return self.execute_fn(self.fn_assoc, sql, *args, **kwargs)

    def execute_obj(self, sql, *args, **kwargs):
        return self.execute_fn(self.fn_obj, sql, *args, **kwargs)

    def execute_scalar(self, sql, *args, **kwargs):
        return self.execute_fn(self.fn_scalar, sql, *args, **kwargs)

    fetch = make_fetch(execute)
    fetch_all = make_fetch_all(execute)

    def fetchall(self, sql, *a, **kw):
        return self.execute(sql, *a, **kw).fetchall()

    fetch_assoc = make_fetch(execute_assoc)
    fetch_assoc_all = make_fetch_all(execute_assoc)

    fetch_obj = make_fetch(execute_obj)
    fetch_obj_all = make_fetch_all(execute_obj)

    fetch_scalar = make_fetch(execute_scalar)
    fetch_scalar_all = make_fetch_all(execute_scalar)

    fetch_fn = make_fetch(execute_fn)
    fetch_fn_all = make_fetch_all(execute_fn)

    def execute_transposed(self, sql, *args, **kwargs):
        cursor = self.execute(sql, *args, **kwargs)
        ret = [[] for _ in cursor.description]
        for row in cursor:
            cursor.rowcount
            for i, cell in enumerate(row):
                ret[i].append(cell)
        return ret

    def names(self, sql, *parameters, **kwargs):
        if hasattr(sql, 'description'):
            cursor = sql
        else:
            cursor = self.execute(sql, *parameters, **kwargs)
        return [desc[0] for desc in cursor.description]


class Oracle(Base):
    Error = cx_Oracle.Error
    DatabaseError = cx_Oracle.DatabaseError

    def __init__(self, user, password, server=None, schema=None, lazy_connect=False, host=None, port=None, sid=None):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.sid = sid
        self.server = self._make_server(server, host, port, sid)

        self.schema = schema
        self._connection = None if lazy_connect else self._connect()

    @classmethod
    def _make_server(cls, server, host, port, sid):
        assert (
            server is not None and host is None and port is None and sid is None
            or server is None and host is not None and port is not None and sid is not None
        ), 'give server or host, port, sid'
        if server:
            return server
        else:
            return cx_Oracle.makedsn(host, port, sid)

    def __repr__(self):
        if self.host is not None:
            return repr({'host': self.host, 'port': self.port, 'sid': self.sid, 'user': self.user, 'schema': self.schema})
        else:
            return repr({'server': self.server, 'user': self.user, 'schema': self.schema})

    def to_short_repr(self):
        if self.host is not None:
            return (self.host, self.port, self.sid, self.user, self.schema)
        else:
            return (self.host, self.user, self.schema)

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._connect()
        return self._connection

    def _connect(self):
        connection = cx_Oracle.connect(self.user, self.password, self.server)
        if self.schema is not None:
            cursor = connection.cursor()
            cursor.execute('alter session set current_schema=%s' % self.schema)
        return connection

    def cursor(self):
        return self.connection.cursor()

    def disconnect(self):
        self._connection = None

    _reconnection_exception_codes = frozenset([
        28,  # cx_Oracle.DatabaseError: ORA-00028: your session has been killed
        3113,  # cx_Oracle.OperationalError: ORA-03113: end-of-file on communication channel
        3114,  # cx_Oracle.OperationalError: ORA-03114: not connected to ORACLE
        12571,  # cx_Oracle.OperationalError: ORA-12571: TNS:packet writer failure
    ])

    def _is_reconnect_exception(self, e):
        if not hasattr(e.args[0], 'code'):
            return False
        code = e.args[0].code
        return code in self._reconnection_exception_codes

    def _execute(self, sql, **kwargs):
        kwargs = {k.encode('ascii'): v.encode('ascii') if isinstance(v, unicode) else v for k, v in kwargs.iteritems()}
        attempts = 2
        while attempts > 0:
            attempts -= 1
            cursor = self.cursor()
            try:
                cursor.execute(sql, kwargs)
                return cursor
            except cx_Oracle.DatabaseError as e:
                if attempts > 0 and self._is_reconnect_exception(e):
                    logging.exception('!!! oracle exception, possible connection timeout, try reconnect')
                    self.disconnect()
                else:
                    raise


class Sqlite(Base):
    Error = sqlite3.Error
    IntegrityError = sqlite3.IntegrityError

    def __init__(self, path, lazy_connect=False, commit_on_close=True):
        self.path = abspath(path)
        self._connection = None if lazy_connect else self._connect()
        self._commit_on_close = commit_on_close

    def __repr__(self):
        return repr({'path': self.path})

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._connect()
        return self._connection

    def _connect(self):
        try:
            return sqlite3.connect(self.path)
        except Exception as e:
            e.args = e.args + (self.path,)
            raise

    def cursor(self):
        return self.connection.cursor()

    def disconnect(self):
        if self._connection is not None:
            if self._commit_on_close:
                self._connection.commit()
            self._connection.close()
            self._connection = None

    def _execute(self, sql, **kwargs):
        reexecute_interval = 1
        attempts = 5
        while attempts > 0:
            attempts -= 1
            cursor = self.cursor()
            try:
                cursor.execute(sql, kwargs)
                return cursor
            except sqlite3.OperationalError:
                raise
                raise 'check me'
                logging.exception('!!! possible locked database, try reexecute')
                sleep(reexecute_interval)

        raise
