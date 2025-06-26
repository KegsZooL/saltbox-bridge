from __future__ import annotations

import logging
from typing import Any

from salt.client import Caller  # type: ignore
from salt.config import minion_config  # type: ignore

from saltbox_bridge.config import HIERARHY, SETTINGS
from saltbox_bridge.exceptions import SaltCallerTypeError

logger = logging.getLogger(__name__)


def get_salt_caller() -> Caller:
    opts = minion_config('/etc/salt/minion')
    opts['file_client'] = 'local'
    return Caller(mopts=opts)


def get_state_apply_error(data: list[str] | dict[str, dict[str, Any]]) -> list[str]:
    """
    Proccess return dict from salt state.apply function, return errors
    """
    # TODO: Search for standard salt function
    # TODO: Except potential errors while getting fileds
    if isinstance(data, list):
        return ['\n'.join(data)]
    elif isinstance(data, dict):
        errors = []
        for key, val in data.items():
            if not val['result']:
                comment = val.get('comment', 'COMMENT IS MISSING')
                errors.append(f'{key}: {comment}')
        return errors
    else:
        msg = f'Unexpected return type {type(data)}'  # type: ignore[unreachable]
        raise SaltCallerTypeError(msg)


def sync_saltbox() -> None:
    state_name = 'sync_saltbox'
    logger.info('Starting %s', state_name)
    caller = get_salt_caller()
    pillar = {
        'ssh_dir': str(HIERARHY.ssh_dir),
        'sshfs_sync_on': SETTINGS.sshfs_sync_on,
        'sshfs_server': SETTINGS.sshfs_server,
        'sshfs_port': SETTINGS.sshfs_port,
        'sshfs_user': SETTINGS.sshfs_user,
        'sshfs_privkey': str(HIERARHY.sshfs_privkey),
        'sshfs_pubkey': str(HIERARHY.sshfs_pubkey),
        'salt_conf_server': SETTINGS.salt_conf_server,
        'salt_conf_port': SETTINGS.salt_conf_port,
        'salt_conf_user': SETTINGS.salt_conf_user,
        'salt_conf_privkey': str(HIERARHY.salt_conf_privkey),
        'salt_conf_pubkey': str(HIERARHY.salt_conf_pubkey),
    }
    ret = caller.cmd('state.apply', state_name, pillar=pillar)
    logger.info('Finished %s', state_name)
    if (errors := get_state_apply_error(ret)) is not None:
        for msg in errors:
            logger.error(msg)
