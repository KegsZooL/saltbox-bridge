import logging

from salt_box_bridge_service.main import main

__opts__: dict

LOGGER = logging.getLogger(__name__)


def __virtual__() -> bool | tuple[bool, str]:
    if __opts__['__role'] != 'master':
        return False, f'{__name__} runs on master only'
    return True


def start():
    LOGGER.info('Sarting salt.box service as an engine')
    main(salt_opts=__opts__)
