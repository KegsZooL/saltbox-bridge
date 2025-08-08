from __future__ import annotations

import re
import sys
from typing import ClassVar

from prometheus_client import Summary

from saltbox_bridge.salt_handlers.base_handler import MessageDataType
from saltbox_bridge.salt_metrics.base_metric import BaseEventMetric


class TaggedEventCountMetric(BaseEventMetric):
    """
    A metric that counts salt but events grouped by tag type
    and counts the msg size in bytes (e.g. job_ret, job_new, etc...)
    """
    AVAILABLE_TAG_NAME_TO_REGEX: ClassVar[dict[str, re.Pattern]] = {
        'job_ret': re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)'),
        'job_new': re.compile(r'^salt/job/(?P<jid>\d{20})/new$'),
        'job_ret_from_task': re.compile(r'^salt/job/(?P<jid>\d{20})-t(?P<tid>[a-f0-9]{24})/ret/(?P<mid>.+)$'),
        'job_new_for_task': re.compile(r'^salt/job/(?P<jid>\d{20})-t(?P<tid>[a-f0-9]{24})/new$'),
        'minion/refresh': re.compile(r'^minion/refresh/[a-z-]+-[a-f0-9]{12}$')
    }

    @property
    def labels(self) -> list[str]:
        return ['master', 'tag']

    def _create(self) -> Summary:
        return Summary(
            name=self.name,
            documentation=self.desc,
            labelnames=self.labels,
            registry=self.registry
        )

    async def aggregate(self, tag: str, data: MessageDataType) -> None:
        master = self.salt_opts['salt_box_master_id']
        payload_size = sys.getsizeof(data)
        for tag_name in self.AVAILABLE_TAG_NAME_TO_REGEX.keys():
            if self.AVAILABLE_TAG_NAME_TO_REGEX[tag_name].match(tag):
                self.metric.labels(master=master, tag=tag_name).observe(payload_size)  # type: ignore[attr-defined]
