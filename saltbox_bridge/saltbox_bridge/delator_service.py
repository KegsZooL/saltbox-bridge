from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, TypedDict

import salt.config  # type: ignore[import-untyped]
from faststream import context

if TYPE_CHECKING:
    from faststream.redis import RedisBroker
    from redis.asyncio.client import Redis
from salt.utils.event import get_master_event  # type: ignore[import-untyped]

from saltbox_bridge.config import SETTINGS, configure_logging
from saltbox_bridge.event_bus.faststream_redis import get_faststream_broker
from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.exceptions import StopProcessing
from saltbox_bridge.redis import get_redis_client
from saltbox_bridge.salt_handlers.job_return_handler import JobReturnMessageHandler
from saltbox_bridge.salt_handlers.metrics_handler import SaltMessageMetricMessageHandler
from saltbox_bridge.salt_handlers.minion_started_handler import MinionStartedMessageHandler
from saltbox_bridge.salt_handlers.new_job_handler import JobNewMessageHandler
from saltbox_bridge.salt_handlers.presence_handler import PresenceMessageHandler
from saltbox_bridge.utils.core_connector import CoreConnector

LOGGER = logging.getLogger(__name__)


class HandlersArgs(TypedDict):
    redis_client: Redis
    broker: RedisBroker
    salt_opts: dict
    core_connector: CoreConnector


class SaltBridge:
    def __init__(
        self,
        salt_opts: dict,
    ) -> None:
        self.redis_client = get_redis_client()
        self.salt_opts = salt_opts
        self.master_id: str = self.salt_opts['salt_box_master_id']
        self.core_connector = CoreConnector(master_id=self.master_id)

        context.set_global('core_connector', self.core_connector)
        context.set_global('master_id', self.master_id)

        self.broker = get_faststream_broker(
            redis_conf=SETTINGS.faststream_redis_conf,
            middlewares=[MastersAuthMiddleware],
        )
        handlers_args: HandlersArgs = {
            'redis_client': self.redis_client,
            'broker': self.broker,
            'salt_opts': self.salt_opts,
            'core_connector': self.core_connector,
        }

        self.handlers = [
            SaltMessageMetricMessageHandler(**handlers_args),
            JobNewMessageHandler(**handlers_args),
            JobReturnMessageHandler(**handlers_args),
            PresenceMessageHandler(**handlers_args),
            MinionStartedMessageHandler(**handlers_args),
        ]

    async def start(self) -> None:
        await self.core_connector.wait_success_connection()

        with get_master_event(self.salt_opts, self.salt_opts['sock_dir'], listen=True) as event_bus:
            while True:
                await self.process(event_bus.get_event(full=True, no_block=True))

    async def process(self, event: dict | None) -> None:
        if not event:
            return

        tag = event['tag']
        data = event['data']

        LOGGER.debug('%s got event with tag "%s"', __name__, tag)

        try:
            for handler in self.handlers:
                await handler.handle(tag, data)
        except StopProcessing:
            LOGGER.debug('End message processing')
            return


async def _async_start(salt_opts: dict | None) -> None:
    if salt_opts is None:
        salt_opts = salt.config.client_config('/etc/salt/master')
    configure_logging(format=f'{salt_opts["log_fmt_console"]} (Bridge Delator)')
    salt_bridge = SaltBridge(salt_opts=salt_opts)
    await salt_bridge.start()


def start(salt_opts: dict | None = None) -> None:
    coro = _async_start(salt_opts=salt_opts)
    asyncio.run(coro)
