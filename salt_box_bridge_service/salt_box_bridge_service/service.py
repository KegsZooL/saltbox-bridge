# Copyright 2025 Ivan Moshkov

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

import salt.config
from faststream import ContextRepo

from salt_box_bridge_service.config import SETTINGS
from salt_box_bridge_service.faststream_redis import get_faststream_app
from salt_box_bridge_service.redis import get_redis_client
from salt_box_bridge_service.schemas.base_schemas import AuthMessage
from salt_box_bridge_service.subscribers import router
from salt_box_bridge_service.utils.salt_connector import SaltConnector

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'


async def _async_start(
    salt_opts: dict,
) -> None:
    salt_master = salt_opts['salt_box_master_id']

    @asynccontextmanager
    async def lifespan(context: ContextRepo):
        redis_client = get_redis_client()

        salt_connector = SaltConnector(salt_opts=salt_opts, redis_client=redis_client)
        await salt_connector.create_all_jobs_from_redis()

        context.set_global('redis_client', redis_client)
        context.set_global('salt_connector', salt_connector)
        context.set_global('salt_master', salt_master)
        context.set_global('salt_opts', salt_opts)

        yield

        del salt_connector
        del redis_client

    app = get_faststream_app(routers=[router], redis_conf=SETTINGS.faststream_redis_conf, lifespan=lifespan)

    async with app.broker as br:
        message = AuthMessage(master=salt_master, secret=SETTINGS.master_secret)
        await br.publish(message=message, channel='master_auth')  # type: ignore

    await app.run()


def start(
    salt_opts: dict,
) -> None:
    if salt_opts is None:
        salt_opts = salt.config.client_config('/etc/salt/master')

    log_level: str = os.getenv('SALT_BRIDGE_SERVICE_LOG_LEVEL', 'INFO')

    logging.basicConfig()
    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    asyncio.run(
        _async_start(
            salt_opts=salt_opts,
        )
    )
