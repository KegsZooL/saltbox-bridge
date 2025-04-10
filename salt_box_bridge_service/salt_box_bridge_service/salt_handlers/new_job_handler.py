from __future__ import annotations

import logging
import re
from typing import Any

from salt.utils import json

from salt_box_bridge_service.exceptions import StopProcessing
from salt_box_bridge_service.salt_handlers.base_handler import BaseMessageHandler
from salt_box_bridge_service.utils.jid import jid_to_epoch

LOGGER = logging.getLogger(__name__)


class JobNewMessageHandler(BaseMessageHandler):
    """
    A message handler for new job salt message when
    """

    tag_pattern = re.compile(r'salt/job/(?P<jid>\d{20})/new')
    # Mention: on salt-call call there is no salt/job/*/new event
    # (but salt/job/*/ret/* it is)

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        data_json = json.dumps(data)
        LOGGER.info('New job: %s', jid)

        await self._process_job(jid=jid, data_json=data_json)

        raise StopProcessing()

    async def _process_job(self, jid: str, data_json: str) -> None:
        await self.redis_client.zadd(name='jobs', mapping={data_json: jid_to_epoch(jid)})
        await self.redis_client.publish(channel=f'job:{jid}:new', message=data_json)


class JobNewForTaskMessageHandler(JobNewMessageHandler):
    """
    A message handler for new job salt message when for task
    """

    tag_pattern = re.compile(r'salt/job/(?P<jid>\d{20})-t(?P<tid>[a-zA-Z0-9]{24})/new')

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        tid = match.group('tid')

        data['jid'] = jid
        data_json = json.dumps(data)

        LOGGER.info('New job (jid: %s) for task: %s', jid, tid)

        await self._process_job(jid=jid, data_json=data_json)
        await self._process_task(jid=jid, tid=tid, data_json=data_json)

        raise StopProcessing()

    async def _process_task(self, jid: str, tid: str, data_json: str) -> None:
        await self.redis_client.publish(channel=f'task:{tid}:job:{jid}:new', message=data_json)
