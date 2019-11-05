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
import socket

from tcp_client import TcpClient

__author__ = 'Xianguang Zhou <xianguang.zhou@outlook.com>'
__copyright__ = 'Copyright (C) 2019 Xianguang Zhou <xianguang.zhou@outlook.com>'
__license__ = 'AGPL-3.0'


class Connection:

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def handle(self):
        await self._handleHead()
        await self._handleCommand()

    async def close(self):
        self.writer.close()

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _handleHead(self):
        ver = await self.reader.readexactly(1)
        if ver[0] != 5:
            raise Exception('Socks protocol version is not 5.')
        nmethods = await self.reader.readexactly(1)
        await self.reader.readexactly(nmethods[0])
        self.writer.write(bytes([5, 0]))
        await self.writer.drain()

    async def _handleCommand(self):
        verCmdRsv = await self.reader.readexactly(3)
        cmd = verCmdRsv[1]
        if 1 == cmd:
            await self._handleConnect()
        else:
            raise Exception(f'Can not support "CMD={cmd}".')

    async def _handleConnect(self):
        atyp = await self.reader.readexactly(1)
        atyp = atyp[0]
        if 1 == atyp:
            address = await self.reader.readexactly(4)
            host = socket.inet_ntoa(address)
        elif 3 == atyp:
            domainLength = await self.reader.readexactly(1)
            domain = await self.reader.readexactly(domainLength[0])
            host = domain.decode()
        elif 4 == atyp:
            address = await self.reader.readexactly(16)
            host = socket.inet_ntop(socket.AF_INET6, address)
        else:
            raise Exception(f'Can not support "ATYP={atyp}".')
        port = await self.reader.readexactly(2)
        port = int.from_bytes(port, byteorder='big', signed=False)
        client = TcpClient(host, port, self.reader,
                           self.writer)
        async with client:
            try:
                await client.connect()
            except:
                self.writer.write(bytes([5, 1, 0, 1, 0, 0, 0, 0, 0, 0]))
                await self.writer.drain()
            else:
                await client.run()
