from __future__ import annotations

import logging

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from faststream import BaseMiddleware, Context, Logger
from faststream.broker.message import StreamMessage
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage
from faststream.utils.context.repository import context

from saltbox_bridge.config import SETTINGS
from saltbox_bridge.exceptions import CreateJobError
from saltbox_bridge.schemas.base_schemas import BaseInAbstractMessage
from saltbox_bridge.schemas.in_schemas import (
    GatherMinionsInMessage,
    ListSlsReposMessage,
    NewJobIneMessage,
    NewJobSyncIneMessage,
    UpdatePillarCacheInMessage,
)
from saltbox_bridge.schemas.out_schemas import GatherMinionsOutMessage, JobReturn, JobSyncOutMessage, Minion
from saltbox_bridge.utils.salt_connector import SaltConnector, get_salt_caller, get_state_apply_error

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]


class MastersAuthMiddleware(BaseMiddleware):
    async def consume_scope(self, call_next: Callable[[Any], Awaitable[Any]], msg: StreamMessage[Any]) -> Any:
        message: BaseInAbstractMessage = BaseInAbstractMessage(**await msg.decode())  # type: ignore

        salt_master: str = context.get('salt_master')

        if message.master and message.master != salt_master:
            return None

        if message.check_checksum():
            return await super().consume_scope(call_next, msg)
        else:
            LOGGER.error('Checksum failed')
            return None


router = RedisRouter(prefix='master_', middlewares=[MastersAuthMiddleware])


@router.subscriber('run_job')
async def run_job(
    message: NewJobIneMessage,
    logger: Logger,
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> str | None:
    try:
        jid: str = await salt_connector.create_job_from_redis(
            hash_name=message.hash_name,
        )
        logger.info('Created job: %s', jid)
        return jid
    except CreateJobError as error:
        logger.error(error)
        return None


@router.subscriber('run_job_sync')
async def run_job_sync(
    message: NewJobSyncIneMessage,
    logger: Logger,
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> JobSyncOutMessage | None:
    try:
        job_result: dict = await salt_connector.run_job_sync(
            tgt=message.tgt,
            tgt_type=message.tgt_type,
            fun=message.fun,
            arg=message.arg,
            kwarg=message.kwarg,
            jid=message.jid,
        )

        jid: str = next(iter(job_result.values()), {}).get('jid', '')

        result = JobSyncOutMessage(
            **message.model_dump(exclude={'jid'}),
            jid=jid,
            returns={minion_id: JobReturn(**job_return) for minion_id, job_return in job_result.items()},
        )
        result.fill_checksum()

        logger.info('Created job: %s', result)
        return result
    except CreateJobError as error:
        logger.error(error)
        return None


@router.subscriber('gather_minions')
async def gather_minions(
    message: GatherMinionsInMessage,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> GatherMinionsOutMessage:
    minions: list[str] = await salt_connector.gather_minions(tgt=message.tgt, tgt_type=message.tgt_type)

    result = GatherMinionsOutMessage(
        count=len(minions),
        minions=[
            Minion(minion_id=minion, master=salt_master) for minion in minions[: SETTINGS.max_count_of_gather_minions]
        ],
        master=salt_master,
    )
    result.fill_checksum()

    return result


@router.subscriber('update_pillar_cache')
async def update_pillar_cache(
    message: UpdatePillarCacheInMessage,
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> Any:
    return await salt_connector.update_pillar_cache(tgt=message.tgt, tgt_type=message.tgt_type)


@router.subscriber('sync_repos')
async def sync_repos(
    message: ListSlsReposMessage,
    salt_connector: SaltConnector = Context(),
) -> Any:
    # TODO True async?
    # TODO lock file
    # TODO Notify Salt.Box Core

    LOGGER.info('Start sync_repos')
    caller = get_salt_caller()
    repos = [r.dict() for r in message.repos]
    pillar = {
        'gitfs_repos': repos,
        'var_dir': str(SETTINGS.var_dir),
        'sshfs_server': SETTINGS.gitfs_server,
        'sshfs_port': SETTINGS.gitfs_port,
        'gitfs_privkey': str(SETTINGS.gitfs_privkey),
        'gitfs_pubkey': str(SETTINGS.gitfs_pubkey),
        'saltbox_env': 'saltbox',
    }
    ret = caller.cmd('state.apply', 'sync_repos', pillar=pillar)
    LOGGER.info('End sync_repos')
    if (errors := get_state_apply_error(ret)) is not None:
        for msg in errors:
            LOGGER.error(msg)
