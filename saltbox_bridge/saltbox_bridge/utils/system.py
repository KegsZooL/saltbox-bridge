from __future__ import annotations

import os
import random
import string
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_random_bytes(size: int) -> bytes:
    return os.urandom(size)


def get_random_string(size: int) -> str:
    return ''.join(random.choice(string.printable) for _ in range(size))  # noqa: S311
