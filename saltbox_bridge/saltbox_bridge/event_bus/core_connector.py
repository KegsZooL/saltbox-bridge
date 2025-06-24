from __future__ import annotations

import logging
from asyncio import sleep
from datetime import datetime, timedelta, timezone
from typing import Any

from faststream.redis import RedisBroker, RedisMessage
from saltbox_bridge_messages import (
    AuthRequestMessage,
    AuthResponseMessage,
    BridgeMessageBase,
    MasterStatus,
    MasterStatusMessage,
    SshPubKeyModel,
)

from saltbox_bridge.config import HIERARHY
from saltbox_bridge.event_bus.faststream_redis import get_faststream_broker
from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.utils.gpg import SaltBoxCrypt

LOGGER = logging.getLogger(__name__)


# TODO: Only Auth message
#
#    Auth ->
#         <- Status
#    [ repeate with pause while status is not accepted ]
#


class CoreConnector:
    CONNECT_RETRY_INTERVAL_SEC = 10

    def __init__(self, master_id: str, saltbox_crypt: SaltBoxCrypt):
        self.master_id = master_id
        self.saltbox_crypt = saltbox_crypt
        self.master_status = MasterStatus.new
        self.is_connected = False
        self.dt_last_check: datetime | None = None

    async def send_messagee(
        self,
        message: BridgeMessageBase,
        message_tag: str,
        broker: RedisBroker | None = None,
        is_need_auth: bool = False,
    ) -> None:
        if not broker:
            if is_need_auth:
                broker = get_faststream_broker(middlewares=[MastersAuthMiddleware])
            else:
                broker = get_faststream_broker()

        async with broker as br:
            await br.publish(message=message, channel=f'master_{message_tag}')

    async def send_messge_and_wait_response(
        self,
        message: BridgeMessageBase,
        message_tag: str,
        response_timeout: float = 3.0,
        broker: RedisBroker | None = None,
        is_need_auth: bool = False,
    ) -> Any:
        LOGGER.info('Sending message to Core: %s', message_tag)
        if not broker:
            if is_need_auth:
                broker = get_faststream_broker(middlewares=[MastersAuthMiddleware])
            else:
                broker = get_faststream_broker()

        async with broker as br:
            response: RedisMessage = await br.request(  # type: ignore
                message,
                channel=f'master_{message_tag}',
                timeout=response_timeout,
            )
            return await response.decode() if response else None

    async def update_master_status(self) -> None:
        msg = BridgeMessageBase(master=self.master_id)
        ret = await self.send_messge_and_wait_response(message=msg, message_tag='status', is_need_auth=False)
        master_status: MasterStatusMessage = MasterStatusMessage(**ret)
        LOGGER.info('Salt.Box status of master is "%s"', master_status)
        self.master_status = master_status.status

    def _make_auth_req_message(self) -> AuthRequestMessage:
        sshfs_pubkey = HIERARHY.sshfs_pubkey.open().read().strip()
        salt_conf_pubkey = HIERARHY.salt_conf_pubkey.open().read().strip()
        return AuthRequestMessage(
            master=self.master_id,
            crypt_pubkey=self.saltbox_crypt.pubkey,
            salt_conf_pubkey=SshPubKeyModel.from_str(salt_conf_pubkey),
            sshfs_pubkey=SshPubKeyModel.from_str(sshfs_pubkey),
        )

    async def _auth(self) -> None:
        ret = await self.send_messge_and_wait_response(
            message=self._make_auth_req_message(),
            message_tag='auth',
            is_need_auth=False,
        )
        master_auth = AuthResponseMessage(**ret)

        if master_auth.crypt_pubkey:
            self.saltbox_crypt.save_pubkey_core(key_data=master_auth.crypt_pubkey)

        await self.update_master_status()

    async def _connect(self) -> bool:
        await self._auth()

        if self.master_status != MasterStatus.accepted:
            msg = 'Master status is not accepted. Waiting...'
            self.dt_last_check = datetime.now(timezone.utc)
            LOGGER.warning(msg)
            return False

        self.dt_last_check = datetime.now(timezone.utc)
        return True

    async def wait_success_connection(self, timeout: int) -> None:
        dt_start_check: datetime = datetime.now(timezone.utc)

        LOGGER.info('Waiting for connection...')

        while not self.is_connected:
            if datetime.now(timezone.utc) - dt_start_check > timedelta(seconds=timeout):
                LOGGER.warning('Connection timed out, give up now')
                return

            self.is_connected = await self._connect()
            await sleep(self.CONNECT_RETRY_INTERVAL_SEC)

        LOGGER.info('Connection to Core succeed')
        return
