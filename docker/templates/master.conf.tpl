module_dirs:
  - /srv/salt_extmod/
file_root:
  base:
    - /srv/salt/
file_ignore_glob:
  - '*/.git/*'
  - '*.pyc'
  - '*.swp'
auto_accept: true
log_level: '${SALT_MASTER_LOG_LEVEL}'
log_level_logfile: 'quiet'
presence_events: True
engines:
  - salt_box_redis_bridge:
      redis_host: redis-salt
      username: '${REDIS_USERNAME}'
      password: '${REDIS_PASSWORD}'
      ssl: true
      ssl_ca_certs: '/etc/redis/certs/ca.crt'
      # Time to live for job returns and grains (sec)
      expire: 604800
      master_secret: '${MASTER_SECRET}'
  - salt_box_service:
      redis_host: redis-salt
      username: '${REDIS_USERNAME}'
      password: '${REDIS_PASSWORD}'
      ssl: true
      ssl_ca_certs: '/etc/redis/certs/ca.crt'
      # Time to live for job returns and grains (sec)
      expire: 604800
      master_secret: '${MASTER_SECRET}'
schedule:
  salt_box_redis_bridge_cleanup:
    hours: 3
    function: salt_box_redis_bridge.cleanup_expired_jobs
    kwargs:
      # Age of jobs to delete (sec)
      expire: 604800
      redis_host: redis-salt

# vi: syn=yaml
