from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Literal

import salt.config
from faststream import ContextRepo
from redis import asyncio as aioredis

from salt_box_bridge_service.faststream_redis import RedisConf, get_faststream_app
from salt_box_bridge_service.schemas.base_schemas import AuthMessage
from salt_box_bridge_service.subscribers import router
from salt_box_bridge_service.utils.salt_connector import SaltConnector

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'


async def _async_start(
    salt_opts: dict,
    redis_host: str = 'localhost',
    port: int = 6379,
    username: str | None = None,
    password: str | None = None,
    db: int = 0,
    ssl=False,
    ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required',
    ssl_ca_certs: str | None = None,
    expire: int | None = None,
    master_secret: str | None = None,
) -> None:
    salt_master = salt_opts['salt_box_master_id']

    redis_protocol = 'rediss' if ssl else 'redis'

    redis_conf = RedisConf(
        url=f'{redis_protocol}://{redis_host}:{port}',
        username=username,
        password=password,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
    )

    @asynccontextmanager
    async def lifespan(context: ContextRepo):
        redis_client = aioredis.Redis(
            host=redis_host,
            port=port,
            db=db,
            username=username,
            password=password,
            ssl=ssl,
            ssl_cert_reqs=ssl_cert_reqs,
            ssl_ca_certs=ssl_ca_certs,
        )
        salt_connector = SaltConnector(salt_opts=salt_opts, redis_client=redis_client)
        await salt_connector.create_all_jobs_from_redis()

        context.set_global('redis_client', redis_client)
        context.set_global('redis_expire', expire)
        context.set_global('salt_connector', salt_connector)
        context.set_global('salt_master', salt_master)
        context.set_global('salt_opts', salt_opts)
        context.set_global('master_secret', master_secret)

        yield

        del salt_connector
        del redis_client

    app = get_faststream_app(routers=[router], redis_conf=redis_conf, lifespan=lifespan)

    async with app.broker as br:
        message = AuthMessage(master=salt_master, secret=master_secret)
        await br.publish(message=message, channel='master_auth')  # type: ignore

    await app.run()


def start(
    salt_opts: dict,
    redis_host: str = 'localhost',
    port: int = 6379,
    username: str | None = None,
    password: str | None = None,
    db: int = 0,
    ssl=False,
    ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required',
    ssl_ca_certs: str | None = None,
    expire: int | None = None,
    master_secret: str | None = None,
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
            redis_host=redis_host,
            port=port,
            username=username,
            password=password,
            db=db,
            ssl=ssl,
            ssl_cert_reqs=ssl_cert_reqs,
            ssl_ca_certs=ssl_ca_certs,
            expire=expire,
            master_secret=master_secret,
        )
    )
