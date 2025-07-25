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

COMMANDS_MAPPING = {
    'fusioninventory-agent': ['--scan-homedirs', '--local', '-'],
    'ocsinventory-agent': ['--scan-homedirs', '--stdout'],
}

# FusionInventory has also:
#   - 'envs'
#   - 'operatingsystem' (has nested TZ)
#   - 'processes'
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


def get_inventory_cmd() -> list[str] | None:
    for bin, flags in COMMANDS_MAPPING.items():
        if (path := shutil.which(bin)) is not None:
            return [path] + flags
    return None



# TODO (a.karmanov) :: US372 :: Categories
def get() -> dict[str, Any]:
    cmd = get_inventory_cmd()
    if cmd is None:
        agents = tuple(COMMANDS_MAPPING.keys())
        msg = f'Not found compatible inventory agent {agents}'
        raise CommandNotFoundError(msg)
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
