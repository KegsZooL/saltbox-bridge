from __future__ import annotations

import re
import sys
from typing import Any

from saltbox_bridge.salt_handlers.base_handler import BaseMessageHandler, MessageDataType


class SaltMessageMetricMessageHandler(BaseMessageHandler):
    """
    A message handler for salt payload size
    """

    tag_pattern = re.compile(r'salt/.+')
    METRIC_TAG = 'metrics:salt_message'

    async def process(self, match: re.Match, data: dict[str, Any]) -> None: ...

    async def _prepare_metrics_data(self, match: re.Match, tag: str, data: MessageDataType) -> dict:
        metrics_data = await super()._prepare_metrics_data(match=match, tag=tag, data=data)
        metrics_data.update(
            {
                'payload_size': sys.getsizeof(data),
                'tag': tag,
            }
        )

        return metrics_data
