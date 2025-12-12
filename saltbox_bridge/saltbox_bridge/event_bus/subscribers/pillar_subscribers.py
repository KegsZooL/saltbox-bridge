from __future__ import annotations

import logging
from typing import Annotated, Any

from faststream import Context
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage
from saltbox_bridge_messages import CoreEncryptPillarRequest, CoreEncryptPillarResponse, CoreUpdatePillarCacheRequest

from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.utils.salt_caller import SaltCaller
from saltbox_bridge.utils.salt_connector import SaltConnector

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]


router = RedisRouter(middlewares=[MastersAuthMiddleware])
router_not_auth = RedisRouter()


@router.subscriber('update_pillar_cache')
async def update_pillar_cache(
    message: CoreUpdatePillarCacheRequest,
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> Any:
    return await salt_connector.update_pillar_cache(tgt=message.tgt, tgt_type=message.tgt_type)


@router.subscriber('encrypt_pillar_data')
def encrypt_pillar_data(
    message: CoreEncryptPillarRequest,
    salt_caller: SaltCaller = Context(),  # noqa: B008
) -> CoreEncryptPillarResponse:
    encrypted = salt_caller.encrypt_data(
        text=message.text,
        recipients=['saltbox@example.local'],
    )
    return CoreEncryptPillarResponse(encrypted_text=encrypted, master=message.master)
