from __future__ import annotations

from typing import Annotated

from faststream import Context
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage
from saltbox_bridge_messages import (
    BridgeTestBurstLoadMessage,
    BridgeTestBurstResponse,
    CoreEmptyMessage,
    CoreTestBurstRequest,
)

from saltbox_bridge.event_bus.core_connector import CoreConnector
from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.utils.salt_caller import sync_saltbox
from saltbox_bridge.utils.system import get_random_string, utc_now

Message = Annotated[RedisMessage, Context()]

router = RedisRouter(middlewares=[MastersAuthMiddleware])
router_not_auth = RedisRouter()


@router.subscriber('sync_repos')
def sync_repos(message: CoreEmptyMessage) -> None:
    # TODO (a.karmanov): True async?
    # TODO (a.karmanov): lock file
    # TODO (a.karmanov): Notify Salt.Box Core
    sync_saltbox()


@router.subscriber('burst_test')
async def burst_test(
    message: CoreTestBurstRequest,
    core_connector: CoreConnector = Context(),  # noqa: B008
) -> BridgeTestBurstResponse:
    load = get_random_string(message.size)
    start = utc_now()
    for _ in range(message.count):
        load_msg = BridgeTestBurstLoadMessage(master=message.master, load=load)
        await core_connector.send_messagee(message=load_msg, message_tag='burst_test_load')
    duration = utc_now() - start
    return BridgeTestBurstResponse(master=message.master, time=duration)
