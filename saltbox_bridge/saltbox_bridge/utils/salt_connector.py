from __future__ import annotations

import json
import logging
from typing import Any, cast

from redis.asyncio import Redis
from salt.client import LocalClient  # type: ignore
from salt.exceptions import SaltException  # type: ignore
from saltbox_bridge_messages import SaltTgtType

from saltbox_bridge.exceptions import CreateJobError

LOGGER = logging.getLogger(__name__)


class SaltConnector:
    def __init__(self, salt_opts: dict, redis_client: Redis) -> None:
        self.salt_opts = salt_opts
        self.redis_client = redis_client

    @property
    def salt_client(self) -> LocalClient:
        # Common case is to recreate the LocalClient before use. Keeping it leads to errors.
        # mopts takes preloaded master options to avoid re-reading configs.
        return LocalClient(c_path=None, mopts=self.salt_opts, auto_reconnect=True)

    async def create_job_from_redis(self, hash_name: str) -> str:
        job_data: dict[bytes, bytes] = await self.redis_client.hgetall(hash_name)

        jid: str = job_data[b'jid'].decode()
        tgt: str = job_data[b'tgt'].decode()
        tgt_type: SaltTgtType = cast(SaltTgtType, job_data[b'tgt_type'].decode())  # FIXME (a.karmanov): Do not cast  # noqa: TD001 E501
        fun: str = job_data[b'fun'].decode()
        arg: list = json.loads(job_data[b'arg']) if b'arg' in job_data else []
        kwarg: dict = json.loads(job_data[b'kwarg']) if b'kwarg' in job_data else {}
        status: str | None = job_data[b'status'].decode() if b'status' in job_data else None

        if status == 'processed':
            return jid

        try:
            back_jid: str = self.salt_client.cmd_async(
                tgt=tgt, tgt_type=tgt_type, fun=fun, arg=arg, kwarg=kwarg, jid=jid
            )
        except SaltException as err:
            LOGGER.exception(str(err))
            raise CreateJobError(str(err)) from err

        await self.redis_client.hset(hash_name, 'status', 'processed')
        await self.redis_client.expire(hash_name, 600)

        return back_jid

    async def create_all_jobs_from_redis(self) -> list[str]:
        hash_names = await self.redis_client.keys('job_create:*')
        jobs_jid: list[str] = []

        for hash_name in hash_names:
            try:
                jobs_jid.append(await self.create_job_from_redis(hash_name))
            except CreateJobError:
                continue

        return jobs_jid

    async def run_job_sync(
        self, tgt: str, tgt_type: SaltTgtType, fun: str, arg: list, kwarg: dict, jid: str | None
    ) -> dict[str, dict] | Any:
        return self.salt_client.cmd(
            tgt=tgt, tgt_type=tgt_type, fun=fun, arg=arg, kwarg=kwarg, jid=jid, full_return=True
        )

    async def gather_minions(self, tgt: str, tgt_type: SaltTgtType) -> Any | list[str]:
        return self.salt_client.gather_minions(tgt, tgt_type)

    async def update_pillar_cache(self, tgt: str, tgt_type: SaltTgtType) -> dict[str, dict] | Any:
        return self.salt_client.cmd(tgt=tgt, tgt_type=tgt_type, fun='saltutil.refresh_pillar')
