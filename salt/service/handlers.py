import abc
import datetime
import logging
import re
from typing import Any

import salt.client
import salt.config
import salt.exceptions
import salt.grains.core
from redis import asyncio as aioredis
from salt.client import LocalClient

from exceptions import CreateJobError
from utils import create_job_from_redis

LOGGER = logging.getLogger(__name__)

__opts__: salt.config.minion_config('/etc/salt/minion')


class MessageHandlerBase(abc.ABC):
    check_master: bool = False

    def __init__(self, redis_client: aioredis.Redis, salt_master: str, channel: str, channel_returns: str) -> None:
        self.redis_client: aioredis.Redis = redis_client
        self.salt_client: LocalClient | None = None
        self.channel: str = channel
        self.channel_returns: str = channel_returns
        self.salt_master: str = salt_master

    def get_salt_client(self) -> salt.client.LocalClient:
        if self.salt_client is None:
            self.salt_client = salt.client.get_local_client()

        return self.salt_client

    @property
    @abc.abstractmethod
    def COMMAND_PATTERN(self) -> re.Pattern[str]: ...

    async def handle(self, command: str, payload: dict[str, Any]) -> type[bool, Any]:
        """
        If command matches COMMAND_PATTERN, process message

        :raises: StopProcessing when no need to process the message with other handlers
        """
        if match := self.COMMAND_PATTERN.match(command):
            if self.check_master and match.group('master') != self.salt_master:
                return False, None

            return await self.process(match, payload)

        return False, None

    @abc.abstractmethod
    async def process(self, match: re.Match, payload: dict[str, Any]) -> type[bool, Any]:
        """ Take action on message """


class RunJobHandler(MessageHandlerBase):
    """
    Example:
    {
        "command": "job/run",
        "payload": {"tgt": "*", "tgt_type": "glob", "fun": "test.ping", "arg: []. "kwarg": {}}
    }
    """
    COMMAND_PATTERN = re.compile(r'^job/run$')

    async def process(self, match: re.Match, payload: dict[str, Any]) -> type[bool, Any]:
        hash_name: str = payload['hash_name']

        try:
            jid = await create_job_from_redis(
                hash_name=hash_name,
                redis_client=self.redis_client,
                salt_client=self.get_salt_client()
            )
        except CreateJobError as error:
            return False, str(error)

        return True, jid


class RunJobForMasterHandler(RunJobHandler):
    """
    Example:
    {
        "command": "job/run/SALT_MASTER",
        "payload": {"tgt": "*", "tgt_type": "glob", "fun": "test.ping", "arg: []. "kwarg": {}}
    }
    """
    COMMAND_PATTERN = re.compile(r'^job/run/(?P<master>.+)$')
    check_master = True


class PingHandler(MessageHandlerBase):
    """
    Example:
    {"command": "ping", "message_id": "MESSAGE_ID"}
    """
    COMMAND_PATTERN = re.compile(r'^ping$')

    async def process(self, match: re.Match, payload: dict[str, Any]) -> type[bool, Any]:
        return True, {
            'ping': 'pong',
            'master': self.salt_master,
            'master_': salt.grains.core.hostname(),
            'timestamp': datetime.datetime.now().timestamp()
        }


class PingForMasterHandler(PingHandler):
    """
    Example:
    {"command": "ping/SALT_MASTER", "message_id": "MESSAGE_ID"}
    """
    COMMAND_PATTERN = re.compile(r'^ping/(?P<master>.+)$')
    check_master = True
