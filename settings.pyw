from __future__ import division as division

from datetime import datetime as datetime 
from functools import total_ordering as total_ordering 
from itertools import izip as izip 
from os import environ, path
from os.path import abspath as abspath
from time import sleep as sleep 
import logging as logging 
import sqlite3 as sqlite3 

environ ['NLS_LANG']='.AL32UTF8'
import sys
sys.path.append(str(path.join(
                                path.dirname(path.abspath(__file__))
                                ,r"libs\x86_64" if sys.maxsize > 2**32 else r"libs\i386"
                            )))
import cx_Oracle as cx_Oracle 


@total_ordering 
class Expando (object ):
    def __init__ (self ,names ,row ):
        self .__dict__ .update (izip (names ,row ))

    def __repr__ (self ):
        return repr (self .__dict__ )

    def __lt__ (self ,other ):
        return self .__dict__ >other .__dict__ 


def make_fetch (execute ):
    def fn (self ,*args ,**kwargs ):
        for row in execute (self ,*args ,**kwargs ):
            return row 
    return fn 


def make_fetch_all (execute ):
    def fn (self ,*args ,**kwargs ):
        return list (execute (self ,*args ,**kwargs ))
    return fn 


class Base (object ):

    @property 
    def connection (self ):
        raise NotImplementedError ()

    def cursor (self ):
        raise NotImplementedError ()

    def __del__ (self ):
        self .disconnect ()

    def __call__ (self ,*args ,**kwargs ):
        return self .execute (*args ,**kwargs )

    def __enter__ (self ):
        return self 

    def __exit__ (self ,*_exc_info ):
        self .disconnect ()

    def fn_assoc (self ,names ,row ):
        assoc_row =dict (zip (names ,row ))
        assert len (names )==len (assoc_row ),'duplicate column names'
        return assoc_row 

    def fn_obj (self ,names ,row ):
        return Expando (names ,row )

    def fn_scalar (self ,_names ,row ):
        return row [0 ]

    def execute (self ,sql ,**kwargs ):
        assert all (value is None or isinstance (value ,(unicode ,int ,datetime ))for value in kwargs .itervalues ()),repr (kwargs )
        return self ._execute (sql ,**kwargs )

    def execute_fn (self ,fn ,sql ,*args ,**kwargs ):
        cursor =self .execute (sql ,*args ,**kwargs )
        names =zip (*cursor .description )[0 ]
        #names = [desc[0] for desc in cursor.description]
        for row in cursor :
            yield fn (names ,row )

    def execute_assoc (self ,sql ,*args ,**kwargs ):
        return self .execute_fn (self .fn_assoc ,sql ,*args ,**kwargs )

    def execute_obj (self ,sql ,*args ,**kwargs ):
        return self .execute_fn (self .fn_obj ,sql ,*args ,**kwargs )

    def execute_scalar (self ,sql ,*args ,**kwargs ):
        return self .execute_fn (self .fn_scalar ,sql ,*args ,**kwargs )

    fetch =make_fetch (execute )
    fetch_all =make_fetch_all (execute )

    def fetchall (self ,sql ,*a ,**kw ):
        return self .execute (sql ,*a ,**kw ).fetchall ()

    fetch_assoc =make_fetch (execute_assoc )
    fetch_assoc_all =make_fetch_all (execute_assoc )

    fetch_obj =make_fetch (execute_obj )
    fetch_obj_all =make_fetch_all (execute_obj )

    fetch_scalar =make_fetch (execute_scalar )
    fetch_scalar_all =make_fetch_all (execute_scalar )

    fetch_fn =make_fetch (execute_fn )
    fetch_fn_all =make_fetch_all (execute_fn )

    def execute_transposed (self ,sql ,*args ,**kwargs ):
        cursor =self .execute (sql ,*args ,**kwargs )
        ret =[[]for _ in cursor .description ]
        for row in cursor :
            cursor .rowcount 
            for i ,cell in enumerate (row ):
                ret [i ].append (cell )
        return ret 

    def names (self ,sql ,*parameters ,**kwargs ):
        if hasattr (sql ,'description'):
            cursor =sql 
        else :
            cursor =self .execute (sql ,*parameters ,**kwargs )
        return [desc [0 ]for desc in cursor .description ]


