from __future__ import annotations

import logging
import re
from typing import Any

from salt.exceptions import SaltException

from salt_box_bridge_service.exceptions import StopProcessing
from salt_box_bridge_service.salt_handlers.base_handler import BaseMessageHandler

LOGGER = logging.getLogger(__name__)


class MinionStartedMessageHandler(BaseMessageHandler):
    """
    A message handler for salt minion started messages
    """

    tag_pattern = re.compile(r'salt/minion/(?P<mid>.+)/start')

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        mid = match.group('mid')

        LOGGER.debug('salt/minion/%s/start', mid)

        try:
            self.salt_client.cmd_async(tgt=mid, fun='grains.items')
        except SaltException as err:
            LOGGER.exception(str(err))

        raise StopProcessing()
