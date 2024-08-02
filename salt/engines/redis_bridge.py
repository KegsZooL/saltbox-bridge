"""
Salt master config:

    module_dirs:
      - /srv/salt_extmod/  # Custom modules' dir for the master
                           # better not to mix with /srv/salt/

    engines:
      - redis_bridge:  # start() args following
          host: localhost  # Redis insance

Put the module to /srv/salt_extmod/engines/redis_bridge.py

Restart salt-master. Log and exceptions will be in salt-master log.
"""
from __future__ import annotations

import abc
import asyncio
import logging
import re

from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis

from salt.exceptions import SaltRunnerError, SaltMasterError  # type: ignore
from salt.utils.event import get_master_event  # type: ignore
from salt.utils import json  # type: ignore

LOGGER = logging.getLogger(__name__)
__opts__: dict
__salt__: dict


def __virtual__() -> bool | tuple[bool, str]:
    if __opts__['__role'] != 'master':
        return False, f'{__name__} runs on master only'
    return True


JID_REGEX = (
    r'^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})'
    r'(?P<minute>\d{2})(?P<second>\d{2})(?P<microsecond>\d{6})$'
)
JID_PATTERN = re.compile(JID_REGEX)


def jid_to_epoch(jid: str) -> float:
    if not (match := JID_PATTERN.match(jid)):
        raise SaltMasterError('Unexpected JID format: %s', jid)

    kwargs = {k: int(val) for k, val in match.groupdict().items()}

    try:
        dt = datetime(**kwargs, tzinfo=timezone.utc)
    except ValueError as err:
        raise SaltRunnerError(err)

    return dt.timestamp()


class StopProcessing(Exception):
    """
    Raising of StopProcessing is signal a message is no need further processing
    """


class MessageHanlerBase(abc.ABC):
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis_client = redis_client

    @property
    @abc.abstractmethod
    def TAG_PATTERN(self) -> re.Pattern[str]: ...

    async def handle(self, tag: str, body: Any) -> None:
        """
        If tag matches TAG_PATTERN, process message

        :raises: StopProcessing when no need to process the message with other handlers
        """
        if match := self.TAG_PATTERN.match(tag):
            return await self.process(match, body)

    @abc.abstractmethod
    async def process(self, match: re.Match, body: Any) -> None:
        """ Take action on message """


class MessageHandlerNew(MessageHanlerBase):
    TAG_PATTERN = re.compile(r'salt/job/(?P<jid>[\d]{20})/new')

    async def process(self, match: re.Match, body: Any) -> None:
        # Mention: on salt-call call there is no salt/job/*/new event
        # (but salt/job/*/ret/* it is)
        jid = match.group('jid')
        LOGGER.info('New job: %s', jid)
        await self.redis_client.zadd(name='jobs', mapping={body: jid_to_epoch(jid)})
        await self.redis_client.publish(channel=f'job:{jid}', message=body)
        raise StopProcessing()


class MessageHanlerReturn(MessageHanlerBase):
    TAG_PATTERN = re.compile(r'salt/job/(?P<jid>[\d]{20})/ret/(?P<mid>.+)')

    def __init__(self, redis: redis.Redis, expire: int | None) -> None:
        self.expire = expire
        super().__init__(redis)

    async def process(self, match: re.Match, body: Any) -> None:
        jid = match.group('jid')
        mid = match.group('mid')
        LOGGER.info('New job return: %s: %s', jid, mid)

        async with self.redis_client.pipeline(transaction=True) as pipe:
            name = f'job.rets:{jid}'
            pipe = pipe.hset(name=name, key=mid, value=body)
            if self.expire is not None:
                pipe = pipe.expire(name=name, time=self.expire)
            await pipe.execute()
        await self.redis_client.publish(channel=f'job.rets:{jid}', message=body)
        raise StopProcessing()


class MessageHandlerGrainsItems(MessageHanlerBase):
    # TODO
    TAG_PATTERN = re.compile(r'$^')

    # TODO
    async def process(self, match: re.Match, body: Any) -> None:
        ...


class RedisPusher:
    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        expire: int | None = None
    ) -> None:
        redis_client = redis.Redis(host=host, port=port, db=db)
        self.handlers = [
            MessageHandlerNew(redis_client),
            MessageHanlerReturn(redis_client, expire=expire),
            MessageHandlerGrainsItems(redis_client),
        ]

    async def process(self, event: dict | None) -> None:
        if not event:
            return

        tag = event['tag']
        body = json.dumps(event['data'])

        LOGGER.debug('%s got event with tag "%s"', __name__, tag)

        for handler in self.handlers:
            try:
                await handler.handle(tag, body)
            except StopProcessing:
                LOGGER.debug('End message processing')
                return


async def _async_start(host: str, port: int, db: int, expire) -> None:
    sock_dir = __opts__['sock_dir']
    pusher = RedisPusher(host=host, port=port, db=db, expire=expire)

    with get_master_event(__opts__, sock_dir, listen=True) as event_bus:
        while True:
            await pusher.process(event_bus.get_event(full=True))


def start(
    host: str = 'localhost',
    port: int = 6379,
    db: int = 0,
    expire: int | None = None,
) -> None:
    coro = _async_start(host=host, port=port, db=db, expire=expire)
    asyncio.run(coro)
