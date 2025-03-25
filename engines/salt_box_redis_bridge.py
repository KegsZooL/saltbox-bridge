"""
Salt master config:

    module_dirs:
      - /srv/salt_extmod/  # Custom modules' dir for the master
                           # better not to mix with /srv/salt/

    engines:
      - salt_box_redis_bridge:  # start() args following
          host: localhost  # Redis instance

Put the module to /srv/salt_extmod/engines/

Restart salt-master. Log and exceptions will be in salt-master log.
"""

from __future__ import annotations

import logging
from typing import Literal

from salt_box_bridge_service.bridge import start as start_bridge

__opts__: dict
__salt__: dict

LOGGER = logging.getLogger(__name__)


def __virtual__() -> bool | tuple[bool, str]:  # noqa: N807
    if __opts__['__role'] != 'master':  # noqa: F821
        return False, f'{__name__} runs on master only'
    return True


def start(
    redis_host: str = 'localhost',
    port: int = 6379,
    username: str | None = None,
    password: str | None = None,
    db: int = 0,
    ssl=False,
    ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required',
    ssl_ca_certs: str | None = None,
    expire: int | None = None,
    master_secret: str | None = None,
) -> None:
    """
    Start a salt.box redis bridge.

    Args:
        port: Redis client connection port
        username: Redis client allowed username
        password: Redis client user password
        db: Redis client database index
        ssl: Redis client TLS encryption flag
        ssl_cert_reqs: Redis client validation policy
        ssl_ca_certs: Redis client path to server root certs concatenated file
        expire: Time of records live in seconds
        redis_host: Redis client connection host
        master_secret: Salt master secret
    """

    LOGGER.info('Starting salt.box redis bridge as an engine')
    start_bridge(
        salt_opts=__opts__,  # noqa: F821
        redis_host=redis_host,
        port=port,
        username=username,
        password=password,
        db=db,
        ssl=ssl,
        ssl_cert_reqs=ssl_cert_reqs,
        ssl_ca_certs=ssl_ca_certs,
        expire=expire,
        master_secret=master_secret,
    )
