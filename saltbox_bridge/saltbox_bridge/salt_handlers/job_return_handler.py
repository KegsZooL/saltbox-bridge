from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, ClassVar

from salt.utils import json  # type: ignore
from saltbox_bridge_messages import (
    BridgeInventoryDataSavedMessage,
    BridgeMinionGrainsMessage,
    BridgeMinionPresenceMessage,
)

from saltbox_bridge.config import SETTINGS
from saltbox_bridge.exceptions import StopProcessing
from saltbox_bridge.salt_handlers.base_handler import BaseMessageHandler, MessageDataType
from saltbox_bridge.utils.jid import jid_to_epoch

logger = logging.getLogger(__name__)


class JobReturnMessageHandler(BaseMessageHandler):
    """
    A message handler that handles salt job return messages
    """

    tag_patterns: ClassVar[list[re.Pattern[str]]] = [re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)')]
    METRIC_TAG = 'metrics:job_return'
    INVENTORY_SAVED_MSG_TAG = 'inventory_saved'
    INVENTORY_STATE = 'inventory'

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        mid = match.group('mid')
        data['salt_master'] = self.salt_opts['salt_box_master_id']
        function = data['fun']
        data_json = json.dumps(data)

        logger.info('Job %s return for %s, function %s', jid, mid, function)

        send_presence_task = asyncio.create_task(self._send_presence(mid=mid, data=data))

        await self._process_return(jid=jid, mid=mid, function=function, data=data, data_json=data_json)
        await send_presence_task

        raise StopProcessing()

    @classmethod
    def _inventory_state_predicate(cls, data: dict[str, Any]) -> bool:
        fun = data['fun']
        if fun not in ('state.apply', 'state.sls'):
            return False

        fun_args = data['fun_args']
        if cls.INVENTORY_STATE in fun_args:
            return True

        # Check inventory in kwargs
        for arg in fun_args:
            if isinstance(arg, dict) and arg.get('__kwarg__'):
                mods = arg.get('mods')
                if mods == cls.INVENTORY_STATE or (isinstance(mods, list) and cls.INVENTORY_STATE in mods):
                    return True

        return False

    async def _process_return(self, jid: str, mid: str, function: str, data: dict, data_json: str) -> None:
        save_job_return_task = asyncio.create_task(
            self._save_job_return_and_notify(jid=jid, mid=mid, data_json=data_json)
        )
        update_job_task = asyncio.create_task(self._update_job_item(jid=jid, mid=mid, data=data))

        await save_job_return_task
        await update_job_task

        if function == 'grains.items':
            await self._process_grains(mid, data['return'])
        elif function == 'inventory.get':
            logger.debug('Got inventory.get return for %s', mid)
            await self._notify_on_inventory_fun(jid=jid, mid=mid, data=data)
        elif self._inventory_state_predicate(data):
            logger.debug('Got inventory state return for %s', mid)
            await self._notify_on_inventory_state(jid=jid, mid=mid, data=data)

    async def _save_job_return_and_notify(self, jid: str, mid: str, data_json: str) -> None:
        hash_name = f'job:{jid}:return'
        async with self.redis_client.pipeline() as pipe:
            pipe = pipe.hset(name=hash_name, key=mid, value=data_json)
            if SETTINGS.expire is not None:
                pipe = pipe.expire(name=hash_name, time=SETTINGS.expire)
            pipe.publish(channel=hash_name, message=data_json)
            await pipe.execute()

    async def _update_job_item(self, jid: str, mid: str, data: dict) -> None:
        logger.debug('Updating job for %s', mid)
        scored_jid = jid_to_epoch(jid)

        try:
            jobs_raw_data = await self.redis_client.zrange(name='jobs', start=scored_jid, end=scored_jid, byscore=True)  # type: ignore[call-overload]
            job_data: dict[str, Any] = json.loads(jobs_raw_data[0])
            job_data.setdefault('returning', {})[mid] = data['retcode'] == 0
        except Exception as e:
            logger.debug('Failed to get job return for %s%: %s', jid, e)
            return

        async with self.redis_client.pipeline() as pipe:
            pipe.zremrangebyscore(name='jobs', min=scored_jid, max=scored_jid)
            pipe.zadd(name='jobs', mapping={json.dumps(job_data): scored_jid})

            await pipe.execute()

    async def _notify_on_inventory_fun(self, jid: str, mid: str, data: dict[str, Any]) -> None:
        if data['retcode'] != 0:
            logger.warning('inventory.get failed for JID=%s, minion=%s', jid, mid)
            return

        message = BridgeInventoryDataSavedMessage(
            master=self.master_id,
            jid=jid,
            minions=[mid],
            path=['return'],
        )
        await self.send_message(message=message, message_tag=self.INVENTORY_SAVED_MSG_TAG)

    async def _notify_on_inventory_state(self, jid: str, mid: str, data: dict[str, Any]) -> None:
        if data['retcode'] != 0:
            logger.warning('"state.apply inventory" get failed for JID=%s, minion=%s', jid, mid)
            return

        for mod, mod_data in data['return'].items():  # noqa: B007
            if mod_data['name'] == 'inventory.get':
                if mod_data['result'] is not True:
                    logger.warning('Calling inventory.get from state seems failed for JID=%s, minion=%s', jid, mid)
                    return
                break
        else:
            logger.error('Failed to find inventory.get data for JID=%s, minion=%s', jid, mid)
            return

        message = BridgeInventoryDataSavedMessage(
            master=self.master_id,
            jid=jid,
            minions=[mid],
            path=['return', mod, 'changes', 'ret'],
        )
        await self.send_message(message=message, message_tag=self.INVENTORY_SAVED_MSG_TAG)

    async def _process_grains(self, mid: str, grains: dict[str, Any]) -> None:
        logger.debug('Processing grains for %s', mid)
        if not grains:
            return

        message = BridgeMinionGrainsMessage(master=self.master_id, grains=grains)
        await self.send_message(message=message, message_tag='grains')

    async def _send_presence(self, mid: str, data: dict[str, Any]) -> None:
        message = BridgeMinionPresenceMessage(
            minions=[mid],
            master=self.salt_opts['salt_box_master_id'],
            stamp=datetime.fromisoformat(data['_stamp']).timestamp(),
        )

        await self.send_message(message=message, message_tag='presence')

    async def _prepare_metrics_data(self, match: re.Match, tag: str, data: MessageDataType) -> dict:
        metrics_data = await super()._prepare_metrics_data(match=match, tag=tag, data=data)
        metrics_data.update(
            {
                'jid': match.group('jid'),
                'minion_id': match.group('mid'),
                'stamp': data['_stamp'],
            }
        )

        return metrics_data


