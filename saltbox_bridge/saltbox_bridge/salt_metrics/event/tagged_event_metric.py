from __future__ import annotations

import re
import sys
from typing import ClassVar

from prometheus_client import Summary

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import EventBaseMetric


class TaggedEventCountMetric(EventBaseMetric):
    """
    A metric that counts salt but events grouped by tag type
    and counts the msg size in bytes (e.g. job_ret, job_new, etc...)
    """
    AVAILABLE_TAG_NAME_TO_REGEX: ClassVar[list[tuple[str, re.Pattern, bool]]] = [
        ('job_ret', re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)'), True),
        ('job_new', re.compile(r'^salt/job/(?P<jid>\d{20})/new$'), True),
        ('minion/refresh', re.compile(r'^minion/refresh/[a-z-]+-[a-f0-9]{12}$'), True),
        ('unavailable', re.compile(r'^\d{20}$'), False)
    ]

    @property
    def labels(self) -> list[str]:
        return ['master', 'tag']

    def _create(self) -> Summary:
        return Summary(
            name=self.name, documentation=self.desc, labelnames=self.labels, registry=self.registry)

    async def aggregate(self, tag: str, data: MessageDataType) -> None:
        master = self.salt_opts['salt_box_master_id']
        payload_size = sys.getsizeof(data)
        for tag_name, pattern, is_available in self.AVAILABLE_TAG_NAME_TO_REGEX:
            if pattern.match(tag):
                if is_available:
                    self.metric.labels(master=master, tag=tag_name).observe(payload_size)  # type: ignore[attr-defined]
                return
        self.metric.labels(master=master, tag=tag).observe(payload_size)  # type: ignore[attr-defined]
