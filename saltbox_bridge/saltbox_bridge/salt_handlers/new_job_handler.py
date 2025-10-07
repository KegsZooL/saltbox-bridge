from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, ClassVar

from salt.utils import json  # type: ignore

from saltbox_bridge.exceptions import StopProcessing
from saltbox_bridge.salt_handlers.base_handler import BaseMessageHandler, MessageDataType

logger = logging.getLogger(__name__)


class JobNewMessageHandler(BaseMessageHandler):
    """
    A message handler for new job salt message when
    """

    tag_patterns: ClassVar[list[re.Pattern[str]]] = [re.compile(r'^salt/job/(?P<jid>\d{20})/new$')]
    METRIC_TAG = 'metrics:new_job'
    METRIC_TASK_TAG = 'metrics:task:new_job'
    # Mention: on salt-call call there is no salt/job/*/new event
    # (but salt/job/*/ret/* it is)

    async def _handle(self, match: re.Match, tag: str, data: MessageDataType) -> None:
        data = await self.normalize_data(match=match, tag=tag, data=data)

        jid = match.group('jid')
        job = await self.core_connector.get_job(jid)

        tid: str | None = None

        if job and 'source' in job.keys() and job['source'].get('type') == 'task':
            tid = job['source']['id']

        process_metrics_task = None
        if self.can_process_metrics():
            process_metrics_task = asyncio.create_task(self.process_metrics(match=match, tag=tag, data=data, tid=tid))

        await self.process(match=match, data=data, job=job, tid=tid)

        if process_metrics_task is not None:
            await process_metrics_task

    async def normalize_data(self, match: re.Match, tag: str, data: MessageDataType) -> MessageDataType:
        # US292: Job* models exept `tgt: str`
        if isinstance(tgt := data.get('tgt'), list):
            data['tgt'] = ','.join(tgt)

        data['system_user'] = data.pop('user', None)

        return data

    async def process(
        self, match: re.Match, data: MessageDataType, job: dict[str, Any] | None = None, tid: str | None = None
    ) -> None:
        jid = match.group('jid')

        if tid:
            logger.info('New job (jid: %s) for task: %s', jid, tid)
        else:
            logger.info('New job: %s', jid)

        await self.core_connector.update_or_create_job(jid=jid, data=data, job=job, notify_channel='job:{jid}:new')

        if tid:
            await self.redis_client.publish(channel=f'task:{tid}:job:{jid}:new', message=json.dumps(data))

        raise StopProcessing()

    async def _prepare_metrics_data(
        self, match: re.Match, tag: str, data: MessageDataType, tid: str | None = None
    ) -> dict:
        metrics_data = await super()._prepare_metrics_data(match=match, tag=tag, data=data)
        metrics_data.update(
            {
                'jid': match.group('jid'),
                'tgt': data['tgt'],
                'fun': data['fun'],
                'stamp': data['_stamp'],
            }
        )

        if tid:
            metrics_data.update({'tid': tid})

        return metrics_data

    async def process_metrics(self, match: re.Match, tag: str, data: MessageDataType, tid: str | None = None) -> None:
        await super().process_metrics(match=match, tag=tag, data=data)

        if tid:
            await self.redis_client.publish(
                channel=self.METRIC_TASK_TAG,
                message=json.dumps(await self._prepare_metrics_data(match=match, tag=tag, data=data, tid=tid)),
            )
