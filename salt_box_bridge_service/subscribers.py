from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from faststream import BaseMiddleware, Context, Logger
from faststream.broker.message import StreamMessage
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage
from faststream.utils.context.repository import context
from redis.asyncio import Redis

from salt_box_bridge_service.exceptions import CreateJobError
from salt_box_bridge_service.schemas.base_schemas import BaseInAbstractMessage
from salt_box_bridge_service.schemas.in_schemas import GatherMinionsInMessage, NewJobIneMessage
from salt_box_bridge_service.utils.salt_connector import SaltConnector

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]


class MastersAuthMiddleware(BaseMiddleware):
    async def consume_scope(self, call_next: Callable[[Any], Awaitable[Any]], msg: StreamMessage[Any]) -> Any:
        message: BaseInAbstractMessage = BaseInAbstractMessage(**await msg.decode())  # type: ignore

        secret: str = context.get('master_secret')
        salt_master: str = context.get('salt_master')

        if message.master and message.master != salt_master:
            return

        if message.check_checksum(secret):
            await super().consume_scope(call_next, msg)
        else:
            LOGGER.error('Checksum failed')


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


@router.subscriber('gather_minions')
async def gather_minions(
    message: GatherMinionsInMessage,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
    redis_client: Redis = Context(),  # noqa: B008
) -> str | None:
    minions: list[str] = await salt_connector.gather_minions(tgt=message.tgt, tgt_type=message.tgt_type)
    key: str = f'{salt_master}__{message.tgt}__{message.tgt_type}'

    result: dict = {
        'count': len(minions),
        'minions': [{'minion_id': minion, 'master': salt_master} for minion in minions[:100]],
    }

    await redis_client.hset(name='minions-cache', key=key, value=json.dumps(result))
    await redis_client.hpexpire('minions-cache', 15 * 1000, key)
