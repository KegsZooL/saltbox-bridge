from __future__ import annotations

import logging
from typing import Annotated

from faststream import Context
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage

from saltbox_bridge.event_bus.subscribers import system_subscribers
from saltbox_bridge.event_bus.subscribers.minion_subscribers import router as minion_router
from saltbox_bridge.event_bus.subscribers.minion_subscribers import router_not_auth as minion_router_not_auth
from saltbox_bridge.event_bus.subscribers.pillar_subscribers import router as pillar_router
from saltbox_bridge.event_bus.subscribers.pillar_subscribers import router_not_auth as pillar_router_not_auth

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]


router = RedisRouter(prefix='master_')

router.include_routers(
    minion_router,
    minion_router_not_auth,
    pillar_router,
    pillar_router_not_auth,
    system_subscribers.router,
    system_subscribers.router_not_auth,
)
