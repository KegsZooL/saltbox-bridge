from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any, Iterable
from xml.etree import ElementTree

from salt.exceptions import (  # type: ignore[import-untyped]
    CommandExecutionError,
    CommandNotFoundError,
    SaltException,
    SaltInvocationError,
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


def _validate_categories(categories: Iterable[str]) -> Iterable[str]:
    for cat in categories:
        if cat not in CATEGORIES:
            msg = f'Unsupported category {cat}, use available_categories() to check supported'
            raise SaltInvocationError(msg)
    return categories


def _element_to_dict(elem: ElementTree.Element) -> dict[str, Any]:
    return {child.tag.lower(): child.text for child in elem}

def _inventory_to_dict(data: str, categories: Iterable[str] = CATEGORIES) -> dict[str, Any]:
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

    for category in categories:
        parsed[category] = [
            _element_to_dict(s) for s in content.findall(category.upper())
        ]

    return parsed


def get_inventory_cmd() -> list[str] | None:
    """
    Show list of command with args to execute to get inventory data
    """
    for bin, flags in COMMANDS_MAPPING.items():
        if (path := shutil.which(bin)) is not None:
            return [path] + flags
    return None


def get(only: list[str] | None = None, exclude: list[str] | None = None ) -> dict[str, Any]:
    """
    Get inventory data

    only
        list of categories to return. All available if empty.
        See avaliable with `inventory.available_categories`.

    exclude
        Exclude specified categories from return. Affects `only` list.

    CLI Example:

    .. code-block:: bash

        salt '*' inventory.get exclude=['softwares','bios']
    """
    cmd = get_inventory_cmd()
    if only:
        categories = set(_validate_categories(only))
    else:
        categories = set(CATEGORIES)

    if exclude:
        categories -= set(_validate_categories(exclude))

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

    return _inventory_to_dict(result.stdout.decode(), categories=categories)


def available_categories() -> Iterable[str]:
    """
    List supported categories of inventory data
    """
    return CATEGORIES


if __name__ == '__main__':
    import json
    print(json.dumps(get(), indent=4))
