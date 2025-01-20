import asyncio
import json
import logging.config
from typing import Any

from redis import asyncio as aioredis

from salt_box_bridge_service.exceptions import StopProcessing
from salt_box_bridge_service.handlers import MessageHandlerBase, RunJobHandler, RunJobForMasterHandler, PingHandler
from salt_box_bridge_service.utils import JobCreator

LOGGER = logging.getLogger(__name__)


class SaltConsumer:

    def __init__(
        self,
        redis_client: aioredis.Redis,
        salt_opts: dict,
        salt_master: str,
        channel: str = '',
        channel_returns: str = ''
    ):
        self.job_creator = JobCreator(salt_opts=salt_opts, redis_client=redis_client)
        self.channel = channel
        self.channel_returns = channel_returns

        self.redis_client = redis_client

        self.handlers: list[MessageHandlerBase] = [
            PingHandler(
                job_creator=self.job_creator,
                salt_master=salt_master
            ),
            RunJobHandler(
                job_creator=self.job_creator,
                salt_master=salt_master
            ),
            RunJobForMasterHandler(
                job_creator=self.job_creator,
                salt_master=salt_master
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
        await self.job_creator.create_all_jobs_from_redis()

        LOGGER.info('Starting salt.box bridge service consumer')

        async with self.redis_client.pubsub() as pubsub:
            await pubsub.subscribe(self.channel)

            while True:
                msg = await pubsub.get_message()
                if msg and not msg['type'] == 'subscribe':
                    await self.handle_message(msg['data'])
                await asyncio.sleep(0.01)
