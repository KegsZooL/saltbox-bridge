import asyncio
import os
from typing import Literal

from consumer import SaltConsumer


async def __main__():
    host: str = 'redis-salt'
    port: int = 6379
    db: int = 0
    username = os.environ['REDIS_USERNAME']
    ssl: bool = True
    ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required'
    ssl_ca_certs = '/etc/redis/certs/ca.crt'

    with open('/run/secrets/redis_salt_password', 'r') as file:
        password = file.readline()  # TODO: get redis password from env

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


if __name__ == '__main__':
    asyncio.run(__main__())
