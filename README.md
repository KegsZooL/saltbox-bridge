# Salt.Box Bridge

## Description
Bridge component is a set of additional SaltStack modules to connect Salt
master to Salt.Box.

Currently supported salt-master versions:
- 3007.13

## Salt files hierarhy

- `/srv/salt_custom/` is for user's custom files managed with Salt.Box File
  Browser.
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

## Installing a secondary Salt Master

The [`bin/install_master.sh`](./bin/install_master.sh) script installs Salt
and connects a new, independent `salt-master` to SaltBox via Redis. Use it to
attach a master running on its own host so it shares job data with the main SaltBox instance,
without that host's minion being managed by SaltBox master.

For a fully manual, step-by-step walkthrough of the same process see the
[Salt.Box user documentation](https://saltbox.pro/docs/next/administration/master_install).

### Requirements

- A host with network access to the SaltBox Redis instance by **IP address**
  (hostnames are not accepted by the script's prompts) and its port (`6379`
  by default).
- The `redis-ca.crt` authority certificate issued by the SaltBox instance.
  Obtain it from the SaltBox side with
  [Salt.Box Compose](https://dev.saltbox.pro/saltbox/saltbox-compose), e.g.:

  ```bash
  sudo ./bin/sb-compose.sh cp redis-salt:/etc/redis/certs/ca.crt ./redis-ca.crt
  ```

> **ATTENTION!** The script must be run as root. It installs system packages,
> writes to `/etc/salt/`, `/etc/apt/`, and enables the `salt-master` systemd
> service.

### Quick start

The script is self-contained and can be copied on its own to the target
host — it clones the rest of `saltbox-bridge` itself, into a `saltbox-bridge/`
directory next to its own location:

```bash
sudo ./bin/install_master.sh
```

Use `--en_locale` or `--ru_locale` to select the language of interactive
prompts and log messages (Russian is the default). Use `-h`/`--help` to print
the full option list and a summary of what the script does.

```bash
sudo ./bin/install_master.sh --en_locale
```

### What it does

1. Installs the `redis-ca.crt` certificate (auto-detected next to the script,
   or at a path you provide) to `/etc/salt/ssl/redis-ca.crt`.
2. Checks connectivity to the SaltBox Redis instance at the IP address and
   port you provide.
3. Installs required system packages (`curl`, `git`, `rsync`, `gettext`,
   etc.).
4. Installs Salt from the official APT repository.
5. Creates the [Salt files hierarchy](#salt-files-hierarhy) directories.
6. Clones or updates the [`saltbox-bridge`](https://dev.saltbox.pro/saltbox/saltbox-bridge)
   repository next to the script.
7. Syncs Bridge files into the Salt directories above and installs the Bridge
   Python package.
8. Renders `/etc/salt/master`, `/etc/salt/minion`, and `/etc/salt/saltbox`
   from the Bridge [`master/templates/`](./master/templates) files, filled in
   with the SaltBox connection details.
9. Enables and restarts the `salt-master` service.
10. Disables `salt-minion`, since a secondary master does not run its own minion.

### Interactive prompts

During the run you will be asked to:

- provide the `redis-ca.crt` certificate — either let the script search the
  current directory automatically, or specify a path;
- provide the SaltBox IP address and Redis port;
- choose a Salt master ID (defaults to `master-<timestamp>`) and a log level
  for the master and the minion, selected separately on a `0`–`9` scale (see
  [Salt logging
  levels](https://docs.saltproject.io/en/latest/ref/configuration/logging/index.html));
  default is `1` (`info`);
- provide the Redis username (default `redis`) and password used by the
  `saltbox` config.

> **NOTE:** If a local copy of `saltbox-bridge` already exists next to the
> script, you will be asked whether to reuse it or re-clone. Re-cloning
> **PERMANENTLY DELETES** the local copy, and you will be warned separately
> if it has uncommitted changes.

### Re-running the script

**The script is safe to re-run**: package installation and directory creation are
idempotent, and configs are fully re-rendered from the Bridge templates each
time.

Re-running is the **recommended** way to pick up updated Bridge templates
or to change the master ID, log levels, or Redis credentials.
