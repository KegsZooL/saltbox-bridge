from __future__ import annotations

import abc
import asyncio
import logging
from datetime import timedelta
from typing import Any, ClassVar

from salt.config import master_config  # type: ignore[import-untyped]
from salt.utils.event import MasterEvent, get_master_event  # type: ignore[import-untyped]

from saltbox_bridge.utils.system import utc_now

logger = logging.getLogger(__name__)

MASTER_CONF_PATH = '/etc/salt/master'


class SaltBusMessage(abc.ABC):
    @abc.abstractmethod
    def get_tag(self) -> str: ...
    @abc.abstractmethod
    def get_data(self) -> dict[str, Any]: ...


class FakeJobNewBusMessage(SaltBusMessage):
    LATEST_JID_TIME = utc_now()
    DEFAULT_MINIONS: ClassVar = ['fake!_minion']

    def __init__(self, fun: str = 'test.ping', minions: list[str] | None = None) -> None:
        self.minions = minions if minions is not None else self.DEFAULT_MINIONS
        self.jid = self._gen_jid()
        self.fun = fun

    def get_tag(self) -> str:
        return f'salt/job/{self.jid}/new'

    def get_data(self) -> dict[str, Any]:
        return {
            'arg': [],
            'fun': self.fun,
            'jid': self.jid,
            'minions': self.minions,
            'missing': [],
            'tgt': self.minions,
            'tgt_type': 'list',
            'user': 'root'
        }

    def _gen_jid(self) -> str:
        jid_dt = utc_now()
        if jid_dt <= self.LATEST_JID_TIME:
            jid_dt = self.LATEST_JID_TIME + timedelta(microseconds=1)
        self.LATEST_JID_TIME = jid_dt
        return f'{jid_dt:%Y%m%d%H%M%S%f}'


def get_event_obj() -> MasterEvent:
    opts = master_config(MASTER_CONF_PATH)
    return get_master_event(opts, sock_dir=opts['sock_dir'], listen=False)


class FakeJobNewEventGenerator:
    BASE_CHUNK_SIZE = 100
    THRESHOLD = 0.1  # TODO (a.karmanov) US363 :  Implement time lag threshold
    lock = asyncio.Lock()

    async def fire(self, duration: timedelta, rate: int) -> None:
        """
        Generate fake `job/{jid}/new` messages

        :param duration: how long to send fake messages
        :param rate: target messages per second rate
        """
        async with self.lock:
            return await self._fire(duration=duration, rate=rate)

    async def _fire(self, duration: timedelta, rate: int) -> None:
        event = get_event_obj()
        start_time = utc_now()
        end_time = start_time + duration
        counter = 0
        chunk_size = self.BASE_CHUNK_SIZE if self.BASE_CHUNK_SIZE < rate else rate
        chunk_rate = rate / chunk_size
        relax_time = 1 / chunk_rate

        while utc_now() < end_time:
            for _ in range(chunk_size):
                data = FakeJobNewBusMessage()
                event.fire_event(data=data.get_data(), tag=data.get_tag())
                counter += 1
            await asyncio.sleep(relax_time)
