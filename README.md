# Salt.Box bridge

## Description
Bridge component is a set of additional SaltStack modules to connect Salt
master to Salt.Box.

## Manual installation
0. Get Redis root certificate with command inside `salt-box-compose`:
  ```bash
  sudo docker compose cp redis-salt:/etc/redis/certs/ca.crt ./
  ```
1. Copy files to Salt master you want to connect.
2. Put `*.py` files from (`engines/`)[./engines/] to Salt engines dir e.g.
  `/srv/salt_extmod/engines/`. 
3. Put  `*.py` files from (`runners/`)[./runners/] to Salt runner modules dir
   e.g. `/srv/salt_extmod/runners/`.
4. Install the (`salt_box_bridge_service`)[./salt\_box\_bridge\_service/] module:
  ```bash
  sudo pip3 install `./salt_box_bridge_service/`
  ```
5. Save `ca.crt` from the first step e.g. as `/etc/salt/ssl/redis-ca.crt`


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
  - salt_box_redis_bridge:
## REDIS_HOST is host with deployted salt-box-compose
      redis_host: 'REDIS_HOST'
## REDIS_USERNAME is REDIS_SALT_USERNAME from salt-box-compose `.env` file
      username: 'REDIS_USERNAME'
## REDIS_PASSWORD is in `secrets/redis_salt_password`
      password: 'REDIS_PASSWORD'
      ssl: true
## Where the cert had been saved before
      ssl_ca_certs: '/etc/salt/ssl/redis-ca.crt'
      # Time to live for job returns and grains (sec)
      expire: 604800
## Generate MASTER_SECRET e.g. with `pwgen -sN 1 16` command
      master_secret: 'MASTER_SECRET'
  - salt_box_service:
## REDIS_HOST is host with deployted salt-box-compose
      redis_host: 'REDIS_HOST'
## REDIS_USERNAME is REDIS_SALT_USERNAME from salt-box-compose `.env` file
      username: 'REDIS_USERNAME'
## REDIS_PASSWORD is in `secrets/redis_salt_password`
      password: 'REDIS_PASSWORD'
      ssl: true
## Where the cert had been saved before
      ssl_ca_certs: '/etc/salt/ssl/redis-ca.crt'
      # Time to live for job returns and grains (sec)
      expire: 604800
## The same MASTER_SECRET as in salt_box_redis_bridge_config
      master_secret: 'MASTER_SECRET'

## Strictly recommended to cleanup historical data
schedule:
  salt_box_redis_bridge_cleanup:
    hours: 3
    function: salt_box_redis_bridge.cleanup_expired_jobs
    kwargs:
      # Age of jobs to delete (sec)
      expire: 604800
      redis_host: redis-salt
```

Use `./make_maser_id.sh` helper script to create id with hostname and timestamp
and save it to separate file __instead__ of specifying `salt_master_id` in the
main config manually.
