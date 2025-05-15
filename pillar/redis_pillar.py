from __future__ import annotations

import asyncio
import logging
from typing import Any

from saltbox_bridge.redis import get_redis_client

__opts__: dict

LOGGER = logging.getLogger(__name__)


def __virtual__() -> bool | tuple[bool, str]:  # noqa: N807
    if __opts__['__role'] != 'master':  # noqa: F821
        return False, f'{__name__} runs on master only'
    return True


async def async_ext_pillar(minion_id: str, pillar: dict, *args: Any, **kwargs: Any) -> dict:
    master_id: str = __opts__['salt_box_master_id']  # noqa: F821

    redis_client = get_redis_client()

    pillars: dict = await redis_client.hgetall(f'pillar:{master_id}')
    pillars.update(await redis_client.hgetall(f'pillar:{master_id}:{minion_id}'))

    return pillars


def ext_pillar(minion_id: str, pillar: dict, *args: Any, **kwargs: Any) -> dict:
    return asyncio.run(async_ext_pillar(minion_id, pillar, *args, **kwargs))
