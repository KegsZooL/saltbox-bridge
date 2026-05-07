from __future__ import annotations

import logging
from typing import Annotated

from faststream import Context
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage
from saltbox_bridge_messages import CoreMessageBase, SaltKeysRequest, SaltKeysResponse

from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.utils.salt_connector import SaltConnector

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]


router = RedisRouter(middlewares=[MastersAuthMiddleware])
router_not_auth = RedisRouter()


@router.subscriber('accept_keys')
async def accept_keys(
    message: SaltKeysRequest,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> SaltKeysResponse:
    minions: list[str] = await salt_connector.salt_key_accept(minions_ids=message.minions)

    result = SaltKeysResponse(
        minions=minions,
        master=salt_master,
    )

    return result


@router.subscriber('accept_all_keys')
async def accept_all_keys(
    message: CoreMessageBase,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> SaltKeysResponse:
    minions: list[str] = await salt_connector.salt_key_all_accept()

    result = SaltKeysResponse(
        minions=minions,
        master=salt_master,
    )

    return result


@router.subscriber('reject_keys')
async def reject_keys(
    message: SaltKeysRequest,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> SaltKeysResponse:
    minions: list[str] = await salt_connector.salt_key_reject(minions_ids=message.minions)

    result = SaltKeysResponse(
        minions=minions,
        master=salt_master,
    )

    return result


@router.subscriber('reject_all_keys')
async def reject_all_keys(
    message: CoreMessageBase,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> SaltKeysResponse:
    minions: list[str] = await salt_connector.salt_key_all_reject()

    result = SaltKeysResponse(
        minions=minions,
        master=salt_master,
    )

    return result


@router.subscriber('delete_keys')
async def delete_keys(
    message: SaltKeysRequest,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> SaltKeysResponse:
    minions: list[str] = await salt_connector.salt_key_delete(minions_ids=message.minions)

    result = SaltKeysResponse(
        minions=minions,
        master=salt_master,
    )

    return result


@router.subscriber('delete_all_keys')
async def delete_all_keys(
    message: CoreMessageBase,
    salt_master: str = Context(),
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> SaltKeysResponse:
    minions: list[str] = await salt_connector.salt_key_all_delete()

    result = SaltKeysResponse(
        minions=minions,
        master=salt_master,
    )

    return result
