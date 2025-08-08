from __future__ import annotations

from saltbox_bridge.salt_metrics.event.event_payload_size_metric import EventPayloadSizeMetric
from saltbox_bridge.salt_metrics.event.tagged_event_metric import TaggedEventCountMetric
from saltbox_bridge.salt_metrics.job.job_new_metric import JobNewMetric
from saltbox_bridge.salt_metrics.job.job_return_metric import JobReturnMetric
from saltbox_bridge.salt_metrics.task_metric import TaskMetric

METRIC_SPECS = [
    {
        'key': 'job_new',
        'clazz': JobNewMetric,
        'desc': 'Total number of new jobs received',
        'labels': JobNewMetric.labels
    },
    {
        'key': 'job_ret',
        'clazz': JobReturnMetric,
        'desc': 'Total number of job returns',
        'labels': JobReturnMetric.labels
    },
    {
        'key': 'event_total',
        'clazz': TaggedEventCountMetric,
        'desc': 'Total number of tagged events',
        'labels': TaggedEventCountMetric.labels
    },
    {
        'key': 'event_payload_size',
        'clazz': EventPayloadSizeMetric,
        'desc': 'Sum of payload sizes for all tagged events',
        'labels': EventPayloadSizeMetric.labels
    },
    {
        'key': 'task_status',
        'clazz': TaskMetric,
        'desc': 'Task status metric',
        'labels': TaskMetric.labels
    },
]
