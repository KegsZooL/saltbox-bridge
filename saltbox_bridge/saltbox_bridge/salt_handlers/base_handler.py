from __future__ import annotations

import abc
import json
import re
from typing import Any, cast

import redis.asyncio as redis
from faststream.redis import RedisBroker
from salt.client import LocalClient  # type: ignore
from saltbox_bridge_messages import BridgeMessageBase

from saltbox_bridge.config import SETTINGS

MessageDataType = dict[str, Any]


class BaseMessageHandler(abc.ABC):
    """
    A base class for handling salt.box messages

    Attributes:
        redis_client: Redis client
        salt_opts: Salt options
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        broker: RedisBroker,
        salt_opts: dict,
    ) -> None:
        self.redis_client = redis_client
        self.broker = broker
        self.salt_opts = salt_opts

    METRIC_TAG: str | None = None

    @property
    def salt_client(self) -> LocalClient:
        return LocalClient(c_path=None, mopts=self.salt_opts, auto_reconnect=True)

    @property
    def master_id(self) -> str:
        return cast(str, self.salt_opts['salt_box_master_id'])

    async def send_message(self, message: BridgeMessageBase, message_tag: str) -> None:
        async with self.broker as br:
            await br.publish(message=message, channel=f'master_{message_tag}')

    @property
    @abc.abstractmethod
    def tag_pattern(self) -> re.Pattern[str]: ...

    async def normalize_data(self, match: re.Match, tag: str, data: MessageDataType) -> MessageDataType:
        return data

    async def handle(self, tag: str, data: MessageDataType) -> None:
        """
        If tag matches tag_pattern, process message

        Args:
            tag: salt message tag
            data: salt message data

        Raises:
            StopProcessing: when no need to process the message with other handlers
        """
        if match := self.tag_pattern.match(tag):
            data = await self.normalize_data(match=match, tag=tag, data=data)

            if self.can_process_metrics():
                await self.process_metrics(match=match, tag=tag, data=data)

            return await self.process(match, data)

        return None

    def can_process_metrics(self) -> bool:
        if SETTINGS.is_metric_enabled and self.METRIC_TAG:
            return True

        return False

    async def _prepare_metrics_data(self, match: re.Match, tag: str, data: MessageDataType) -> dict:
        """
        Prepare metrics data

        Args:
            match: matched salt message tag
            tag: salt message tag
            data: salt message data
        """

        return {
            'master_id': self.master_id,
        }

    async def process_metrics(self, match: re.Match, tag: str, data: MessageDataType) -> None:
        """
        Process metrics

        Args:
            match: matched salt message tag
            tag: salt message tag
            data: salt message data
        """

        if not self.METRIC_TAG:
            return

        await self.redis_client.publish(
            channel=self.METRIC_TAG, message=json.dumps(await self._prepare_metrics_data(match, tag, data))
        )

    @abc.abstractmethod
    async def process(self, match: re.Match, data: MessageDataType) -> None:
        """
        Take action on message

        Args:
            match: matched salt message tag
            data: salt message data

        Raises:
            StopProcessing: when no need to process the message with other handlers
        """
