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

## Manual installation

> Jun 2025: section needs udpate

0. Get Redis root certificate with command inside `saltbox-compose`:
  ```bash
  sudo docker compose cp redis-salt:/etc/redis/certs/ca.crt ./redis-ca.crt
  ```
1. Copy `saltbox-bridge` files and the `redis-ca.crt` to Salt master you want to connect.
2. Put `*.py` files from [`engines/`](./engines/) to Salt engines dir e.g.
  `/srv/salt_extmod/engines/`. 
3. Put  `*.py` files from [`runners/`](./runners/) to Salt runner modules dir
   e.g. `/srv/salt_extmod/runners/`.
4. Install the [`saltbox_bridge`](./salt\_box\_bridge\_service/) module:
  ```bash
  sudo pip3 install `./saltbox_bridge/`
  ```
5. Put `redis-ca.crt` from the first step e.g. to `/etc/salt/ssl/`


Owner for copied files should be the same as `salt-master` process user
(usually `root`).

Now tune the config of master.
```yaml
# /etc/salt/master

## Unique master identifier in Salt.Box
## Latin letters, digits, underscore, minus and dot
salt_master_id: UNIQUE_NAME

## Where subdirs with bridge modules are
module_dirs:
  - /srv/salt_extmod/

## Accept pubkeys from minions. Turn off to manage manually.
auto_accept: true

## Special minion precense periodic event means the minion is online
presence_events: True

## Set real values
engines:
  - saltbox_delator:
  - saltbox_agent:
ext_pillar:
  - redis_pillar:

## Strictly recommended to cleanup historical data
schedule:
  saltbox_delator_cleanup:
    hours: 3
    function: saltbox_delator.cleanup_expired_jobs
```

Put contents of [`master/states/`](master/states/) directory to __minion__
`file_roots` directory. By default minion roots is `/srv/salt/`, but it is
prefferd to change it to not interfere with master default roots:

```yaml
# /etc/salt/minion on master host

file_roots:
    base:
        - '/srv/salt_master_local/'
```

Put `saltbox` YAML file to `/etc/salt/`:
```yaml
# /etc/salt/saltbox

## Salt.Box config
## File is YAML formatted.

## Redis config
## REDIS_HOST is host with deployed saltbox-compose
redis_host: 'REDIS_HOST'
## REDIS_USERNAME is REDIS_SALT_USERNAME from saltbox-compose `.env` file
redis_username: 'REDIS_USERNAME'
## REDIS_PASSWORD is in `secrets/redis_salt_password`
redis_password: 'REDIS_PASSWORD'
redis_ssl_use: true
## Where the cert had been saved before
redis_ssl_ca_certs: '/etc/salt/ssl/redis-ca.crt'

## Time to live for job returns and grains (sec)
## `null` (with no quotes) to not expire.
## WARNING! `null` value may lead to worse perfomance and intensive storage usage.
expire: 604800

## Salt.Box SLS files and Salt modules obtaining options.
## Address of Salt.Box main server
salt_conf_server: 'saltbox.local'  # CHANGE ME
## Port of Salt.Box main server which sshfs service listen
salt_conf_port: 1022
## SSH user name to access files
salt_conf_user: 'master'
## Path on REMOTE server where files kept
salt_conf_source: '/srv/master/salt/'
## Path on LOCAL server which is in Salt Master `file_root`
salt_conf_destination: '/srv/saltbox_salt/' 

## Settings of files replication from Salt.Box sshfs service
## Replication should be enabled for remote master
sshfs_sync_on: true
## Address of Salt.Box main server to sync FROM
sshfs_server: 'saltbox.local'  # CHANGE ME
## Port of Salt.Box main server which sshfs service listen
sshfs_port: 1022
## SSH user name to access files
sshfs_user: 'saltbox'
## Path on REMOTE server where files kept
sshfs_source: '/srv/sshfs/'
## Path on LOCAL server where files will be placed
sshfs_destination: '/srv/sshfs/'  # CHANGE ME
```

Use `./make_master_id.sh` helper script to create id with hostname and timestamp
and save it to separate file __instead__ of specifying `salt_master_id` in the
main config manually.

SSH daemon should be setup to serve the `SSHFS_DESTINATION` directory and respectful
pillars should be setted to make minions able to get files from their master.
