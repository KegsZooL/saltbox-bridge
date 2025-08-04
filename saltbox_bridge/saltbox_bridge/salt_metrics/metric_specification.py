from __future__ import annotations

from saltbox_bridge.salt_metrics.event.event_payload_size_metric import EventPayloadSizeMetric
from saltbox_bridge.salt_metrics.event.tagged_event_metric import TaggedEventCountMetric
from saltbox_bridge.salt_metrics.job.job_new_metric import JobNewMetric
from saltbox_bridge.salt_metrics.job.job_return_metric import JobReturnMetric

METRIC_SPECS = [
    {
        'key': 'job_new',
        'clazz': JobNewMetric,
        'desc': '',
        'labels': JobNewMetric.labels
    },
    {
        'key': 'job_ret',
        'clazz': JobReturnMetric,
        'desc': '',
        'labels': JobReturnMetric.labels
    },
    {
        'key': 'event_total',
        'clazz': TaggedEventCountMetric,
        'desc': '',
        'labels': TaggedEventCountMetric.labels
    },
    {
        'key': 'event_payload_size',
        'clazz': EventPayloadSizeMetric,
        'desc': '',
        'labels': EventPayloadSizeMetric.labels
    }
]
