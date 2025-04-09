from __future__ import annotations

import asyncio
import logging
from typing import Literal

import redis.asyncio as redis
from salt.utils.event import get_master_event

from salt_box_bridge_service.exceptions import StopProcessing
from salt_box_bridge_service.faststream_redis import RedisConf, get_faststream_broker
from salt_box_bridge_service.salt_handlers.job_return_handler import (
    JobReturnForTaskMessageHandler,
    JobReturnMessageHandler,
)
from salt_box_bridge_service.salt_handlers.minion_started_handler import MinionStartedMessageHandler
from salt_box_bridge_service.salt_handlers.new_job_handler import JobNewForTaskMessageHandler, JobNewMessageHandler
from salt_box_bridge_service.salt_handlers.presence_handler import PresenceMessageHandler

LOGGER = logging.getLogger(__name__)


class SaltBridge:
    def __init__(
        self,
        redis_client: redis.Redis,
        redis_conf: RedisConf,
        salt_opts: dict,
        expire: int | None = None,
        master_secret: str | None = None,
    ) -> None:
        self.redis_client = redis_client
        self.salt_opts = salt_opts
        self.broker = get_faststream_broker(redis_conf=redis_conf)
        handlers_args = {
            'redis_client': self.redis_client,
            'broker': self.broker,
            'salt_opts': self.salt_opts,
            'master_secret': master_secret,
        }

        self.handlers = [
            JobNewMessageHandler(**handlers_args),
            JobNewForTaskMessageHandler(**handlers_args),
            JobReturnMessageHandler(**handlers_args, expire=expire),
            JobReturnForTaskMessageHandler(**handlers_args, expire=expire),
            PresenceMessageHandler(**handlers_args),
            MinionStartedMessageHandler(**handlers_args),
        ]

    async def start(self) -> None:
        with get_master_event(self.salt_opts, self.salt_opts['sock_dir'], listen=True) as event_bus:
            while True:
                await self.process(event_bus.get_event(full=True))
                await asyncio.sleep(0.00001)

    async def process(self, event: dict | None) -> None:
        if not event:
            return

        tag = event['tag']
        data = event['data']

        LOGGER.debug('%s got event with tag "%s"', __name__, tag)

        for handler in self.handlers:
            try:
                await handler.handle(tag, data)
            except StopProcessing:
                LOGGER.debug('End message processing')
                return


async def _async_start(
    redis_client: redis.Redis, redis_conf: RedisConf, salt_opts: dict, expire: int | None, master_secret: str | None
) -> None:
    salt_bridge = SaltBridge(
        redis_client=redis_client,
        redis_conf=redis_conf,
        salt_opts=salt_opts,
        expire=expire,
        master_secret=master_secret,
    )
    await salt_bridge.start()


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
    redis_client = redis.Redis(
        host=redis_host,
        port=port,
        db=db,
        username=username,
        password=password,
        ssl=ssl,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
    )
    redis_protocol = 'rediss' if ssl else 'redis'
    redis_conf = RedisConf(
        url=f'{redis_protocol}://{redis_host}:{port}',
        username=username,
        password=password,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
    )
    coro = _async_start(
        redis_client=redis_client,
        redis_conf=redis_conf,
        salt_opts=salt_opts,
        expire=expire,
        master_secret=master_secret,
    )
    asyncio.run(coro)
