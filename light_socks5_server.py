#!/usr/bin/env python
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
import ipaddress
import socket

__author__ = 'Xianguang Zhou <xianguang.zhou@outlook.com>'
__copyright__ = 'Copyright (C) 2019 Xianguang Zhou <xianguang.zhou@outlook.com>'
__license__ = 'AGPL-3.0'


class TcpClient:

    def __init__(self, host: str, port: int, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.dstHost = host
        self.dstPort = port
        self.srcReader = reader
        self.srcWriter = writer
        self.dstReader = None
        self.dstWriter = None

    async def connect(self):
        self.dstReader, self.dstWriter = await asyncio.open_connection(
            self.dstHost,
            self.dstPort)

    async def run(self):
        self.srcWriter.write(bytes([5, 0, 0]))
        await self.srcWriter.drain()
        (localAddress, localPort) = self.dstWriter.get_extra_info(
            'sockname')
        localIpAddress = ipaddress.ip_address(localAddress)
        if isinstance(localIpAddress, ipaddress.IPv4Address):
            self.srcWriter.write(bytes([1]))
            await self.srcWriter.drain()
            self.srcWriter.write(socket.inet_aton(localAddress))
            await self.srcWriter.drain()
        elif isinstance(localIpAddress, ipaddress.IPv6Address):
            self.srcWriter.write(bytes([4]))
            await self.srcWriter.drain()
            self.srcWriter.write(
                socket.inet_pton(socket.AF_INET6, localAddress))
            await self.srcWriter.drain()
        else:
            raise Exception(f'Can not support "{localAddress}" address.')
        self.srcWriter.write(
            localPort.to_bytes(length=2, byteorder='big', signed=False))
        await self.srcWriter.drain()

        upTask = asyncio.create_task(
            TcpClient._transmit(self.srcReader, self.dstWriter))
        downTask = asyncio.create_task(
            TcpClient._transmit(self.dstReader, self.srcWriter))
        await asyncio.wait([upTask, downTask],
                           return_when=asyncio.ALL_COMPLETED)

    @staticmethod
    async def _transmit(reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter):
        try:
            data = await reader.read(1024)
            while len(data) != 0:
                writer.write(data)
                await writer.drain()
                data = await reader.read(1024)
        except ConnectionError:
            pass

    async def close(self):
        if self.dstWriter is not None:
            self.dstWriter.close()

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


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
        except (ConnectionError, asyncio.streams.IncompleteReadError):
            pass

    async def run(self):
        server = await asyncio.start_server(Server._handleConnection, self.host,
                                            self.port)
        async with server:
            print(f'Serving on "{self.host}:{self.port}".')
            await server.serve_forever()


async def amain():
    s = Server()
    await s.run()


def main():
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
