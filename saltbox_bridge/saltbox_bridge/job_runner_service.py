from __future__ import annotations

import asyncio
import logging

import salt.config  # type: ignore[import-untyped]
from salt.exceptions import SaltException  # type: ignore

from saltbox_bridge.config import SETTINGS, configure_logging
from saltbox_bridge.redis import get_redis_client
from saltbox_bridge.utils.core_connector import CoreConnector
from saltbox_bridge.utils.salt_connector import SaltConnector

LOGGER = logging.getLogger(__name__)


class JobRunner:
    JOBS_TO_CREATE_SET_NAME = 'jobs:to_create'

    def __init__(
        self,
        salt_opts: dict,
    ) -> None:
        self.redis_client = get_redis_client()
        self.salt_opts = salt_opts
        self.master_id: str = self.salt_opts['salt_box_master_id']
        self.core_connector = CoreConnector(master_id=self.master_id, redis_client=self.redis_client)
        self.salt_connector = SaltConnector(salt_opts=salt_opts, redis_client=self.redis_client)

    async def start(self) -> None:
        await self.core_connector.wait_success_connection()

        while True:
            jids: list[bytes] = await self.redis_client.spop(self.JOBS_TO_CREATE_SET_NAME, SETTINGS.runner_batch_size)  # type: ignore
            for jid in jids:
                await self.process(jid)
            await asyncio.sleep(SETTINGS.runner_sleep_timeout)

    async def process(self, jid: bytes) -> None:
        if not jid:
            return

        job = await self.core_connector.get_job(jid.decode())
        if not job:
            return

        LOGGER.debug('Processing job: %s', job)

        try:
            self.salt_connector.create_job_by_zeromq(
                jid=job['jid'],
                tgt=job['tgt'],
                tgt_type=job['tgt_type'],
                fun=job['fun'],
                fun_args=job.get('arg', []) or [],
                fun_kwargs=job.get('kwarg', {}) or {},
            )
            await self.core_connector.update_or_create_job(jid=job['jid'], data={'status': 'running'}, job=job)
        except SaltException as err:
            LOGGER.exception(str(err))
            await self.redis_client.sadd(self.JOBS_TO_CREATE_SET_NAME, jid)


async def _async_start(salt_opts: dict | None) -> None:
    if salt_opts is None:
        salt_opts = salt.config.client_config('/etc/salt/master')
    configure_logging(format=f'{salt_opts["log_fmt_console"]} (Bridge Job Runner)')
    job_runner = JobRunner(salt_opts=salt_opts)
    await job_runner.start()


def start(salt_opts: dict | None = None) -> None:
    coro = _async_start(salt_opts=salt_opts)
    asyncio.run(coro)