class Oracle (Base ):
    Error =cx_Oracle .Error 
    DatabaseError =cx_Oracle .DatabaseError 

    def __init__ (self ,user ,password ,server =None ,schema =None ,lazy_connect =False ,host =None ,port =None ,sid =None ):
        self .user =user 
        self .password =password 
        self .host =host 
        self .port =port 
        self .sid =sid 
        self .server =self ._make_server (server ,host ,port ,sid )

        self .schema =schema 
        self ._connection =None if lazy_connect else self ._connect ()

    @classmethod 
    def _make_server (cls ,server ,host ,port ,sid ):
        assert (
        server is not None and host is None and port is None and sid is None 
        or server is None and host is not None and port is not None and sid is not None 
        ),'give server or host, port, sid'
        if server :
            return server 
        else :
            return cx_Oracle .makedsn (host ,port ,sid )

    def __repr__ (self ):
        if self .host is not None :
            return repr ({'host':self .host ,'port':self .port ,'sid':self .sid ,'user':self .user ,'schema':self .schema })
        else :
            return repr ({'server':self .server ,'user':self .user ,'schema':self .schema })

    def to_short_repr (self ):
        if self .host is not None :
            return (self .host ,self .port ,self .sid ,self .user ,self .schema )
        else :
            return (self .host ,self .user ,self .schema )

    @property 
    def connection (self ):
        if self ._connection is None :
            self ._connection =self ._connect ()
        return self ._connection 

    def _connect (self ):
        connection =cx_Oracle .connect (self .user ,self .password ,self .server )
        if self .schema is not None :
            cursor =connection .cursor ()
            cursor .execute ('alter session set current_schema=%s'%self .schema )
        return connection 

    def cursor (self ):
        return self .connection .cursor ()

    def disconnect (self ):
        self ._connection =None 

    _reconnection_exception_codes =frozenset ([
    28 ,# cx_Oracle.DatabaseError: ORA-00028: your session has been killed
    3113 ,# cx_Oracle.OperationalError: ORA-03113: end-of-file on communication channel
    3114 ,# cx_Oracle.OperationalError: ORA-03114: not connected to ORACLE
    12571 ,# cx_Oracle.OperationalError: ORA-12571: TNS:packet writer failure
    ])

    def _is_reconnect_exception (self ,e ):
        if not hasattr (e .args [0 ],'code'):
            return False 
        code =e .args [0 ].code 
        return code in self ._reconnection_exception_codes 

    def _execute (self ,sql ,**kwargs ):
        kwargs ={k .encode ('ascii'):v .encode ('ascii')if isinstance (v ,unicode )else v for k ,v in kwargs .iteritems ()}
        attempts =2 
        while attempts >0 :
            attempts -=1 
            cursor =self .cursor ()
            try :
                cursor .execute (sql ,kwargs )
                return cursor 
            except cx_Oracle .DatabaseError as e :
                if attempts >0 and self ._is_reconnect_exception (e ):
                    logging .exception ('!!! oracle exception, possible connection timeout, try reconnect')
                    self .disconnect ()
                else :
                    raise 


class Sqlite (Base ):
    Error =sqlite3 .Error 
    IntegrityError =sqlite3 .IntegrityError 

    def __init__ (self ,path ,lazy_connect =False ,commit_on_close =True ):
        self .path =abspath (path )
        self ._connection =None if lazy_connect else self ._connect ()
        self ._commit_on_close =commit_on_close 

    def __repr__ (self ):
        return repr ({'path':self .path })

    @property 
    def connection (self ):
        if self ._connection is None :
            self ._connection =self ._connect ()
        return self ._connection 

    def _connect (self ):
        try :
            return sqlite3 .connect (self .path )
        except Exception as e :
            e .args =e .args +(self .path ,)
            raise 

    def cursor (self ):
        return self .connection .cursor ()

    def disconnect (self ):
        if self ._connection is not None :
            if self ._commit_on_close :
                self ._connection .commit ()
            self ._connection .close ()
            self ._connection =None 

    def _execute (self ,sql ,**kwargs ):
        reexecute_interval =1 
        attempts =5 
        while attempts >0 :
            attempts -=1 
            cursor =self .cursor ()
            try :
                cursor .execute (sql ,kwargs )
                return cursor 
            except sqlite3 .OperationalError :
                raise 
                raise 'check me'
                logging .exception ('!!! possible locked database, try reexecute')
                sleep (reexecute_interval )

        raise 'Error'



