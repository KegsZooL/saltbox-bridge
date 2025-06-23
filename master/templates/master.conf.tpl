module_dirs:
  - /srv/salt_extmod/
file_roots:
  base:
    - /srv/salt/
    - /srv/saltbox_salt/
file_ignore_glob:
  - '*/.git/*'
  - '*.pyc'
  - '*.swp'
auto_accept: true
log_level: '${SALT_MASTER_LOG_LEVEL}'
log_level_logfile: 'quiet'
presence_events: True
engines:
  - saltbox_delator: {}
  - saltbox_agent: {}
ext_pillar:
  - redis_pillar:
      salt_box_env_file: '/etc/salt/salt_box.d/.env'
schedule:
  saltbox_delator_cleanup:
    hours: 3
    function: saltbox_delator.cleanup_expired_jobs

# vi: syn=yaml
