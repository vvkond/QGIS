from os.path import abspath

from tig_loader.bimap import BiMap
from tig_loader.connections import create_connection
from tig_loader.db import Sqlite
from tig_loader.tools import create_tool
from tig_loader.utils import StrictInit, cached_property


class Connections(StrictInit):
    items = None

    @cached_property
    def by_id(self):
        return {c.id: c for c in self.items}

    @cached_property
    def unique_bimap(self):
        return BiMap((c.id, c.name) for c in self.items)

    @cached_property
    def unique_names(self):
        return self.unique_bimap.unique_names

    @cached_property
    def by_unique_name(self):
        return {
            unique_name: self.by_id[self.unique_bimap.key_by_unique_name[unique_name]]
            for unique_name in self.unique_bimap.unique_names
        }


class Config(StrictInit):
    arg_db_path = None

    @cached_property
    def db_path(self):
        return abspath(self.arg_db_path)

    @cached_property
    def root_path(self):
        return abspath(self.db_path + '/..')

    @cached_property
    def db(self):
        return Sqlite(self.db_path)

    def enumerate_connections_args(self):
        return self.db.execute_assoc('''
select * from connections c order by c.name'''
)

    def get_connections(self):
        return map(create_connection, self.enumerate_connections_args())

    @cached_property
    def connections(self):
        return Connections(items=self.get_connections())

    def get_connection_args(self, id):
        return self.db.fetch_assoc('''
select * from connections c where c.id=:id
''', id=id)

    def get_connection(self, id):
        return create_connection(self.get_connection_args(id))

    def enumerate_tools_args(self):
        return self.db.execute_assoc('''
select * from tools t where t.enabled order by t.name
''')

    def get_tools(self):
        return [create_tool(args, config=self) for args in self.enumerate_tools_args()]

    def get_tool_args(self, id):
        return self.db.fetch_assoc('''
select * from tools t where t.id=:id order by t.name
''', id=id)

    def get_tool(self, id, **kw):
        return create_tool(self.get_tool_args(id), config=self, **kw)

    def get_tool_args_by_name(self, tool_name):
        return self.db.fetch_assoc('''
select * from tools t where t.tool_name=:tool_name order by t.name
''', tool_name=tool_name)

    def get_tool_by_name(self, tool_name, **kw):
        return create_tool(self.get_tool_args_by_name(tool_name.decode('ascii')), config=self, **kw)
