from __future__ import annotations

import re
from typing import ClassVar

from prometheus_client import Counter

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import BaseMetric


class EventTotalMetric(BaseMetric):
    """
    A metric reflects the total number of events passed in salt bus
    """
    AVAILABLE_TAG_NAME_TO_REGEX: ClassVar[list[tuple[str, re.Pattern, bool]]] = [
        ('job_ret', re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)'), True),
        ('job_new', re.compile(r'^salt/job/(?P<jid>\d{20})/new$'), True),
        ('unavailable', re.compile(r'^\d{20}$'), False)
    ]

    def _create(self) -> Counter:
        return Counter(
            name=self.name, documentation=self.desc, labelnames=self.labels, registry=self.registry)

    @property
    def labels(self) -> list[str]:
        return ['master', 'tag']

    def can_handle(self, tag: str) -> bool:
        return True

    async def aggregate(self, tag: str, data: MessageDataType) -> None:
        master = self.salt_opts['salt_box_master_id']
        for tag_name, pattern, is_available in self.AVAILABLE_TAG_NAME_TO_REGEX:
            if pattern.match(tag):
                if is_available:
                    self.metric.labels(master=master, tag=tag_name).inc()  # type: ignore[attr-defined]
                return
        self.metric.labels(master=master, tag=tag).inc()  # type: ignore[attr-defined]
