from __future__ import annotations

import logging
import re
from typing import ClassVar

from redis.asyncio.client import Pipeline
from salt.utils import json  # type: ignore

from saltbox_bridge.exceptions import StopProcessing
from saltbox_bridge.salt_handlers.base_handler import BaseMessageHandler, MessageDataType
from saltbox_bridge.utils.jid import jid_to_epoch

logger = logging.getLogger(__name__)


class JobNewMessageHandler(BaseMessageHandler):
    """
    A message handler for new job salt message when
    """

    tag_patterns: ClassVar[list[re.Pattern[str]]] = [re.compile(r'^salt/job/(?P<jid>\d{20})/new$')]
    METRIC_TAG = 'metrics:new_job'
    # Mention: on salt-call call there is no salt/job/*/new event
    # (but salt/job/*/ret/* it is)

    async def normalize_data(self, match: re.Match, tag: str, data: MessageDataType) -> MessageDataType:
        # US292: Job* models exept `tgt: str`
        if isinstance(tgt := data.get('tgt'), list):
            data['tgt'] = ','.join(tgt)

        job_create_data: dict[bytes, bytes] = await self.redis_client.hgetall(f'job_create:{data["jid"]}')
        raw_user_data = job_create_data.get(b'user', None)

        if raw_user_data:
            user_data = json.loads(raw_user_data.decode('utf-8'))
        else:
            user_data = {'sub': 'system', 'email_verified': True, 'name': 'System', 'email': 'system@localhost'}

        data['salt_master'] = self.master_id
        data['returning'] = {}
        data['system_user'] = data.get('user', None)
        data['user'] = user_data

        return data

    async def process(self, match: re.Match, data: MessageDataType) -> None:
        jid = match.group('jid')
        data_json = json.dumps(data)
        logger.info('New job: %s', jid)

        async with self.redis_client.pipeline() as pipe:
            self._save_job_pipeline(pipe, jid=jid, data_json=data_json)
            await pipe.execute()

        raise StopProcessing()

    def _save_job_pipeline(self, pipe: Pipeline, jid: str, data_json: str) -> Pipeline:
        # TODO: Key should be uniq for master to prevent possible JID overlaps
        pipe = pipe.zadd(name='jobs', mapping={data_json: jid_to_epoch(jid)})
        pipe = pipe.publish(channel=f'job:{jid}:new', message=data_json)
        return pipe

    async def _prepare_metrics_data(self, match: re.Match, tag: str, data: MessageDataType) -> dict:
        metrics_data = await super()._prepare_metrics_data(match=match, tag=tag, data=data)
        metrics_data.update(
            {
                'jid': match.group('jid'),
                'tgt': data['tgt'],
                'fun': data['fun'],
                'stamp': data['_stamp'],
            }
        )

        return metrics_data


class JobNewForTaskMessageHandler(JobNewMessageHandler):
    """
    A message handler for new job salt message when for task
    """

    tag_patterns: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r'^salt/job/(?P<jid>\d{20})-t(?P<tid>[a-zA-Z0-9]{24})/new$')
    ]
    METRIC_TASK_TAG = 'metrics:task:new_job'

    async def normalize_data(self, match: re.Match, tag: str, data: MessageDataType) -> MessageDataType:
        data['jid'] = match.group('jid')
        return await super().normalize_data(match=match, tag=tag, data=data)

    async def process(self, match: re.Match, data: MessageDataType) -> None:
        jid = match.group('jid')
        tid = match.group('tid')

        data_json = json.dumps(data)

        logger.info('New job (jid: %s) for task: %s', jid, tid)

        async with self.redis_client.pipeline() as pipe:
            self._save_job_pipeline(pipe, jid=jid, data_json=data_json)
            pipe = pipe.publish(channel=f'task:{tid}:job:{jid}:new', message=data_json)
            await pipe.execute()

        raise StopProcessing()

    async def _prepare_metrics_data(self, match: re.Match, tag: str, data: MessageDataType) -> dict:
        metrics_data = await super()._prepare_metrics_data(match=match, tag=tag, data=data)
        metrics_data.update({'tid': match.group('tid')})

        return metrics_data

    async def process_metrics(self, match: re.Match, tag: str, data: MessageDataType) -> None:
        await super().process_metrics(match=match, tag=tag, data=data)

        await self.redis_client.publish(
            channel=self.METRIC_TASK_TAG, message=json.dumps(await self._prepare_metrics_data(match, tag, data))
        )
