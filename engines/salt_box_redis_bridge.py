"""
Salt master config:

    module_dirs:
      - /srv/salt_extmod/  # Custom modules' dir for the master
                           # better not to mix with /srv/salt/

    engines:
      - salt_box_redis_bridge:  # start() args following
          host: localhost  # Redis instance

Put the module to /srv/salt_extmod/engines/

Restart salt-master. Log and exceptions will be in salt-master log.
"""

from __future__ import annotations

import logging
import os

from salt_box_bridge_service.bridge import start as start_bridge
from salt_box_bridge_service.config import SETTINGS

__opts__: dict
__salt__: dict

LOGGER = logging.getLogger(__name__)


def __virtual__() -> bool | tuple[bool, str]:  # noqa: N807
    if __opts__['__role'] != 'master':  # noqa: F821
        return False, f'{__name__} runs on master only'
    return True


def start(salt_box_env_file: str) -> None:
    """
    Start a salt.box redis bridge.

    Args:
        salt_box_env_file: path to salt.box env file
    """

    os.environ['SALT_BOX_ENV_FILE'] = salt_box_env_file
    SETTINGS.__init__(_env_file=salt_box_env_file)

    LOGGER.info('Starting salt.box redis bridge as an engine')
    start_bridge(salt_opts=__opts__)  # noqa: F821
