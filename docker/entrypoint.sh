#! /bin/sh
# shellcheck disable=SC2016
#
set -e
trap '[ $? -eq 0 ] && exit 0 || echo "ERROR on $0 line ${LINENO}"' EXIT

error() {
  >&2 echo "$1"
  exit 1
}

[ -z "$REDIS_USERNAME" ] && error 'Missing REDIS_USERNAME value'
[ -z "$REDIS_PASSWORD_FILE" ] && error 'Missing REDIS_PASSWORD_FILE value'

REDIS_PASSWORD="$(cat "$REDIS_PASSWORD_FILE")"
export REDIS_PASSWORD

mkdir --parents /etc/salt/master.d/
envsubst '$SALT_MASTER_LOG_LEVEL $REDIS_USERNAME $REDIS_PASSWORD' \
  < /root/templates/master.conf.tpl \
  > /etc/salt/master.d/master.conf

exec "$@"
