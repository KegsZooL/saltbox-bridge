from __future__ import annotations

import logging
from typing import Annotated

from faststream import Context
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage
from saltbox_bridge_messages import CoreNewJobAsyncRequest

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
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> None:
    try:
        jid: str = await salt_connector.create_job_from_redis(
            hash_name=message.hash_name,
        )
        LOGGER.debug('Created job: %s', jid)
    except CreateJobError as error:
        LOGGER.error(error)

    return None
