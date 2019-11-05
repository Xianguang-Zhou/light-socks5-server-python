# -*- coding: utf-8 -*-

# Copyright (C) 2019 Xianguang Zhou <xianguang.zhou@outlook.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio

from connection import Connection

__author__ = 'Xianguang Zhou <xianguang.zhou@outlook.com>'
__copyright__ = 'Copyright (C) 2019 Xianguang Zhou <xianguang.zhou@outlook.com>'
__license__ = 'AGPL-3.0'


class Server:

    def __init__(self, host='0.0.0.0', port=1080):
        self.host = host
        self.port = port

    @staticmethod
    async def _handleConnection(reader: asyncio.StreamReader,
                                writer: asyncio.StreamWriter):
        try:
            c = Connection(reader, writer)
            async with c:
                await c.handle()
        except (ConnectionError, TimeoutError,
                asyncio.streams.IncompleteReadError):
            pass

    async def run(self):
        server = await asyncio.start_server(Server._handleConnection, self.host,
                                            self.port)
        async with server:
            print(f'Serving on "{self.host}:{self.port}".')
            await server.serve_forever()
