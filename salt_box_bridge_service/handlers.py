import abc
import datetime
import logging
import re
from typing import Any

import salt.client  # type:ignore
import salt.config  # type:ignore
import salt.exceptions  # type:ignore
import salt.grains.core  # type:ignore

from salt_box_bridge_service.exceptions import CreateJobError
from salt_box_bridge_service.utils import JobCreator

LOGGER = logging.getLogger(__name__)


class MessageHandlerBase(abc.ABC):
    check_master: bool = False

    def __init__(
        self,
        job_creator: JobCreator,
        salt_master: str,
        channel: str,  # TODO Redundant?
        channel_returns: str  # TODO Redundant?
    ) -> None:
        self.job_creator = job_creator
        self.channel: str = channel
        self.channel_returns: str = channel_returns
        self.salt_master: str = salt_master

    @property
    @abc.abstractmethod
    def COMMAND_PATTERN(self) -> re.Pattern[str]: ...

    async def handle(self, command: str, payload: dict[str, Any]) -> tuple[bool, Any]:
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
    async def process(self, match: re.Match, payload: dict[str, Any]) -> tuple[bool, Any]:
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

    async def process(self, match: re.Match, payload: dict[str, Any]) -> tuple[bool, Any]:
        hash_name: str = payload['hash_name']

        try:
            jid = await self.job_creator.create_job_from_redis(
                hash_name=hash_name,
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

    async def process(self, match: re.Match, payload: dict[str, Any]) -> tuple[bool, Any]:
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
