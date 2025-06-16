from __future__ import annotations

import logging
from typing import Annotated, Any

from faststream import Context
from faststream.redis import RedisRouter
from faststream.redis.message import RedisMessage

from saltbox_bridge.config import HIERARHY, SETTINGS
from saltbox_bridge.event_bus.messages.sls_messages import ListSlsReposMessage
from saltbox_bridge.event_bus.middlewares import MastersAuthMiddleware
from saltbox_bridge.utils.salt_connector import SaltConnector, get_salt_caller, get_state_apply_error

LOGGER = logging.getLogger(__name__)
Message = Annotated[RedisMessage, Context()]

router = RedisRouter(middlewares=[MastersAuthMiddleware])
router_not_auth = RedisRouter()


@router.subscriber('sync_repos')
async def sync_repos(
    message: ListSlsReposMessage,
    salt_connector: SaltConnector = Context(),  # noqa: B008
) -> Any:
    # TODO (a.karmanov): True async?
    # TODO (a.karmanov): lock file
    # TODO (a.karmanov): Notify Salt.Box Core
    # TODO (a.karmanov): Make message models shared and udpate

    LOGGER.info('Start saync_saltbox_modules')
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
    ret = caller.cmd('state.apply', 'sync_saltbox', pillar=pillar)
    LOGGER.info('End sync_saltbox_modules')
    if (errors := get_state_apply_error(ret)) is not None:
        for msg in errors:
            LOGGER.error(msg)