class StrictInit (object ):
    def __init__ (self ,**kw ):
        assert not set (kw ).difference (dir (self .__class__ )),'{0} does not declare fields {1}'.format (self .__class__ ,list (set (kw ).difference (dir (self .__class__ ))))
        self .__dict__ .update (kw )


class Args (StrictInit ):
    args =None 


class Exc (Exception ):
    pass 


class cached_property (object ):

    def __init__ (self ,func ,name =None ,doc =None ):
        self .__name__ =name or func .__name__ 
        self .__module__ =func .__module__ 
        self .__doc__ =doc or func .__doc__ 
        self .func =func 

    def __get__ (self ,obj ,type =None ):
        if obj is None :
            return self 
        value =self .func (obj )
        setattr (obj ,self .__name__ ,value )
        return value 

import json as json 
import os as os 







class TigressConnection (StrictInit ):
    args =None 

    @cached_property 
    def id (self ):
        return int (self .args ['id'])

    @cached_property 
    def name (self ):
        return unicode (self .args ['name'])

    @cached_property 
    def options (self ):
        return json .loads (self .args ['options'])

    @cached_property 
    def host (self ):
        return unicode (self .options ['host'])

    @cached_property 
    def port (self ):
        return int (self .options .get ('port',1521 ))

    @cached_property 
    def sid (self ):
        return unicode (self .options .get ('sid','TIG11G'))

    @cached_property 
    def user (self ):
        return unicode (self .options ['user'])

    @cached_property 
    def password (self ):
        return unicode (self .options ['password'])

    def get_db (self ,project =None ):
        return Oracle (
        user =self .user ,
        password =self .password ,
        host =self .host ,
        port =self .port ,
        sid =self .sid ,
        schema =project ,
        )


class TigressSQliteConnection (TigressConnection ):

    @cached_property 
    def path (self ):
        ' oracle users password '
        return unicode (self .options ['path'])

    def get_db (self ,project ='global'):
        ' create and return SQLite db '
        dbPath =os .path .abspath (os .path .join (self .path ,project ))
        globalPath =os .path .abspath (os .path .join (self .path ,'global'))
        db =Sqlite (dbPath )
        db .execute ("attach '{0}' as global".format (globalPath ))
        return db 



def create_connection (args ):
    return connection_types [args ['type']](args =args )

connection_types ={
'tigress':TigressConnection ,
'sqlite':TigressSQliteConnection ,
}

from Tkconstants import DISABLED as DISABLED 
from Tkconstants import TRUE as TRUE 
from Tkinter import E as E 
from Tkinter import N as N 
from Tkinter import NSEW as NSEW 
from Tkinter import S as S 
from Tkinter import StringVar as StringVar 
from Tkinter import Tk as Tk 
from os .path import abspath as abspath 
from tkMessageBox import askyesno as askyesno 
from tkMessageBox import showerror as showerror 
from tkMessageBox import showinfo as showinfo 
import tkFileDialog as tkFileDialog 
from ttk import Button as Button 
from ttk import Entry as Entry 
from ttk import Frame as Frame 
from ttk import Label as Label 
from ttk import Treeview as Treeview 
import json as json 





WIDGET_CONNECTIONS ='widget_connections'
WIDGET_CONNECTION ='widget_connection'
WIDGET_CONNECTION_SQLITE ='widget_connection_sqlite'
WIDGET_TOOLS ='widget_tools'
WIDGET_TOOL ='widget_tool'


def to_unicode (s ):
    if isinstance (s ,unicode ):
        return s 
    return s .decode ('utf-8')


class Db (object ):
    def __init__ (self ,db_path ):
        self .db =Sqlite (db_path )

    def enumerate_connections (self ):
        return self .db .execute ('select id, name, type from connections order by name, id')

    def get_connection (self ,id ):
        row =self .db .fetch_assoc ('select * from connections where id=:id',id =id )
        row ['options']=json .loads (row ['options'])
        return row 

    def delete_connection (self ,id ):
        self .db .execute ('delete from connections where id=:id',id =id )
        self .db .connection .commit ()

    def create_connection (self ,**args ):
        id =self .db .execute ('insert into connections (type, name, options) values(:type, :name, :options)',**args ).lastrowid 
        self .db .connection .commit ()
        return id 

    def update_connection (self ,**args ):
        self .db .execute ('update connections set type=:type, name=:name, options=:options where id=:id',**args )

    def enumerate_tools (self ):
        return self .db .execute_assoc ('select id, name from tools t order by name, id')


