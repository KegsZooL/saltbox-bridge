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

import asyncio
import logging
import re

from datetime import datetime, timezone
from typing import Optional, Union

import redis.asyncio as redis

from salt.exceptions import SaltRunnerError, SaltMasterError  # type: ignore
from salt.utils.event import get_master_event  # type: ignore
from salt.utils import json  # type: ignore

LOGGER = logging.getLogger(__name__)
__opts__: dict
__salt__: dict


def __virtual__() -> Union[bool, tuple[bool, str]]:
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


class RedisPusher:
    def __init__(self, host: str, port: int, db: int) -> None:
        self.redis = redis.Redis(host=host, port=port, db=db)

    async def process(self, event: Optional[dict]) -> None:
        # TODO Make separate tag handlers
        if not event:
            return

        tag_new = re.compile(r'salt/job/(?P<jid>[\d]{20})/new')
        tag_ret = re.compile(r'salt/job/(?P<jid>[\d]{20})/ret/(?P<mid>.+)')

        tag = event['tag']
        body = json.dumps(event['data'])

        LOGGER.debug('%s got event with tag "%s"', __name__, tag)

        if match := tag_new.match(tag):
            # Mention: on salt-call call there is no salt/job/*/new event
            # (but on salt/job/*/ret/* it is)
            jid = match.group('jid')
            LOGGER.info('New job: %s', jid)
            async with self.redis.pipeline(transaction=True) as pipe:
                await pipe\
                    .zadd(name='jobs', mapping={body: jid_to_epoch(jid)})\
                    .execute()
            # _stamp keyword will not be in websocket message
            await self.redis.publish(channel=f'job:{jid}', message=body)
            return

        elif match := tag_ret.match(tag):
            jid = match.group('jid')
            mid = match.group('mid')
            LOGGER.info('New job return: %s: %s', jid, mid)

            await self.redis.hset(name=f'job.rets:{jid}', key=mid, value=body)
            await self.redis.publish(channel=f'job.rets:{jid}', message=body)
            return


async def _async_start(host: str, port: int, db: int, expire) -> None:
    sock_dir = __opts__['sock_dir']
    pusher = RedisPusher(host=host, port=port, db=db)

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
