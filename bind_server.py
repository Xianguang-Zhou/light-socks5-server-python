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

import stream

__author__ = 'Xianguang Zhou <xianguang.zhou@outlook.com>'
__copyright__ = 'Copyright (C) 2019 Xianguang Zhou <xianguang.zhou@outlook.com>'
__license__ = 'AGPL-3.0'


class BindServer:

    def __init__(self, bindHost, clientAddress, clientPort,
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.bindHost = bindHost
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.srcReader = reader
        self.srcWriter = writer
        self.server: asyncio.AbstractServer = None
        self.servingFuture: asyncio.futures.Future = None

    async def bind(self):
        self.server = await asyncio.start_server(self._handleConnection,
                                                 self.bindHost,
                                                 start_serving=False)

    async def run(self):
        self.srcWriter.write(bytes([5, 0, 0]))
        await self.srcWriter.drain()
        bindAddress, bindPort = self.server.sockets[0].getsockname()
        bindIpAddress = ipaddress.ip_address(bindAddress)
        if isinstance(bindIpAddress, ipaddress.IPv4Address):
            self.srcWriter.write(bytes([1]))
            await self.srcWriter.drain()
            self.srcWriter.write(socket.inet_aton(bindAddress))
            await self.srcWriter.drain()
        elif isinstance(bindIpAddress, ipaddress.IPv6Address):
            self.srcWriter.write(bytes([4]))
            await self.srcWriter.drain()
            self.srcWriter.write(socket.inet_pton(socket.AF_INET6, bindAddress))
            await self.srcWriter.drain()
        else:
            raise Exception(f'Can not support "{bindAddress}" address.')
        self.srcWriter.write(
            bindPort.to_bytes(length=2, byteorder='big', signed=False))
        await self.srcWriter.drain()

        self.servingFuture = asyncio.get_running_loop().create_future()
        await self.server.start_serving()
        await self.servingFuture

    async def close(self):
        if self.server is not None:
            self.server.close()

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _handleConnection(self, dstReader: asyncio.StreamReader,
                                dstWriter: asyncio.StreamWriter):
        try:
            asyncio.Task.current_task()._log_destroy_pending = False
            clientAddress, clientPort = dstWriter.get_extra_info('sockname')
            if clientAddress == self.clientAddress and clientPort == self.clientPort:
                self.server.close()
                self.server = None

                self.srcWriter.write(bytes([5, 0, 0]))
                await self.srcWriter.drain()
                clientIpAddress = ipaddress.ip_address(clientAddress)
                if isinstance(clientIpAddress, ipaddress.IPv4Address):
                    self.srcWriter.write(bytes([1]))
                    await self.srcWriter.drain()
                    self.srcWriter.write(socket.inet_aton(clientAddress))
                    await self.srcWriter.drain()
                elif isinstance(clientIpAddress, ipaddress.IPv6Address):
                    self.srcWriter.write(bytes([4]))
                    await self.srcWriter.drain()
                    self.srcWriter.write(
                        socket.inet_pton(socket.AF_INET6, clientAddress))
                    await self.srcWriter.drain()
                else:
                    raise Exception(
                        f'Can not support "{clientAddress}" address.')
                self.srcWriter.write(
                    clientPort.to_bytes(length=2, byteorder='big',
                                        signed=False))
                await self.srcWriter.drain()

                await stream.relay(self.srcReader, self.srcWriter, dstReader,
                                   dstWriter)
                self.servingFuture.set_result(None)
        finally:
            dstWriter.close()
