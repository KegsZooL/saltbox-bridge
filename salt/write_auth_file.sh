#! /bin/sh

set -e

if [ -z "$SALT_API_USER" ]; then
  >&2 echo 'Missing SALT_API_USER value'
  exit 1
fi

echo "$SALT_API_USER:$(cat /run/secrets/salt_api_password)" > /etc/salt/auth.txt
