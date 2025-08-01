from __future__ import annotations

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import BaseMetric


class MetricRouter:
    def __init__(self, metrics: list[BaseMetric]):
        self.metrics = metrics

    async def route_and_aggregate(self, tag: str, data: MessageDataType) -> None:
        for metric in self.metrics:
            if metric.can_handle(tag=tag):
                await metric.aggregate(tag=tag, data=data)
