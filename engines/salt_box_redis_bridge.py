"""
Salt master config:

    module_dirs:
      - /srv/salt_extmod/  # Custom modules' dir for the master
                           # better not to mix with /srv/salt/

    engines:
      - salt_box_redis_bridge:  # start() args following
          host: localhost  # Redis instance

Put the module to /srv/salt_extmod/engines/

Restart salt-master. Log and exceptions will be in salt-master log.
"""
from __future__ import annotations

import abc
import asyncio
import logging
import re

from datetime import datetime, timezone
from typing import Any, Literal

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
        raise SaltMasterError('Unexpected JID format: %s' % jid)

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


class MessageHandlerBase(abc.ABC):
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis_client = redis_client

    @property
    @abc.abstractmethod
    def TAG_PATTERN(self) -> re.Pattern[str]: ...

    async def handle(self, tag: str, data: dict[str, Any]) -> None:
        """
        If tag matches TAG_PATTERN, process message

        :raises: StopProcessing when no need to process the message with other handlers
        """
        if match := self.TAG_PATTERN.match(tag):
            return await self.process(match, data)

    @abc.abstractmethod
    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        """ Take action on message """


class MessageHandlerJobNew(MessageHandlerBase):
    TAG_PATTERN = re.compile(r'salt/job/(?P<jid>\d{20})/new')
    # Mention: on salt-call call there is no salt/job/*/new event
    # (but salt/job/*/ret/* it is)

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        data_json = json.dumps(data)
        LOGGER.info('New job: %s', jid)

        await self._process_job(jid=jid, data_json=data_json)

        raise StopProcessing()

    async def _process_job(self, jid: str, data_json: str) -> None:
        await self.redis_client.zadd(name='jobs', mapping={data_json: jid_to_epoch(jid)})
        await self.redis_client.publish(channel=f'job:{jid}:new', message=data_json)

class MessageHandlerJobNewForTask(MessageHandlerJobNew):
    TAG_PATTERN = re.compile(r'salt/job/(?P<jid>\d{20})-t(?P<tid>[a-zA-Z0-9]{24})/new')

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        tid = match.group('tid')

        data['jid'] = jid
        data_json = json.dumps(data)

        LOGGER.info('New job (jid: %s) for task: %s', jid, tid)

        await self._process_job(jid=jid, data_json=data_json)
        await self._process_task(jid=jid, tid=tid, data_json=data_json)

        raise StopProcessing()

    async def _process_task(self, jid: str, tid: str, data_json: str) -> None:
        await self.redis_client.publish(channel=f'task:{tid}:job:{jid}:new', message=data_json)


class MessageHandlerJobReturn(MessageHandlerBase):
    TAG_PATTERN = re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)')

    def __init__(self, redis_client: redis.Redis, expire: int | None) -> None:
        self.expire = expire
        super().__init__(redis_client)

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        mid = match.group('mid')
        function = data['fun']
        data_json = json.dumps(data)

        LOGGER.info('Job %s return for %s, function %s', jid, mid, function)

        await self._process_return(jid=jid, mid=mid, function=function, data=data, data_json=data_json)

        raise StopProcessing()

    async def _process_return(self, jid: str, mid: str, function: str, data: dict, data_json: str):
        hash_name = f'job:{jid}:return'

        async with self.redis_client.pipeline(transaction=True) as pipe:
            pipe = pipe.hset(name=hash_name, key=mid, value=data_json)
            if self.expire is not None:
                pipe = pipe.expire(name=hash_name, time=self.expire)
            await pipe.execute()

        await self.redis_client.publish(channel=hash_name, message=data_json)

        if function == 'grains.items':
            await self._process_grains(mid, data['return'])

    async def _process_grains(self, mid: str, grains: dict[str, Any]) -> None:
        LOGGER.debug('Processing grains for %s', mid)
        if not grains:
            return

        mapping = {k: json.dumps(val) for k, val in grains.items()}

        hash_name = f'minion:{mid}:grains'
        async with self.redis_client.pipeline(transaction=True) as pipe:
            pipe = pipe.hset(name=hash_name, mapping=mapping)  # type: ignore
            if self.expire is not None:
                pipe = pipe.expire(name=hash_name, time=self.expire)
            await pipe.execute()
        dumped_grains = json.dumps(grains)
        await self.redis_client.publish(channel=hash_name, message=dumped_grains)
        await self.redis_client.publish(channel='grains', message=dumped_grains)


class MessageHandlerJobReturnForTask(MessageHandlerJobReturn):
    TAG_PATTERN = re.compile(r'salt/job/(?P<jid>\d{20})-t(?P<tid>[a-zA-Z0-9]{24})/ret/(?P<mid>.+)')

    async def _process_task(self, jid, tid, data_json):
        await self.redis_client.publish(channel=f'task:{tid}:job:{jid}:return', message=data_json)


    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        tid = match.group('tid')
        mid = match.group('mid')


        data['jid'] = jid
        function = data['fun']
        data_json = json.dumps(data)

        LOGGER.info('Job %s (task %s) return for %s, function %s', jid, tid, mid, function)

        await self._process_return(jid=jid, mid=mid, function=function, data=data, data_json=data_json)
        await self._process_task(jid=jid, tid=tid, data_json=data_json)

        raise StopProcessing()



class RedisPusher:
    def __init__(
        self,
        redis_client: redis.Redis,
        expire: int | None = None
    ) -> None:
        self.handlers = [
            MessageHandlerJobNew(redis_client),
            MessageHandlerJobNewForTask(redis_client),
            MessageHandlerJobReturn(redis_client, expire=expire),
            MessageHandlerJobReturnForTask(redis_client, expire=expire),
        ]

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


async def _async_start(redis_client: redis.Redis, expire: int | None) -> None:
    sock_dir = __opts__['sock_dir']
    pusher = RedisPusher(redis_client, expire)

    with get_master_event(__opts__, sock_dir, listen=True) as event_bus:
        while True:
            await pusher.process(event_bus.get_event(full=True))


def start(
    redis_host: str = 'localhost',
    port: int = 6379,
    username: str | None = None,
    password: str | None = None,
    db: int = 0,
    ssl=False,
    ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required',
    ssl_ca_certs: str | None = None,
    expire: int | None = None,
) -> None:
    """
    redis_host
        Redis client connection host

    port
        Redis client connection port

    username
        Redis client allowed username

    password
        Redis client user password

    db
        Redis client database index

    ssl
        Redis client TLS encryption flag

    ssl_cert_reqs
        Redis client validation policy

    ssl_ca_certs
        Redis client path to server root certs concatenated file

    expire
        Time of records live in seconds
    """

    redis_client = redis.Redis(
        host=redis_host,
        port=port,
        db=db,
        username=username,
        password=password,
        ssl=ssl,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
    )
    coro = _async_start(redis_client, expire=expire)
    asyncio.run(coro)
