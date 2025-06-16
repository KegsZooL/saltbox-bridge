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
  chown -R "$(id -u):$(id -g)" "$SALTBOX_BRIDGE_SRC_PATH"
  # `salt-pip` overrides target if not passed and it is not work for editable
  "$PIP_CMD" install --editable "$SALTBOX_BRIDGE_SRC_PATH" --target=''
fi

[ -z "$REDIS_USERNAME" ] && error 'Missing REDIS_USERNAME value'
[ -z "$REDIS_PASSWORD_FILE" ] && error 'Missing REDIS_PASSWORD_FILE value'

REDIS_PASSWORD="$(cat "$REDIS_PASSWORD_FILE")"
export REDIS_PASSWORD

mkdir --parents /etc/salt/master.d/
envsubst '$SALT_MASTER_LOG_LEVEL' \
  < /root/templates/master.conf.tpl \
  > /etc/salt/master.d/master.conf

envsubst '$SALT_MINION_LOG_LEVEL' \
  < /root/templates/minion.conf.tpl \
  > /etc/salt/minion

envsubst '$REDIS_USERNAME $REDIS_PASSWORD' \
  < /root/templates/saltbox.conf.tpl \
  > /etc/salt/saltbox

exec "$@"
