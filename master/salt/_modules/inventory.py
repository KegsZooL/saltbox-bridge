import logging
import shutil
import subprocess
from typing import Any
from xml.etree import ElementTree

from salt.exceptions import (  # type: ignore[import-untyped]
    CommandExecutionError,
    CommandNotFoundError,
    SaltException,
)

logger = logging.getLogger(__name__)

BIN_NAMES = ('fusioninventory-agent', 'ocsinventory-agent')
CATEGORIES = (
    'batteries',
    'bios',
    'controllers',
    'cpus',
    'drives',
    'hardware',
    'inputs',
    'local_groups',
    'local_users',
    'networks',
    'ports',
    'softwares',
    'sounds',
    'storages',
    'users',
    'videos',
    'virtualmachines',
)


def element_to_dict(elem: ElementTree.Element) -> dict[str, Any]:
    return {child.tag.lower(): child.text for child in elem}

def inventory_to_dict(data: str) -> dict[str, Any]:
    parsed: dict[str, Any] = { }

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as err:
        raise SaltException(err) from err

    xpath = 'CONTENT'
    content = root.find(xpath)
    if content is None:
        msg = f'Not found {xpath} tag in agent output'
        raise SaltException(msg)

    for category in CATEGORIES:
        parsed[category] = [
            element_to_dict(s) for s in content.findall(category.upper())
        ]

    return parsed


def get_inventory_agent() -> str | None:
    for bin in BIN_NAMES:
        if (path := shutil.which(bin)) is not None:
            return path
    return None



def get() -> dict[str, Any]:
    inv_agent = get_inventory_agent()
    if inv_agent is None:
        msg = f'Not found compatible inventory agent {BIN_NAMES}'
        raise CommandNotFoundError(msg)
    cmd = [inv_agent, '--stdout']
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as err:
        cmd_str = ' '.join(cmd)
        logger.error('Command failed: "%s", stderr follows', cmd_str)
        for line in err.stderr.decode().splitlines():
            logger.error(line)
        msg = f'Command failed: "{cmd_str}"'
        raise CommandExecutionError(msg) from None
    return inventory_to_dict(result.stdout.decode())


if __name__ == '__main__':
    import json
    print(json.dumps(get(), indent=4))
