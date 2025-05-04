"""
FastMS engines.saltbox_delator related functions
"""

from datetime import datetime, timedelta, timezone

import redis
from salt.exceptions import CommandExecutionError  # type: ignore


def __virtual__() -> bool:  # noqa: N807
    return True


def cleanup_expired_jobs(expire: int, redis_host='localhost', port=6379, db=0) -> int:
    """
    Cleanup expired records in jobs sorted set and return amount of deletions

    expire
        How old in seconds records will be deleted

    redis_host: 'localhost'
        Redis host connection option

    port: 6379
        Redis port connection option

    db: 0
        Redis db connection option

    CLI Example:

    .. code-block:: bash

        salt-run saltbox_delator.cleanup_expired_jobs 3600 redis_host=redis-host
    """
    redis_client = redis.Redis(host=redis_host, port=port, db=db)
    expiration_time = (datetime.now(tz=timezone.utc) - timedelta(seconds=expire)).timestamp()
    try:
        return redis_client.zremrangebyscore('jobs', min=0.0, max=expiration_time)
    except redis.ConnectionError as err:
        raise CommandExecutionError(err) from err
