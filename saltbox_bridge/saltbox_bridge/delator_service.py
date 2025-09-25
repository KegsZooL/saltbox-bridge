from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, TypedDict

import salt.config  # type: ignore[import-untyped]
from faststream import context
from prometheus_client import CollectorRegistry

from saltbox_bridge.salt_metrics.service.metric_factory import MetricFactory
from saltbox_bridge.salt_metrics.service.metric_router import MetricRouter

if TYPE_CHECKING:
    from faststream.redis import RedisBroker
    from redis.asyncio.client import Redis
from salt.utils.event import get_master_event  # type: ignore[import-untyped]

from saltbox_bridge.config import SETTINGS, configure_logging
from saltbox_bridge.event_bus.core_connector import CoreConnector
from saltbox_bridge.event_bus.faststream_redis import get_faststream_broker
from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.exceptions import StopProcessing
from saltbox_bridge.redis import get_redis_client
from saltbox_bridge.salt_handlers.job_return_handler import (
    JobReturnForTaskMessageHandler,
    JobReturnMessageHandler,
)
from saltbox_bridge.salt_handlers.minion_started_handler import MinionStartedMessageHandler
from saltbox_bridge.salt_handlers.new_job_handler import JobNewForTaskMessageHandler, JobNewMessageHandler
from saltbox_bridge.salt_handlers.presence_handler import PresenceMessageHandler
from saltbox_bridge.salt_metrics.service.metric_service import start_prometheus_client

LOGGER = logging.getLogger(__name__)
metric_registry = CollectorRegistry()


class HandlersArgs(TypedDict):
    redis_client: Redis
    broker: RedisBroker
    salt_opts: dict


class SaltBridge:
    def __init__(
        self,
        salt_opts: dict,
    ) -> None:
        self.redis_client = get_redis_client()
        self.salt_opts = salt_opts

        self.broker = get_faststream_broker(
            redis_conf=SETTINGS.faststream_redis_conf,
            middlewares=[MastersAuthMiddleware],
        )
        handlers_args: HandlersArgs = {
            'redis_client': self.redis_client,
            'broker': self.broker,
            'salt_opts': self.salt_opts,
        }

        mf = MetricFactory(registry=metric_registry, redis_client=self.redis_client, salt_opts=self.salt_opts)
        metrics = mf.create_all()
        self.metric_router = MetricRouter(metrics=metrics)

        self.handlers = {
            JobNewMessageHandler(**handlers_args),
            JobNewForTaskMessageHandler(**handlers_args),
            JobReturnMessageHandler(**handlers_args),
            JobReturnForTaskMessageHandler(**handlers_args),
            PresenceMessageHandler(**handlers_args),
            MinionStartedMessageHandler(**handlers_args),
        }

    async def start(self) -> None:
        master_id: str = self.salt_opts['salt_box_master_id']
        core_connector = CoreConnector(master_id=master_id)

        context.set_global('core_connector', core_connector)
        context.set_global('master_id', master_id)

        await start_prometheus_client(registry=metric_registry)
        await core_connector.wait_success_connection()

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
        await self.metric_router.route_and_aggregate(tag=tag, data=data)

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