class DetailsWidget (Frame ):
    def __init__ (self ,master ,db ,app ,object_id =None ):
        Frame .__init__ (self ,master )
        self .db =db 
        self .app =app 
        self .object_id =object_id 
        self ._create ()


class ConnectionsWidget (DetailsWidget ):
    def _create (self ):
        self .rowconfigure (0 ,weight =1 )
        self .rowconfigure (1 ,weight =1 )
        self .columnconfigure (0 ,weight =1 )
        new_connection =Button (self ,text ='New ORACLE connection',command =self .on_new_connection )
        new_connection .grid (row =0 ,column =0 )
        new_connection1 =Button (self ,text ='New SQLite connection',command =self .on_new_sqlite_connection )
        new_connection1 .grid (row =1 ,column =0 )

    def on_new_connection (self ):
        self .app .new_connection ()

    def on_new_sqlite_connection (self ):
        self .app .new_sqlite_connection ()


def toggle (widget ,enabled =True ):
    widget .state ([('!'if enabled else '')+DISABLED ])


class ConnectionWidget (DetailsWidget ):
    def _create (self ):
        self .rowconfigure (0 ,weight =1 )
        self .rowconfigure (1 ,weight =1 )
        self .columnconfigure (0 ,weight =1 )

        _next_row =[0 ]

        def next_row ():
            ret =_next_row [0 ]
            _next_row [0 ]+=1 
            return ret 

        def create_buttons ():
            buttons_panel =Frame (self )
            buttons_panel .grid (row =next_row (),column =0 ,sticky =S )

            _next_col =[0 ]

            def create_button (name ,command =None ):
                button =Button (buttons_panel ,text =name ,command =command )
                button .grid (row =0 ,column =_next_col [0 ])
                _next_col [0 ]+=1 
                return button 

            self .test_connection =create_button ('Test',self .on_test_connection )
            self .delete_connection =create_button ('Delete',self .on_delete )
            self .copy =create_button ('Copy',self .on_copy )
            self .save =create_button ('Save',self .on_save )
            self .create =create_button ('Create',self .on_create )

        def create_inputs ():
            inputs_panel =Frame (self ,padding =10 )
            inputs_panel .grid (row =next_row (),column =0 ,sticky =N )

            _next_row =[0 ]

            self ._inputs =[]

            def create_input (name ,**kw ):
                var =StringVar ()
                row =_next_row [0 ]
                _next_row [0 ]+=1 
                Label (inputs_panel ,text =name ).grid (row =row ,column =0 ,sticky =E )
                input =Entry (inputs_panel ,textvariable =var ,cursor ='xterm',**kw )
                input .grid (row =row ,column =1 )
                self ._inputs .append (input )
                return var 

            self .type =StringVar ()
            self .name =create_input ('Name:')
            self .host =create_input ('Host:')
            self .port =create_input ('Port:')
            self .sid =create_input ('Sid:')
            self .user =create_input ('User:')
            self .password =create_input ('Password:')

        create_buttons ()
        create_inputs ()

        if self .object_id is None :
            self .load_new ()
        else :
            self .load_existing ()
        self .update_ui_state ()

    def update_ui_state (self ):
        enabled =self .type .get ()=='tigress'or self .type .get ()=='sqlite'
        new =self .object_id is None 
        for input in self ._inputs :
            toggle (input ,enabled )
        toggle (self .test_connection ,enabled )
        toggle (self .delete_connection ,not new )
        toggle (self .copy ,enabled and not new )
        toggle (self .save ,enabled and not new )
        toggle (self .create ,enabled and new )

    def load_new (self ):
        self .type .set ('tigress')
        self .name .set ('New connection')
        self .host .set ('127.0.0.1')
        self .port .set (1521 )
        self .sid .set ('TIG11G')
        self .user .set ('system')
        self .password .set ('')

    def load_existing (self ):
        d =self .db .get_connection (self .object_id )
        self .type .set (d ['type'])
        if self .type .get ()=='tigress':
            self .name .set (d ['name'])
            self .host .set (d ['options']['host'])
            self .port .set (d ['options']['port'])
            self .sid .set (d ['options']['sid'])
            self .user .set (d ['options']['user'])
            self .password .set (d ['options']['password'])
        else :
            self .name .set (d ['name'])
            self .host .set ('')
            self .port .set ('')
            self .sid .set ('')
            self .user .set ('')
            self .password .set ('')

    def get_ui_options (self ):
        return {
        'id':self .object_id ,
        'name':to_unicode (self .name .get ()),
        'type':u'tigress',
        'options':json .dumps ({
        'host':to_unicode (self .host .get ()),
        'port':to_unicode (self .port .get ()),
        'sid':to_unicode (self .sid .get ()),
        'user':to_unicode (self .user .get ()),
        'password':to_unicode (self .password .get ()),
        'path':'',
        },ensure_ascii =False ),
        }

    def on_delete (self ):
        if not askyesno ('Delete connection','Delete connection {} permanently?'.format (self .name .get ())):
            return 
        try :
            self .db .delete_connection (self .object_id )
            self .app .reload_connections ()
        except Exception as e :
            showerror ('Error',str (e ))

    def on_test_connection (self ):
        connection =create_connection (self .get_ui_options ())
        try :
            db =connection .get_db ()
            projects_count =db .fetch_scalar ('SELECT count(*) FROM  GLOBAL.project')
            showinfo ('Success','Connection sucessuful. Found {} projects.'.format (projects_count ))
        except Exception as e :
            showerror ('Error',str (e ))

    def on_save (self ):
        try :
            self .db .update_connection (**self .get_ui_options ())
        except Exception as e :
            showerror ('Error',str (e ))
        self .app .reload_connections (switch_to =self .object_id )

    def on_create (self ):
        try :
            connection_id =self .db .create_connection (**self .get_ui_options ())
        except Exception as e :
            showerror ('Error',str (e ))
            return 
        self .app .reload_connections (switch_to =connection_id )

    def on_copy (self ):
        options =self .get_ui_options ()
        options ['name']=options ['name']+' copy'
        try :
            connection_id =self .db .create_connection (**options )
        except Exception as e :
            showerror ('Error',str (e ))
            return 
        self .app .reload_connections (switch_to =connection_id )

