# Salt.Box bridge

## Description
Bridge component is a set of additional SaltStack modules to connect Salt
master to Salt.Box.

Currently supported salt-master versions:
- 3006.9

## Manual installation
0. Get Redis root certificate with command inside `salt-box-compose`:
  ```bash
  sudo docker compose cp redis-salt:/etc/redis/certs/ca.crt ./redis-ca.crt
  ```
1. Copy `salt-box-bridge` files and the `redis-ca.crt` to Salt master you want to connect.
2. Put `*.py` files from [`engines/`](./engines/) to Salt engines dir e.g.
  `/srv/salt_extmod/engines/`. 
3. Put  `*.py` files from [`runners/`](./runners/) to Salt runner modules dir
   e.g. `/srv/salt_extmod/runners/`.
4. Install the [`salt_box_bridge_service`](./salt\_box\_bridge\_service/) module:
  ```bash
  sudo pip3 install `./salt_box_bridge_service/`
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
  - salt_box_redis_bridge:
      # Path to .env file
      salt_box_env_file: '/etc/salt/salt_box.d/.env'
  - salt_box_service:
      # Path to .env file
      salt_box_env_file: '/etc/salt/salt_box.d/.env'

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

Put `.env` file to `/etc/salt/salt_box.d/`:
```
# /etc/salt/salt_box.d/.env

# Redis conf:

## REDIS_HOST is host with deployted salt-box-compose
REDIS_HOST="REDIS_HOST"
## REDIS_USERNAME is REDIS_SALT_USERNAME from salt-box-compose `.env` file
REDIS_USERNAME="REDIS_USERNAME"
## REDIS_PASSWORD is in `secrets/redis_salt_password`
REDIS_PASSWORD="REDIS_PASSWORD"
REDIS_SSL_USE=True
## Where the cert had been saved before
REDIS_SSL_CA_CERTS="/etc/salt/ssl/redis-ca.crt"

# Salt.box bridge conf:

# Time to live for job returns and grains (sec)
EXPIRE=604800
## The same MASTER_SECRET as in salt_box_redis_bridge_config
MASTER_SECRET="MASTER_SECRET"
```

Use `./make_maser_id.sh` helper script to create id with hostname and timestamp
and save it to separate file __instead__ of specifying `salt_master_id` in the
main config manually.
