import logging
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def ensure_ssh_key(privkey_file: Path, key_type: str = 'ed25519') -> None:
    """
    Ensure a pair of private and public key files exists.

    Directory of privkey_file must exists.
    """
    if privkey_file.exists():
        return

    cmd = ['ssh-keygen', '-t', key_type, '-N', '', '-f', str(privkey_file)]
    subprocess.run(cmd, stdin=subprocess.DEVNULL, check=True)

    LOGGER.info('SSH key generated: %s', privkey_file)