class SqliteConnectionWidget (ConnectionWidget ):
    def _create (self ):
        self .rowconfigure (0 ,weight =1 )
        self .rowconfigure (1 ,weight =1 )
        self .columnconfigure (0 ,weight =1 )

        _next_row =[0 ]

        def next_row ():
            ret =_next_row [0 ]
            _next_row [0 ]+=1 
            return ret 

        def create_buttons ():
            buttons_panel =Frame (self )
            buttons_panel .grid (row =next_row (),column =0 ,sticky =S )

            _next_col =[0 ]

            def create_button (name ,command =None ):
                button =Button (buttons_panel ,text =name ,command =command )
                button .grid (row =0 ,column =_next_col [0 ])
                _next_col [0 ]+=1 
                return button 

            self .test_connection =create_button ('Test',self .on_test_connection )
            self .delete_connection =create_button ('Delete',self .on_delete )
            self .copy =create_button ('Copy',self .on_copy )
            self .save =create_button ('Save',self .on_save )
            self .create =create_button ('Create',self .on_create )

        def create_inputs ():
            inputs_panel =Frame (self ,padding =10 )
            inputs_panel .grid (row =next_row (),column =0 ,sticky =N )

            _next_row =[0 ]

            self ._inputs =[]

            def create_input (name ,**kw ):
                var =StringVar ()
                row =_next_row [0 ]
                _next_row [0 ]+=1 
                Label (inputs_panel ,text =name ).grid (row =row ,column =0 ,sticky =E )
                input =Entry (inputs_panel ,textvariable =var ,cursor ='xterm',**kw )
                input .grid (row =row ,column =1 )
                self ._inputs .append (input )
                return var 

            def create_button (name ,command =None ):
                row =_next_row [0 ]-1 
                button =Button (inputs_panel ,text =name ,command =command )
                button .grid (row =row ,column =2 )
                return button 

            self .type =StringVar ()
            self .name =create_input ('Name:',width =40 )
            self .path =create_input ('Path:',width =40 )
            self .selfile =create_button ('File',self .on_selfile )

        create_buttons ()
        create_inputs ()

        if self .object_id is None :
            self .load_new ()
        else :
            self .load_existing ()
        self .update_ui_state ()

    def load_new (self ):
        self .type .set ('sqlite')
        self .name .set ('New connection')
        self .path .set ('')

    def load_existing (self ):
        d =self .db .get_connection (self .object_id )
        self .type .set (d ['type'])
        if self .type .get ()=='sqlite':
            self .name .set (d ['name'])
            self .path .set (d ['options']['path'])
        else :
            self .name .set (d ['name'])
            self .path .set ('')

    def get_ui_options (self ):
        return {
        'id':self .object_id ,
        'name':to_unicode (self .name .get ()),
        'type':u'sqlite',
        'options':json .dumps ({
        'host':'',
        'port':'',
        'sid':'',
        'user':'',
        'password':'',
        'path':to_unicode (self .path .get ()),
        },ensure_ascii =False ),
        }

    def on_selfile (self ):
        options ={}
        options ['initialdir']=self .path .get ()

        val =tkFileDialog .askdirectory (**options )
        if val :
            self .path .set (val )


