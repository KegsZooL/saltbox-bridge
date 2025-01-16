user: salt
module_dirs:
  - /srv/salt_extmod/
auto_accept: true
engines:
  - salt_box_redis_bridge:
      redis_host: redis-salt
      username: '${REDIS_USERNAME}'
      password: '${REDIS_PASSWORD}'
      ssl: true
      ssl_ca_certs: '/etc/redis/certs/ca.crt'
      # Time to live for job returns and grains (sec)
      expire: 604800
  - salt_box_service: {}
schedule:
  salt_box_redis_bridge_cleanup:
    hours: 3
    function: salt_box_redis_bridge.cleanup_expired_jobs
    kwargs:
      # Age of jobs to delete (sec)
      expire: 604800
      redis_host: redis-salt

# vi: syn=yaml
