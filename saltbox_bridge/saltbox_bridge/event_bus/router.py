from __future__ import annotations

from faststream.redis import RedisRouter

from saltbox_bridge.event_bus.subscribers.minion_subscribers import router as minion_router
from saltbox_bridge.event_bus.subscribers.minion_subscribers import router_not_auth as minion_router_not_auth
from saltbox_bridge.event_bus.subscribers.pillar_subscribers import router as pillar_router
from saltbox_bridge.event_bus.subscribers.pillar_subscribers import router_not_auth as pillar_router_not_auth
from saltbox_bridge.event_bus.subscribers.system_subscribers import router as system_router
from saltbox_bridge.event_bus.subscribers.system_subscribers import router_not_auth as system_router_not_auth

router = RedisRouter(prefix='master_')

router.include_routers(
    minion_router,
    minion_router_not_auth,
    pillar_router,
    pillar_router_not_auth,
    system_router,
    system_router_not_auth,
)
