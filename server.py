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


class _GetHostIpProtocol(asyncio.DatagramProtocol):

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.hostIpFuture = loop.create_future()

    def connection_made(self, transport: asyncio.DatagramTransport):
        hostIp, _ = transport.get_extra_info('sockname')
        self.hostIpFuture.set_result(hostIp)


async def _getHostIp():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: _GetHostIpProtocol(loop),
        remote_addr=('8.8.8.8', 80))
    try:
        hostIp = await protocol.hostIpFuture
    finally:
        transport.close()
    return hostIp


class Server:

    def __init__(self, host='0.0.0.0', port=1080, bindHost=None):
        self.host = host
        self.port = port
        self.bindHost = bindHost

    async def _handleConnection(self, reader: asyncio.StreamReader,
                                writer: asyncio.StreamWriter):
        try:
            asyncio.Task.current_task()._log_destroy_pending = False
            c = Connection(reader, writer, self.bindHost)
            async with c:
                await c.handle()
        except (ConnectionError, TimeoutError,
                asyncio.streams.IncompleteReadError):
            pass

    async def run(self):
        if self.bindHost is None:
            self.bindHost = await _getHostIp()
        server = await asyncio.start_server(self._handleConnection, self.host,
                                            self.port, start_serving=False)
        async with server:
            for s in server.sockets:
                host, port = s.getsockname()
                print(f'Serving on "{host}:{port}".')
            await server.serve_forever()
