from __future__ import annotations

from pydantic_settings import BaseSettings

from saltbox_bridge.salt_metrics.event_total_metric import EventTotalMetric
from saltbox_bridge.salt_metrics.job_new_metric import JobNewMetric
from saltbox_bridge.salt_metrics.job_return_metric import JobReturnMetric

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
        'clazz': EventTotalMetric,
        'desc': '',
        'labels': EventTotalMetric.labels
    },
]


class MetricSettings(BaseSettings):
    port: int = 8004
    addr: str = '0.0.0.0'  # noqa: S104
    certfile: str | None = None
    keyfile: str | None = None
    client_cafile: str | None = None
    client_capath: str | None = None
    client_auth_required: bool = False
