from __future__ import annotations

import asyncio
import logging

from prometheus_client import CollectorRegistry, disable_created_metrics, start_http_server

from saltbox_bridge.config import SETTINGS

logger = logging.getLogger(__name__)


async def start_prometheus_client(registry: CollectorRegistry) -> None:
    def run() -> None:
        port = SETTINGS.prometheus_client_port
        logger.info("Starting Prometheus metrics server on port %s", port)
        try:
            disable_created_metrics()  # type: ignore[no-untyped-call]
            _ = start_http_server(
                  port=port,
                  addr=SETTINGS.prometheus_client_addr,
                  registry=registry,
                  certfile=SETTINGS.prometheus_client_certfile,
                  keyfile=SETTINGS.prometheus_client_keyfile,
                  client_cafile=SETTINGS.prometheus_client_cafile,
                  client_capath=SETTINGS.prometheus_client_capath,
                  client_auth_required=SETTINGS.prometheus_client_auth_required
                )
            logger.info("Prometheus metrics server launched")
        except Exception as ex:
            logger.exception("Failed to start prometheus_client on '%s' port", port)
            raise ex

    await asyncio.to_thread(run)
