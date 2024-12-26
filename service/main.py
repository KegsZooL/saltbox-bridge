import asyncio
import logging
import os
import sys

from typing import Literal

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

    with open(redis_password_file, 'r') as file:
        password = file.readline()

    consumer = SaltConsumer(
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        ssl=ssl,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
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
