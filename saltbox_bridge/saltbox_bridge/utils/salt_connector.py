from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from redis.asyncio import Redis
from salt.channel.client import ReqChannel  # type: ignore
from salt.client import LocalClient  # type: ignore
from salt.utils.args import condition_input  # type: ignore
from saltbox_bridge_messages import SaltTgtType

LOGGER = logging.getLogger(__name__)


class SaltConnector:
    def __init__(self, salt_opts: dict, redis_client: Redis) -> None:
        self.salt_opts = salt_opts
        self.redis_client = redis_client

        with Path(self.salt_opts['cachedir']).joinpath('.root_key').open('r') as key_f:
            self.key = key_f.read()

        self.channel = ReqChannel.factory(self.salt_opts, crypt='clear', master_uri='tcp://localhost:4506')

    def create_job_by_zeromq(
        self, jid: str, tgt: str, tgt_type: SaltTgtType, fun: str, fun_args: list, fun_kwargs: dict
    ) -> str:
        load: dict[str, str | list | dict] = {
            'cmd': 'publish',
            'user': 'root',
            'key': self.key,
            'fun': fun,
            'tgt': tgt,
            'tgt_type': tgt_type,
            'arg': condition_input(fun_args, fun_kwargs),
            'ret': '',
            'jid': jid,
            'load': {},
        }

        ret = self.channel.send(load, timeout=60).get('load', {})
        ret_jid: str = ret.get('jid', '')

        return ret_jid

    @property
    def salt_client(self) -> LocalClient:
        # Common case is to recreate the LocalClient before use. Keeping it leads to errors.
        # mopts takes preloaded master options to avoid re-reading configs.
        return LocalClient(c_path=None, mopts=self.salt_opts, auto_reconnect=True)

    async def gather_minions(self, tgt: str, tgt_type: SaltTgtType) -> Any | list[str]:

        if tgt_type != 'pillar':
            return self.salt_client.gather_minions(tgt, tgt_type)

        key, sep, expected = tgt.partition(':')
        if not sep:
            return []

        minions = self.salt_client.cmd('*', 'pillar.get', [key])

        def matches(value: object) -> bool:
            if isinstance(value, (list, tuple, set)):
                return expected in value
            if isinstance(value, dict):
                return expected in value or expected in value.values()
            return str(value) == expected

        return [mid for mid, value in minions.items() if matches(value)]

    async def update_pillar_cache(self, tgt: str, tgt_type: SaltTgtType) -> dict[str, dict] | Any:
        return self.salt_client.cmd(tgt=tgt, tgt_type=tgt_type, fun='saltutil.refresh_pillar')
