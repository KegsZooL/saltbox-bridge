id: saltbox-main-minion
master: localhost
file_client: local
file_roots:
  base:
    - '/srv/salt_master_local/'
log_level: '${SALT_MINION_LOG_LEVEL}'
master_tries: -1
retry_dns: 5
recon_randomize: False
recon_max: 0

# vi: filetype=yaml
