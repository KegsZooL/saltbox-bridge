from __future__ import annotations

from prometheus_client import CollectorRegistry

from saltbox_bridge.salt_metrics.base_metric import BaseMetric


class MetricsFactory:
    def __init__(self, registry: CollectorRegistry) -> None:
        self._instances: dict[str, BaseMetric] = {}
        self._registry = registry

    def get(self, metric_clazz: type[BaseMetric], name: str, desc: str, labels: list[str] | None) -> BaseMetric:
        if name not in self._instances:
            self._instances[name] = metric_clazz(
                registry=self._registry,
                name=name,
                desc=desc,
                labels=labels
            )
        return self._instances[name]
