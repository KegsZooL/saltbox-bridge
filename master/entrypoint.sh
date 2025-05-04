#! /bin/sh
# shellcheck disable=SC2016
#
set -e

error() {
  >&2 echo "$1"
  exit 1
}

if [ "$SALT_BOX_DEV_MODE" = 1 ]; then
  # Update install
  chown -R "$(id -u):$(id -g)" "$SALT_BOX_BRIDGE_SERVICE_SRC_PATH"
  pip3 install --editable "$SALT_BOX_BRIDGE_SERVICE_SRC_PATH"
fi

[ -z "$REDIS_USERNAME" ] && error 'Missing REDIS_USERNAME value'
[ -z "$REDIS_PASSWORD_FILE" ] && error 'Missing REDIS_PASSWORD_FILE value'
[ -z "$MASTER_SECRET_FILE" ] && error 'Missing $MASTER_SECRET_FILE value'

REDIS_PASSWORD="$(cat "$REDIS_PASSWORD_FILE")"
export REDIS_PASSWORD

MASTER_SECRET="$(cat "$MASTER_SECRET_FILE")"
export MASTER_SECRET

mkdir --parents /etc/salt/master.d/
envsubst '$SALT_MASTER_LOG_LEVEL' \
  < /root/templates/master.conf.tpl \
  > /etc/salt/master.d/master.conf

envsubst '$SALT_MINION_LOG_LEVEL' \
  < /root/templates/minion.conf.tpl \
  > /etc/salt/minion

envsubst '$REDIS_USERNAME $REDIS_PASSWORD $MASTER_SECRET' \
  < /root/templates/salt_box.conf.tpl \
  > /etc/salt/salt_box.conf

exec "$@"
