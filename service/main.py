import asyncio
import logging
import os
import sys

from typing import Literal

from redis import asyncio as aioredis

from consumer import SaltConsumer

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'


async def run() -> None:
    host: str = 'redis-salt'
    port: int = 6379
    db: int = 0
    username = os.environ['REDIS_USERNAME']
    ssl: bool = True
    ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required'
    ssl_ca_certs = '/etc/redis/certs/ca.crt'
    redis_password_file: str = os.getenv('REDIS_PASSWORD_FILE', '')
    salt_master = os.getenv('SALT_MASTER', 'salt-master')  # TODO From conf

    with open(redis_password_file, 'r') as file:
        password = file.readline()

    redis_client = aioredis.Redis(
        host=host,
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
        salt_master=salt_master,
        channel='salt-service',
        channel_returns='salt-service-returns',
    )

    await consumer.consume()


def main() -> None:
    log_level: str = os.getenv('SALT_BRIDGE_SERVICE_LOG_LEVEL', 'INFO')

    logging.basicConfig()
    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    asyncio.run(run())


if __name__ == '__main__':
    main()
