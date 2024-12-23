import asyncio
import json
import logging.config
from typing import Any, Literal

import salt.config
from salt.client import get_local_client
from redis import asyncio as aioredis

from exceptions import StopProcessing
from handlers import RunJobHandler, RunJobForMasterHandler, PingHandler
from utils import create_all_jobs_from_redis

LOGGER = logging.getLogger(__name__)

__opts__: salt.config.minion_config('/etc/salt/minion')


class SaltConsumer:

    def __init__(
            self,
            host: str = 'localhost',
            port: int = 6379,
            username: str | None = None,
            password: str | None = None,
            db: int = 0,
            ssl=False,
            ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required',
            ssl_ca_certs: str | None = None,
            channel: str = '',
            channel_returns: str = ''
    ):
        self.host = host
        self.port = port
        self.channel = channel
        self.channel_returns = channel_returns
        self.db = db
        self.username = username
        self.password = password
        self.ssl = ssl
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs

        self.salt_master = 'salt-master'  # TODO: collect salt master

        self.redis_client = aioredis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            username=self.username,
            password=self.password,
            ssl=self.ssl,
            ssl_cert_reqs=self.ssl_cert_reqs,
            ssl_ca_certs=self.ssl_ca_certs,
        )

        self.handlers = [
            PingHandler(
                redis_client=self.redis_client,
                salt_master=self.salt_master,
                channel=self.channel,
                channel_returns = channel_returns
            ),
            RunJobHandler(
                redis_client=self.redis_client,
                salt_master=self.salt_master,
                channel=self.channel,
                channel_returns = channel_returns
            ),
            RunJobForMasterHandler(
                redis_client=self.redis_client,
                salt_master=self.salt_master,
                channel=self.channel,
                channel_returns = channel_returns
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
        await asyncio.sleep(5)  # #FIXME
        await create_all_jobs_from_redis(redis_client=self.redis_client, salt_client=get_local_client())

        async with self.redis_client.pubsub() as pubsub:
            await pubsub.subscribe(self.channel)

            while True:
                msg = await pubsub.get_message()
                if msg and not msg['type'] == 'subscribe':
                    await self.handle_message(msg['data'])
                await asyncio.sleep(0.01)
