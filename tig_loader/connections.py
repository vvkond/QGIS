import json

from tig_loader.db import Oracle
from tig_loader.utils import StrictInit, cached_property


class TigressConnection(StrictInit):
    args = None

    @cached_property
    def id(self):
        return int(self.args['id'])

    @cached_property
    def name(self):
        return unicode(self.args['name'])

    @cached_property
    def options(self):
        return json.loads(self.args['options'])

    @cached_property
    def host(self):
        return unicode(self.options['host'])

    @cached_property
    def port(self):
        return int(self.options.get('port', 1521))

    @cached_property
    def sid(self):
        return unicode(self.options.get('sid', 'TIG11G'))

    @cached_property
    def user(self):
        return unicode(self.options['user'])

    @cached_property
    def password(self):
        return unicode(self.options['password'])

    def get_db(self, project=None):
        return Oracle(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            sid=self.sid,
            schema=project,
        )


def create_connection(args):
    return connection_types[args['type']](args=args)

connection_types = {
    'tigress': TigressConnection,
}
