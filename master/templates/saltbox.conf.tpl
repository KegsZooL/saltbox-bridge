# Salt.Box config
# File has env-file format.

# Redis conf:
REDIS_HOST='redis-salt'
REDIS_USERNAME='${REDIS_USERNAME}'
REDIS_PASSWORD='${REDIS_PASSWORD}'
REDIS_SSL_USE=True
REDIS_SSL_CA_CERTS='/etc/redis/certs/ca.crt'

# Salt.box bridge conf:
# Time to live for job returns and grains (sec)
EXPIRE=604800
MASTER_SECRET='${MASTER_SECRET}'

GITFS_SERVER=sshfs
GITFS_PORT=1022
GITFS_PRIVKEY='/root/.ssh/saltbox_ed25519'
GITFS_PUBKEY='/root/.ssh/saltbox_ed25519.pub'

SSHFS_SYNC_ON=False  # Should be True for remote master
