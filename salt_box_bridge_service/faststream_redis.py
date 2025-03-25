from __future__ import annotations

import os
import ssl
from collections.abc import Callable
from typing import Literal

from faststream import FastStream
from faststream.redis import RedisBroker, RedisRouter
from faststream.redis.publisher.asyncapi import AsyncAPIPublisher
from faststream.redis.subscriber.asyncapi import AsyncAPISubscriber
from faststream.security import SASLPlaintext


class RedisConf:
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        ssl_cert_reqs: Literal['none', 'optional', 'required'] = 'required',
        ssl_ca_certs: str | None = None,
    ):
        self.url = url
        self.username = username
        self.password = password
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs


def get_faststream_broker(
    redis_conf: RedisConf,
) -> RedisBroker:
    if redis_conf.url.startswith('rediss:'):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ssl_context.verify_mode = {
            'none': ssl.CERT_NONE,
            'required': ssl.CERT_REQUIRED,
            'optional': ssl.CERT_OPTIONAL,
        }[redis_conf.ssl_cert_reqs]

        if redis_conf.ssl_ca_certs:
            ssl_context.load_verify_locations(cafile=os.path.relpath(redis_conf.ssl_ca_certs), capath=None, cadata=None)

        security = SASLPlaintext(username=redis_conf.username, password=redis_conf.password, ssl_context=ssl_context)
    else:
        security = SASLPlaintext(username=redis_conf.username, password=redis_conf.password)

    return RedisBroker(url=redis_conf.url, security=security)


def get_faststream_subscriber(
    channel: str,
    redis_conf: RedisConf | None = None,
    broker: RedisBroker | None = None,
) -> AsyncAPISubscriber:
    if not broker:
        if not redis_conf:
            msg = 'Redis broker not configured'
            raise RuntimeError(msg)

        broker: RedisBroker = get_faststream_broker(redis_conf=redis_conf)

    return broker.subscriber(channel)


def get_faststream_publisher(
    channel: str,
    redis_conf: RedisConf | None = None,
    broker: RedisBroker | None = None,
) -> AsyncAPIPublisher:
    if not broker:
        if not redis_conf:
            msg = 'Redis broker not configured'
            raise RuntimeError(msg)

        broker: RedisBroker = get_faststream_broker(redis_conf=redis_conf)

    return broker.publisher(channel)


def get_faststream_app(
    routers: list[RedisRouter],
    redis_conf: RedisConf | None = None,
    broker: RedisBroker | None = None,
    lifespan: Callable | None = None,
) -> FastStream:
    if not broker:
        if not redis_conf:
            msg = 'Redis broker not configured'
            raise RuntimeError(msg)

        broker: RedisBroker = get_faststream_broker(redis_conf=redis_conf)

    for router in routers:
        broker.include_router(router)

    if lifespan:
        return FastStream(broker, lifespan=lifespan)
    else:
        return FastStream(broker)
