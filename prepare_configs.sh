#! /bin/sh
# shellcheck disable=SC2016
#
set -e
trap '[ $? -eq 0 ] && exit 0 || echo "ERROR on $0 line ${LINENO}"' EXIT

error() {
  >&2 echo "$1"
  exit 1
}

[ -z "$SALT_API_USER" ] && error 'Missing SALT_API_USER value'
[ -z "$SALT_API_PASSWORD_FILE" ] && error 'Missing SALT_API_PASSWORD_FILE value'
[ -z "$REDIS_USERNAME" ] && error 'Missing REDIS_USERNAME value'
[ -z "$REDIS_PASSWORD_FILE" ] && error 'Missing REDIS_PASSWORD_FILE value'

salt_api_password="$(cat "$SALT_API_PASSWORD_FILE")"
# shellcheck disable=SC2034
redis_password="$(cat "$REDIS_PASSWORD_FILE")"

mkdir --parents /etc/salt/master.d/
echo "${SALT_API_USER}:${salt_api_password}" > /etc/salt/auth.txt
envsubst '$SALT_API_USER' \
  < /root/templates/api.conf.tpl \
  > /etc/salt/master.d/api.conf
envsubst '$REDIS_USERNAME $redis_password' \
  < /root/templates/master.conf.tpl \
  > /etc/salt/master.d/master.conf
