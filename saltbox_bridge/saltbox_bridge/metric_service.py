from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry, disable_created_metrics, start_http_server
from salt.utils.ssdp import asyncio

from saltbox_bridge.salt_metrics.metric_settings import MetricSettings

logger = logging.getLogger(__name__)


async def start_prometheus_client(registry: CollectorRegistry) -> None:
    def run() -> None:
        settings = MetricSettings()
        logger.info("Starting Prometheus metrics server on port %s", settings.port)

        try:
            disable_created_metrics()
            _ = start_http_server(
                  port=settings.port,
                  addr=settings.addr,
                  registry=registry,
                  certfile=settings.certfile,
                  keyfile=settings.keyfile,
                  client_cafile=settings.client_cafile,
                  client_capath=settings.client_capath,
                  client_auth_required=settings.client_auth_required
                )
            logger.info("Prometheus metrics server launched")
        except Exception as ex:
            logger.exception("Failed to start prometheus_client on '%s' port", settings.port)
            raise ex

    await asyncio.to_thread(run)
