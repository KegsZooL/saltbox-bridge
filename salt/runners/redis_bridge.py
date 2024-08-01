"""
FastMS engines.redis_bridge related functions
"""

from datetime import datetime, timedelta

import redis

from salt.exceptions import CommandExecutionError  # type: ignore


def __virtual__() -> bool:
    return True


def cleanup_expired_jobs(expire: int, host='localhost', port=6379, db=0) -> int:
    """
    Cleanup expired records in jobs sorted set and return amount of deletions

    expire
        How old in seconds records will be deleted

    host: 'localhost'
        Redis host connection option

    port: 6379
        Redis port connection option

    db: 0
        Redis db connection option

    CLI Example:

    .. code-block:: bash

        salt-run redis_bridge.cleanup_expired_jobs 3600 host=redis-host
    """
    redis_client = redis.Redis(host=host, port=port, db=db)
    expiration_time = (datetime.now() - timedelta(seconds=expire)).timestamp()
    try:
        return redis_client.zremrangebyscore('jobs', min=0.0, max=expiration_time)
    except redis.ConnectionError as err:
        raise CommandExecutionError(err)
