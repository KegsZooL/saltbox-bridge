from __future__ import annotations

import logging
from typing import Annotated

from faststream import Context, Logger
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage
from saltbox_bridge_messages import (
    BridgeNewJobResponce,
    CoreNewJobAsyncRequest,
    CoreNewJobRequest,
    JobReturnSchema,
)

from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.exceptions import CreateJobError
from saltbox_bridge.utils.salt_connector import SaltConnector

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]


router = RedisRouter(middlewares=[MastersAuthMiddleware])
router_not_auth = RedisRouter()


@router.subscriber('run_job')
async def run_job(
    message: CoreNewJobAsyncRequest,
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
    message: CoreNewJobRequest,
    logger: Logger,
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> BridgeNewJobResponce | None:
    try:
        job_result: dict = await salt_connector.run_job_sync(
            tgt=message.tgt,
            tgt_type=message.tgt_type,
            fun=message.fun,
            arg=message.arg,
            kwarg=message.kwarg,
            jid=message.jid,
        )

        # TODO: check this part
        job_result_val: dict = next(iter(job_result.values()), {})
        jid: str = job_result_val.get('jid', '')

        result = BridgeNewJobResponce(
            **message.model_dump(exclude={'jid'}),
            jid=jid,
            returns={minion_id: JobReturnSchema(**job_return) for minion_id, job_return in job_result.items()},
        )

        logger.info('Created job: %s', result)
        return result
    except CreateJobError as error:
        logger.error(error)
        return None
