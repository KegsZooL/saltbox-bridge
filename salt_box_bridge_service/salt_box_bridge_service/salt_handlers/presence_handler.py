from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from salt_box_bridge_service.exceptions import StopProcessing
from salt_box_bridge_service.salt_handlers.base_handler import BaseMessageHandler
from salt_box_bridge_service.schemas.out_schemas import PresenceOutMessage


class PresenceMessageHandler(BaseMessageHandler):
    """
    A message handler for salt presence messages
    """

    tag_pattern = re.compile(r'salt/presence/present')

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        message = PresenceOutMessage(
            minions=data['present'],
            master=self.salt_opts['salt_box_master_id'],
            stamp=datetime.fromisoformat(data['_stamp']).timestamp(),
        )

        await self.send_message(message=message, message_tag='presence')

        raise StopProcessing()
