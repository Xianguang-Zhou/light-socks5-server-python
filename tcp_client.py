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
        except (ConnectionError, TimeoutError):
            pass

    async def close(self):
        if self.dstWriter is not None:
            self.dstWriter.close()

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
