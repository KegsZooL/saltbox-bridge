from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from faststream import BaseMiddleware, Context
from faststream.broker.message import StreamMessage
from faststream.redis.message import RedisMessage
from faststream.types import AsyncFunc, AsyncFuncAny
from faststream.utils.context.repository import context
from pydantic import BaseModel

from saltbox_bridge.event_bus.messages.base_messages import AbstractMessage
from saltbox_bridge.exceptions import CreateSignError
from saltbox_bridge.utils.gpg import SaltBoxCrypt

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]


class MastersAuthMiddleware(BaseMiddleware):
    _crypt: SaltBoxCrypt | None = None

    @property
    def crypt(self) -> SaltBoxCrypt:
        if not self._crypt:
            self._crypt = context.get('saltbox_crypt')

        if not self._crypt:
            self._crypt = SaltBoxCrypt(master_id=context.get('salt_box_master_id'), can_gen_new_key=False)

        return self._crypt

    def create_signature(self, message: BaseModel | dict | str) -> str:
        if isinstance(message, BaseModel):
            sign = self.crypt.sign_str(message.model_dump_json())
        elif isinstance(message, dict):
            sign = self.crypt.sign_str(json.dumps(message))
        elif isinstance(message, str):
            sign = self.crypt.sign_str(message)
        else:
            msg = f'Unsupported message type: {type(message)}\n{message!s}'
            raise CreateSignError(msg)

        return sign

    def validate_signature(self, message: bytes, sign: str) -> bool:
        return True  # TODO @: check message signature

    async def consume_scope(self, call_next: AsyncFuncAny, msg: StreamMessage[Any]) -> Any:
        # sign: str | None = msg.headers.pop('sign')
        #
        # if sign is None or not self.validate_signature(message=msg.raw_message, sign=sign):
        #     return None

        try:
            message: AbstractMessage = AbstractMessage(**await msg.decode())  # type: ignore
        except Exception as e:
            error = f'Failed to decode message:\n{msg}\n{e}'
            LOGGER.error(error)
            return None

        salt_master: str = context.get('salt_master')

        if message.master and message.master != salt_master:
            LOGGER.error('Unknown master "%s"', message.master)
            return None

        return await super().consume_scope(call_next, msg)

    async def publish_scope(self, call_next: AsyncFunc, msg: Any, *args: Any, **kwargs: Any) -> Any:
        if not kwargs.get('headers'):  # By default, the "headers" item exists, but its value is None
            kwargs['headers'] = {}  # So "setdefault()" won't work in this situation

        # kwargs['headers']['sign'] = self.create_signature(msg)

        return await super().publish_scope(call_next, msg, *args, **kwargs)
