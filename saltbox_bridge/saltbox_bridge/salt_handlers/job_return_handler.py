from __future__ import annotations

import logging
import re
from typing import Any

from salt.utils import json  # type: ignore
from saltbox_bridge_messages import BridgeInventoryDataSavedMessage, BridgeMinionGrainsMessage

from saltbox_bridge.config import SETTINGS
from saltbox_bridge.exceptions import StopProcessing
from saltbox_bridge.salt_handlers.base_handler import BaseMessageHandler

logger = logging.getLogger(__name__)


class JobReturnMessageHandler(BaseMessageHandler):
    """
    A message handler that handles salt job return messages
    """

    tag_pattern = re.compile(r'salt/job/(?P<jid>\d{20})/ret/(?P<mid>.+)')
    INVENTORY_SAVED_MSG_TAG = 'inventory_saved'

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        jid = match.group('jid')
        mid = match.group('mid')
        data['salt_master'] = self.salt_opts['salt_box_master_id']
        function = data['fun']
        data_json = json.dumps(data)

        logger.info('Job %s return for %s, function %s', jid, mid, function)

        await self._process_return(jid=jid, mid=mid, function=function, data=data, data_json=data_json)

        raise StopProcessing()

    async def _process_return(self, jid: str, mid: str, function: str, data: dict, data_json: str) -> None:
        hash_name = f'job:{jid}:return'
        async with self.redis_client.pipeline(transaction=True) as pipe:
            pipe = pipe.hset(name=hash_name, key=mid, value=data_json)
            if SETTINGS.expire is not None:
                pipe = pipe.expire(name=hash_name, time=SETTINGS.expire)
            await pipe.execute()

        await self.redis_client.publish(channel=hash_name, message=data_json)

        if function == 'grains.items':
            await self._process_grains(mid, data['return'])
        elif function == 'inventory.get':
            logger.debug('Got inventory.get return for %s', mid)
            await self._notify_on_inventory_fun(jid=jid, mid=mid, data=data)
        elif function in ('state.apply', 'state.sls') and 'inventory' in data['fun_args']:
            logger.debug('Got inventory state return for %s', mid)
            await self._notify_on_inventory_state(jid=jid, mid=mid, data=data)

    async def _notify_on_inventory_fun(self, jid: str, mid: str, data: dict[str, Any]) -> None:
        if data['retcode'] != 0:
            logger.warning('inventory.get failed for JID=%s, minion=%s', jid, mid)
            return

        message = BridgeInventoryDataSavedMessage(
            master=self.master_id,
            jid=jid,
            minions=[mid,],
            path=['return'],
        )
        await self.send_message(message=message, message_tag=self.INVENTORY_SAVED_MSG_TAG)

    async def _notify_on_inventory_state(self, jid: str, mid: str, data: dict[str, Any]) -> None:
        # TODO (a.karmanov): <US372> Check retcode
        for mod, mod_data in data['return'].items():  # noqa: B007
            if mod_data['name'] == 'inventory.get':
                break
        else:
            logger.error('Failed to find inventory.get data for JID=%s, minion=%s', jid, mid)
            return

        message = BridgeInventoryDataSavedMessage(
            master=self.master_id,
            jid=jid,
            minions=[mid,],
            path=['return', mod, 'changes', 'ret'],
        )
        await self.send_message(message=message, message_tag=self.INVENTORY_SAVED_MSG_TAG)

    async def _process_grains(self, mid: str, grains: dict[str, Any]) -> None:
        logger.debug('Processing grains for %s', mid)
        if not grains:
            return

        message = BridgeMinionGrainsMessage(master=self.master_id, grains=grains)
        await self.send_message(message=message, message_tag='grains')


class JobReturnForTaskMessageHandler(JobReturnMessageHandler):
    """
    A message handler that handles salt job return messages for tasks
    """

    tag_pattern = re.compile(r'salt/job/(?P<jid>\d{20})-t(?P<tid>[a-zA-Z0-9]{24})/ret/(?P<mid>.+)')

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

        await self._process_return(jid=jid, mid=mid, function=function, data=data, data_json=data_json)
        await self._process_task(jid=jid, tid=tid, data_json=data_json)

        raise StopProcessing()
