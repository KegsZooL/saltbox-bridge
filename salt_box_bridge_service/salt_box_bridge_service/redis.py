from __future__ import annotations

from redis import asyncio as aioredis

from salt_box_bridge_service.config import SETTINGS


def get_redis_client():
    return aioredis.Redis(
        host=SETTINGS.redis_host,
        port=SETTINGS.redis_port,
        db=SETTINGS.redis_db,
        username=SETTINGS.redis_username,
        password=SETTINGS.redis_password,
        ssl=SETTINGS.redis_ssl_use,
        ssl_cert_reqs=SETTINGS.redis_ssl_cert_reqs,
        ssl_ca_certs=SETTINGS.redis_ssl_ca_certs,
    )
