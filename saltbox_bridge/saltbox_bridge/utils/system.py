from __future__ import annotations

import asyncio
import logging
import os
import random
import string
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_random_bytes(size: int) -> bytes:
    return os.urandom(size)


def get_random_string(size: int) -> str:
    return ''.join(random.choice(string.printable) for _ in range(size))  # noqa: S311


class SteadyRun:
    """
    Provides generator to iterate steadily for requested duration.
    """

    def __init__(self) -> None:
        self.counter = 0
        self.lagging_counter = 0

    async def run(self, duration: timedelta, rate: int, strict: bool = True) -> AsyncGenerator[datetime]:
        """
        :param duration: how long to send fake messages
        :param rate: target messages per second rate
        :param strict: exit on timeover if stict otherwise send all rate * duration messages
        :yield: current run time
        """
        def time_series() -> Generator[datetime, None, None]:
            time = start_time
            interval = timedelta(seconds=1 / rate)
            while time < end_time:
                yield time
                time += interval

        self.counter = 0
        self.lagging_counter = 0

        if rate < 1:
            return

        start_time = utc_now()
        end_time = start_time + duration
        now = start_time

        for time in time_series():
            yield time

            self.counter += 1
            now = utc_now()
            relax_time = (time - now).total_seconds()
            if relax_time < 0:
                logging.error('BOOM')  # FIXME
                self.lagging_counter += 1
            if strict and now > end_time:
                break
            await asyncio.sleep(relax_time)
        return