widgets_factory ={
WIDGET_CONNECTIONS :ConnectionsWidget ,
WIDGET_CONNECTION :ConnectionWidget ,
WIDGET_CONNECTION_SQLITE :SqliteConnectionWidget ,
}

connection_factory ={
'tigress':WIDGET_CONNECTION ,
'sqlite':WIDGET_CONNECTION_SQLITE ,
}


class App (object ):
    def __init__ (self ,master ,db_path ):
        db =self .db =Db (db_path )

        master .rowconfigure (0 ,weight =1 )
        master .columnconfigure (0 ,weight =1 )

        main_frame =self .main_frame =Frame (master )
        main_frame .grid (sticky =NSEW )
        main_frame .rowconfigure (0 ,weight =1 )
        main_frame .columnconfigure (0 ,weight =0 )
        main_frame .columnconfigure (1 ,weight =1 )

        tree =self .tree =Treeview (main_frame ,columns =[],selectmode ='browse')
        tree .grid (row =0 ,column =0 ,sticky =NSEW )
        tree .bind ('<<TreeviewSelect>>',self .on_tree_select )

        connections_id =self .connections_id =tree .insert ('','end',text ='Connections',values =[WIDGET_CONNECTIONS ])
        tree .item (connections_id ,open =TRUE )
        for connection_id ,connection_name ,ctype in db .enumerate_connections ():
            tree .insert (connections_id ,'end',text =connection_name ,values =[connection_factory [ctype ],connection_id ])

        tools_id =self .tools_id =tree .insert ('','end',text ='Tools',values =[WIDGET_TOOLS ])
        tree .item (tools_id ,open =TRUE )
        for tool_args in db .enumerate_tools ():
            tree .insert (tools_id ,'end',text =tool_args ['name'],values =[WIDGET_TOOL ,tool_args ['id']])

        self .detail_widget =None 
        if 0 and tree .get_children (connections_id ):
            tree .selection_set (tree .get_children (connections_id )[0 ])
        else :
            tree .selection_set (tree .get_children ()[0 ])

    def reload_connections (self ,switch_to =None ):
        tree =self .tree 
        tree .delete (*tree .get_children (self .connections_id ))
        node_id =self .connections_id 
        for id ,name ,ctype in self .db .enumerate_connections ():
            connection_node_id =self .tree .insert (self .connections_id ,'end',text =name ,values =[connection_factory [ctype ],id ])
            if id ==switch_to :
                node_id =connection_node_id 
        tree .selection_set (node_id )

    def on_tree_select (self ,_event =None ):
        values =self .tree .item (self .tree .selection ()[0 ],'values')
        widget_type_id =values [0 ]
        object_id =int (values [1 ])if len (values )>1 else None 
        self .swith_details (widget_type_id ,object_id )

    def swith_details (self ,widget_type_id ,object_id ):
        if self .detail_widget is not None :
            self .detail_widget .destroy ()
            self .detail_widget =None 

        if widget_type_id in widgets_factory :
            constructor =widgets_factory [widget_type_id ]
            self .detail_widget =constructor (self .main_frame ,app =self ,db =self .db ,object_id =object_id )
            self .detail_widget .grid (row =0 ,column =1 ,sticky =NSEW )

    def new_connection (self ):
        self .swith_details (WIDGET_CONNECTION ,None )

    def new_sqlite_connection (self ):
        self .swith_details (WIDGET_CONNECTION_SQLITE ,None )


def main ():
    db_path =abspath (__file__ +'/../TigLoader.sqlite')
    root =Tk ()
    _app =App (root ,db_path =db_path )
    root .title ('Settings {}'.format (db_path ))
    root .geometry ('650x320')
    root .mainloop ()


if __name__ =='__main__':
    main ()
