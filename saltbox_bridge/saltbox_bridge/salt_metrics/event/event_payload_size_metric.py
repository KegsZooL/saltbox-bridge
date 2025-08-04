from __future__ import annotations

import sys

from prometheus_client import Summary

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import EventBaseMetric


class EventPayloadSizeMetric(EventBaseMetric):

    @property
    def labels(self) -> list[str]:
        return ['master']

    def _create(self) -> Summary:
        return Summary(
            name=self.name, documentation=self.desc, labelnames=self.labels, registry=self.registry)

    async def aggregate(self, tag: str, data: MessageDataType) -> None:
        payload_size = sys.getsizeof(data)
        self.metric.labels(master=self.master).observe(payload_size)  # type: ignore[attr-defined]
