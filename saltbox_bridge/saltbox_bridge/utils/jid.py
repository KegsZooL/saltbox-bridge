from __future__ import annotations

import re
from datetime import datetime, timezone

from salt.exceptions import SaltMasterError, SaltRunnerError  # type: ignore

JID_REGEX = (
    r'^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})'
    r'(?P<minute>\d{2})(?P<second>\d{2})(?P<microsecond>\d{6})$'
)
JID_PATTERN = re.compile(JID_REGEX)


def jid_to_epoch(jid: str) -> float:
    if not (match := JID_PATTERN.match(jid)):
        msg = f'Unexpected JID format: {jid}'
        raise SaltMasterError(msg)

    kwargs = {k: int(val) for k, val in match.groupdict().items()}

    try:
        dt = datetime(**kwargs, tzinfo=timezone.utc)
    except ValueError as err:
        raise SaltRunnerError(err) from err

    return dt.timestamp()
