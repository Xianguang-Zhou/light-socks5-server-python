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
from asyncio import StreamReader, StreamWriter

__author__ = 'Xianguang Zhou <xianguang.zhou@outlook.com>'
__copyright__ = 'Copyright (C) 2019 Xianguang Zhou <xianguang.zhou@outlook.com>'
__license__ = 'AGPL-3.0'


async def relay(srcReader: StreamReader, srcWriter: StreamWriter,
                dstReader: StreamReader, dstWriter: StreamWriter):
    upTask = asyncio.create_task(_transmit(srcReader, dstWriter))
    upTask._log_destroy_pending = False
    downTask = asyncio.create_task(_transmit(dstReader, srcWriter))
    downTask._log_destroy_pending = False
    await asyncio.wait([upTask, downTask], return_when=asyncio.ALL_COMPLETED)


async def _transmit(reader: StreamReader, writer: StreamWriter):
    try:
        data = await reader.read(1024)
        while len(data) != 0 and not writer.is_closing():
            writer.write(data)
            await writer.drain()
            data = await reader.read(1024)
    except (ConnectionError, TimeoutError):
        pass