class JobReturnForTaskMessageHandler(JobReturnMessageHandler):
    """
    A message handler that handles salt job return messages for tasks
    """

    tag_patterns: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r'salt/job/(?P<jid>\d{20})-t(?P<tid>[a-zA-Z0-9]{24})/ret/(?P<mid>.+)')
    ]
    METRIC_TASK_TAG = 'metrics:task:job_return'

    _STATUS_SUCCESS = 'success'
    _STATUS_PARTIAL_SUCCESS = 'partial_success'
    _STATUS_FAILED = 'failed'

    async def _process_task(self, jid: str, tid: str, data_json: str | bytes) -> None:
        await self.redis_client.publish(channel=f'task:{tid}:job:{jid}:return', message=data_json)

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        tid = match.group('tid')
        mid = match.group('mid')

        data['jid'] = jid
        data['salt_master'] = self.salt_opts['salt_box_master_id']
        function = data['fun']
        data_json = json.dumps(data)

        logger.info('Job %s (task %s) return for %s, function %s', jid, tid, mid, function)

        send_presence_task = self._send_presence(mid=mid, data=data)
        process_task_task = self._process_task(jid=jid, tid=tid, data_json=data_json)

        await self._process_return(jid=jid, mid=mid, function=function, data=data, data_json=data_json)
        await send_presence_task
        await process_task_task

        raise StopProcessing()

    async def _extract_job_status(self, data: MessageDataType) -> str:
        if data.get(self._STATUS_SUCCESS, False):
            return self._STATUS_SUCCESS
        elif isinstance(data['return'], dict):
            stage_results = []
            for stage in data['return'].values():
                stage_results.append(stage.get('result', False))
            if all(r is False for r in stage_results):
                return self._STATUS_FAILED
            elif any(r is True for r in stage_results):
                return self._STATUS_PARTIAL_SUCCESS
        return self._STATUS_FAILED

    async def _prepare_metrics_data(self, match: re.Match, tag: str, data: MessageDataType) -> dict:
        metrics_data = await super()._prepare_metrics_data(match=match, tag=tag, data=data)
        metrics_data.update({'tid': match.group('tid'), 'job_status': await self._extract_job_status(data)})

        return metrics_data

    async def process_metrics(self, match: re.Match, tag: str, data: MessageDataType) -> None:
        await super().process_metrics(match=match, tag=tag, data=data)

        await self.redis_client.publish(
            channel=self.METRIC_TASK_TAG, message=json.dumps(await self._prepare_metrics_data(match, tag, data))
        )
