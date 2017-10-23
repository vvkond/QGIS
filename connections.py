"""
Connesion class
"""

import json

from QgisPDS.db import Oracle
from QgisPDS.utils import StrictInit, cached_property


class TigressConnection(StrictInit):
    """ Class definition """
    args = {}

    @cached_property
    def id(self):
        """connection id"""
        return int(self.args['id'])

    @cached_property
    def name(self):
        """connection name"""
        return unicode(self.args['name'])

    @cached_property
    def options(self):
        """connection option"""
        return json.loads(self.args['options'])

    @cached_property
    def host(self):
        """connecion host """
        return unicode(self.options['host'])

    @cached_property
    def port(self):
        """ oracle port """
        return int(self.options.get('port', 1521))

    @cached_property
    def sid(self):
        """ ORACLE sid """
        return unicode(self.options.get('sid', 'TIG11G'))

    @cached_property
    def user(self):
        """ ORACLE user """
        return unicode(self.options['user'])

    @cached_property
    def password(self):
        """ oracle users password """
        return unicode(self.options['password'])

    def get_db(self, project=None):
        """ create and return oracle db """
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
