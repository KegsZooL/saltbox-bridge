import logging
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)

SSH_DIR_MODE = 0o700


def ensure_ssh_key(privkey_file: Path, key_type: str = 'ed25519') -> None:
    """
    Ensure a pair of private and public key files exists.
    """
    if privkey_file.exists():
        return

    directory = privkey_file.parent

    if not directory.exists():
        LOGGER.info('Creating directory for SSH key: %s', directory)
        directory.mkdir(parents=True)
    directory.chmod(SSH_DIR_MODE)

    cmd = ['ssh-keygen', '-t', key_type, '-N', '', '-f', str(privkey_file)]
    subprocess.run(cmd, check=True)

    LOGGER.info('SSH key generated: %s', privkey_file)
