from __future__ import annotations

import asyncio
import logging

from salt.utils.event import get_master_event

from salt_box_bridge_service.config import SETTINGS
from salt_box_bridge_service.exceptions import StopProcessing
from salt_box_bridge_service.faststream_redis import get_faststream_broker
from salt_box_bridge_service.redis import get_redis_client
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
        salt_opts: dict,
    ) -> None:
        self.redis_client = get_redis_client()
        self.salt_opts = salt_opts
        self.broker = get_faststream_broker(redis_conf=SETTINGS.faststream_redis_conf)
        handlers_args = {
            'redis_client': self.redis_client,
            'broker': self.broker,
            'salt_opts': self.salt_opts,
        }

        self.handlers = [
            JobNewMessageHandler(**handlers_args),
            JobNewForTaskMessageHandler(**handlers_args),
            JobReturnMessageHandler(**handlers_args),
            JobReturnForTaskMessageHandler(**handlers_args),
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


async def _async_start(salt_opts: dict) -> None:
    salt_bridge = SaltBridge(salt_opts=salt_opts)
    await salt_bridge.start()


def start(
    salt_opts: dict,
) -> None:
    coro = _async_start(salt_opts=salt_opts)
    asyncio.run(coro)
