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
  - salt_box_service:
ext_pillar:
  - redis_pillar:
      salt_box_env_file: '/etc/salt/salt_box.d/.env'
schedule:
  salt_box_redis_bridge_cleanup:
    hours: 3
    function: salt_box_redis_bridge.cleanup_expired_jobs
    kwargs:
      # Age of jobs to delete (sec)
      expire: 604800
      redis_host: redis-salt

# vi: syn=yaml
