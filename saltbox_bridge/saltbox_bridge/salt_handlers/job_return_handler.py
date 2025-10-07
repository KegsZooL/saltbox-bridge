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

logger = logging.getLogger(__name__)


class JobReturnMessageHandler(BaseMessageHandler):
    """
    A message handler that handles salt job return messages
    """

    tag_patterns: ClassVar[list[re.Pattern[str]]] = [re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)')]
    METRIC_TAG = 'metrics:job_return'
    METRIC_TASK_TAG = 'metrics:task:job_return'
    INVENTORY_SAVED_MSG_TAG = 'inventory_saved'
    INVENTORY_STATE = 'inventory'

    _STATUS_SUCCESS = 'success'
    _STATUS_PARTIAL_SUCCESS = 'partial_success'
    _STATUS_FAILED = 'failed'

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
        data = await super().normalize_data(match=match, tag=tag, data=data)
        data['salt_master'] = self.master_id

        return data

    async def process(
        self, match: re.Match, data: MessageDataType, job: dict[str, Any] | None = None, tid: str | None = None
    ) -> None:
        jid = match.group('jid')
        mid = match.group('mid')
        function = data['fun']
        data_json = json.dumps(data)

        if tid:
            logger.info('Job %s (task %s) return for %s, function %s', jid, tid, mid, function)
        else:
            logger.info('Job %s return for %s, function %s', jid, mid, function)

        send_presence_task = asyncio.create_task(self._send_presence(mid=mid, data=data))
        process_task_task = None
        if tid:
            process_task_task = self._process_task(jid=jid, tid=tid, data_json=data_json)

        await send_presence_task
        if process_task_task:
            await process_task_task
        await self._process_return(jid=jid, mid=mid, function=function, data=data, data_json=data_json)

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

    async def _process_task(self, jid: str, tid: str, data_json: str | bytes) -> None:
        await self.redis_client.publish(channel=f'task:{tid}:job:{jid}:return', message=data_json)

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
        job = await self.core_connector.get_job(jid=jid)

        if not job:
            return

        job.setdefault('minions', [])
        new_data: dict[str, Any] = {
            'returning': job.get('returning', {}),
        }

        if not job:
            logger.debug('Failed to get job return for %s%: %s', jid)
            return

        job.setdefault('returning', {})[mid] = data['retcode'] == 0
        is_finished = all(mid in job['returning'].keys() for mid in job['minions'])

        if is_finished:
            new_data['status'] = 'finished'
        else:
            new_data['status'] = 'waiting_returns'

        await self.core_connector.update_or_create_job(
            jid=jid,
            data=new_data,
            job=job,
            notify_channel='job:{jid}:update',
        )

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

    async def _prepare_metrics_data(
        self, match: re.Match, tag: str, data: MessageDataType, tid: str | None = None
    ) -> dict:
        metrics_data = await super()._prepare_metrics_data(match=match, tag=tag, data=data)
        metrics_data.update(
            {
                'jid': match.group('jid'),
                'minion_id': match.group('mid'),
                'stamp': data['_stamp'],
            }
        )

        if tid:
            metrics_data.update({'tid': tid, 'job_status': await self._extract_job_status(data)})

        return metrics_data

    async def process_metrics(self, match: re.Match, tag: str, data: MessageDataType, tid: str | None = None) -> None:
        await super().process_metrics(match=match, tag=tag, data=data)

        if tid:
            await self.redis_client.publish(
                channel=self.METRIC_TASK_TAG,
                message=json.dumps(await self._prepare_metrics_data(match=match, tag=tag, data=data, tid=tid)),
            )
