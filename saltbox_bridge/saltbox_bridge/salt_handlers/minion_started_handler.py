from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

from salt.exceptions import SaltException  # type: ignore

from saltbox_bridge.exceptions import StopProcessing
from saltbox_bridge.salt_handlers.base_handler import BaseMessageHandler

LOGGER = logging.getLogger(__name__)


class MinionStartedMessageHandler(BaseMessageHandler):
    """
    A message handler for salt minion started messages
    """

    tag_patterns: ClassVar[list[re.Pattern[str]]] = [re.compile(r'salt/minion/(?P<mid>.+)/start')]

    async def process(self, match: re.Match, data: dict[str, Any]) -> None:
        mid = match.group('mid')

        LOGGER.debug('salt/minion/%s/start', mid)

        try:
            self.salt_client.cmd_async(tgt=mid, fun='grains.items')
        except SaltException as err:
            LOGGER.exception(str(err))

        raise StopProcessing()
