from __future__ import annotations

import asyncio
import json
import logging
from fnmatch import fnmatch
from typing import Any

from saltbox_bridge.redis import get_redis_client

__opts__: dict

LOGGER = logging.getLogger(__name__)


def __virtual__() -> bool | tuple[bool, str]:  # noqa: N807
    if __opts__['__role'] != 'master':  # noqa: F821
        return False, f'{__name__} runs on master only'
    return True


def get_loaded_pillars(pillars: dict) -> dict:
    for key, value in pillars.items():
        if isinstance(value, (bytes, bytearray)):
            sval = value.decode()
        else:
            sval = value
        try:
            pillars[key] = json.loads(sval)
        except Exception:
            pillars[key] = sval
    return pillars


async def async_ext_pillar(minion_id: str, pillar: dict, *args: Any, **kwargs: Any) -> dict:
    master_id: str = __opts__['salt_box_master_id']  # noqa: F821

    redis_client = get_redis_client()

    # Load global pillars
    pillars: dict = await redis_client.hgetall(f'pillar:{master_id}')
    pillars = get_loaded_pillars(pillars)

    # Load pattern-matched pillars using SCAN (non-blocking) instead of KEYS
    cursor = 0
    match = f'pillar:{master_id}:*'
    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match=match, count=1000)
        for key in keys:
            if isinstance(key, (bytes, bytearray)):
                key_s = key.decode()
            else:
                key_s = str(key)
            pattern = key_s.split(':', 2)[2]

            if fnmatch(minion_id, pattern):
                minion_specific_pillars: dict = await redis_client.hgetall(key)
                minion_specific_pillars = get_loaded_pillars(minion_specific_pillars)
                pillars.update(minion_specific_pillars)
        if not cursor:
            break

    return pillars


def ext_pillar(minion_id: str, pillar: dict, *args: Any, **kwargs: Any) -> dict:
    return asyncio.run(async_ext_pillar(minion_id, pillar, *args, **kwargs))
