#! /bin/sh
# shellcheck disable=SC2016
set -e

error() {
  e>&2 echo "$1"
  exit 1
}

SALT_API_PASSWORD="$(cat /run/secrets/salt_api_password)"
REDIS_PASSWORD="$(cat /run/secrets/redis_salt_password)"

[ -z "$SALT_API_USER" ] && error 'Missing SALT_API_USER value'
[ -z "$SALT_API_PASSWORD" ] && error 'Missing SALT_API_PASSWORD value'
[ -z "$REDIS_PASSWORD" ] && error 'Missing REDIS_PASSWORD value'

mkdir --parents /etc/salt/master.d/
echo "${SALT_API_USER}:${SALT_API_PASSWORD}" > /etc/salt/auth.txt
envsubst '$SALT_API_USER' \
  < /root/templates/api.conf.tpl \
  > /etc/salt/master.d/api.conf
envsubst '$REDIS_PASSWORD' \
  < /root/templates/master.conf.tpl \
  > /etc/salt/master.d/master.conf
