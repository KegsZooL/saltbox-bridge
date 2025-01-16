from __future__ import annotations

import asyncio
import logging
import os
import sys

from typing import Literal

import salt.config  # type:ignore

from redis import asyncio as aioredis

from salt_box_bridge_service.consumer import SaltConsumer

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'


async def run(salt_opts: dict) -> None:
    redis_host: str = os.getenv('REDIS_HOST', 'redis-salt')
    port: int = 6379
    db: int = 0
    username = os.environ['REDIS_USERNAME']
    ssl: bool = True
    ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required'
    ssl_ca_certs = '/etc/redis/certs/ca.crt'
    redis_password_file: str = os.getenv('REDIS_PASSWORD_FILE', '')
    salt_master = salt_opts['salt_box_master_id']

    with open(redis_password_file, 'r') as file:
        password = file.readline()

    redis_client = aioredis.Redis(
        host=redis_host,
        port=port,
        db=db,
        username=username,
        password=password,
        ssl=ssl,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
    )

    consumer = SaltConsumer(
        redis_client=redis_client,
        salt_opts=salt_opts,
        salt_master=salt_master,
        channel='salt-service',
        channel_returns='salt-service-returns',
    )

    await consumer.consume()


def main(salt_opts: dict | None = None) -> None:
    if salt_opts is None:
        salt_opts = salt.config.client_config('/etc/salt/master')

    log_level: str = os.getenv('SALT_BRIDGE_SERVICE_LOG_LEVEL', 'INFO')

    logging.basicConfig()
    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    asyncio.run(run(salt_opts))


if __name__ == '__main__':
    main()
