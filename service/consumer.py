import asyncio
import json
import logging.config
from typing import Any

import salt.config

from redis import asyncio as aioredis
from salt.client import get_local_client

from exceptions import StopProcessing
from handlers import MessageHandlerBase, RunJobHandler, RunJobForMasterHandler, PingHandler
from utils import create_all_jobs_from_redis

LOGGER = logging.getLogger(__name__)

__opts__: salt.config.minion_config('/etc/salt/minion')


class SaltConsumer:

    def __init__(
        self,
        redis_client: aioredis.Redis,
        salt_master: str,
        channel: str = '',
        channel_returns: str = ''
    ):
        self.channel = channel
        self.channel_returns = channel_returns

        self.redis_client = redis_client

        self.handlers: list[MessageHandlerBase] = [
            PingHandler(
                redis_client=self.redis_client,
                salt_master=salt_master,
                channel=self.channel,
                channel_returns=channel_returns
            ),
            RunJobHandler(
                redis_client=self.redis_client,
                salt_master=salt_master,
                channel=self.channel,
                channel_returns=channel_returns
            ),
            RunJobForMasterHandler(
                redis_client=self.redis_client,
                salt_master=salt_master,
                channel=self.channel,
                channel_returns=channel_returns
            ),
        ]

    async def handle_message(self, message: Any) -> None:
        if not isinstance(message, bytes):
            return
        message = message.decode()

        LOGGER.debug(message)

        try:
            data = json.loads(message)  # '{"command":"job/create", "payload": {}}'
        except json.JSONDecodeError:
            return

        if not isinstance(data, dict):
            return

        command = data.get('command', '')
        payload = data.get('payload', {})
        message_id = data.get('message_id', None)

        returns = []

        for handler in self.handlers:
            try:
                stop_processing, result = await handler.handle(command, payload)
                if result:
                    returns.append(result)
                if stop_processing:
                    continue
            except StopProcessing:
                continue

        if message_id:
            await self.redis_client.publish(self.channel_returns, json.dumps({
                'message_id': message_id,
                'returns': returns,
            }))

    async def consume(self) -> None:
        await create_all_jobs_from_redis(redis_client=self.redis_client, salt_client=get_local_client())

        LOGGER.info('Starting salt.box bridge service consumer')

        async with self.redis_client.pubsub() as pubsub:
            await pubsub.subscribe(self.channel)

            while True:
                msg = await pubsub.get_message()
                if msg and not msg['type'] == 'subscribe':
                    await self.handle_message(msg['data'])
                await asyncio.sleep(0.01)
