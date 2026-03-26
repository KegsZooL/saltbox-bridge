# Salt.Box bridge

## Description
Bridge component is a set of additional SaltStack modules to connect Salt
master to Salt.Box.

Currently supported salt-master versions:
- 3006.9

## Salt files hierarhy

- `/srv/salt/` — standard directory for user's custom files. In Salt.Box Compose
  it is mounted to a local dir.
- `/srv/saltbox_salt/` is a part of Salt.Box system to replicate states from
packages.
- `/srv/salt_local/` is for local Salt.Box states and modules.
- `/srv/salt_master_local/` is for the Master local minion Salt.Box service states and
modules.
- `/srv/salt_extmod/` is for "external modules". There are some distributed
  with this repository. It is possible to put some custom modules here also.
- `/srv/sshfs/` for files to serve both as `ssh://` and `salt://`.
- `/srv/migrator/` — directory of Salt files related to the migration process, accessible
  via the filebrowser when `FILEBROWSER_MIGRATOR_SOURCE_ENABLED` flag is enabled.

## Manual installation

Refer to [Salt.Box documentation](https://saltbox.pro/docs/next/administration/master_install).
