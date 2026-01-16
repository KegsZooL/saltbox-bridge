#! /bin/sh
# shellcheck disable=SC2016
#
set -e
trap '[ $? -eq 0 ] && exit 0 || echo "ERROR on $0 line ${LINENO}"' EXIT


error() {
  >&2 echo "$1"
  exit 1
}

if [ "$SALTBOX_DEV_MODE" = 1 ]; then
  # Update install
  chown -R "$(id -u):$(id -g)" "$SALTBOX_BRIDGE_SRC_PATH"

  # `salt-pip` neets --target='' for editable, but uv does not
  python3 -m uv --no-progress pip install --editable "$SALTBOX_BRIDGE_SRC_PATH"
  python3 -m uv --no-progress pip install --editable "$SALTBOX_BRIDGE_MESSAGES_SRC_PATH"
fi

[ -z "$REDIS_USERNAME" ] && error 'Missing REDIS_USERNAME value'
[ -z "$REDIS_PASSWORD_FILE" ] && error 'Missing REDIS_PASSWORD_FILE value'

REDIS_PASSWORD="$(cat "$REDIS_PASSWORD_FILE")"
export REDIS_PASSWORD

# Initialize volumes from built-in defaults if empty
init_volume_if_empty() {
  local src_dir="$1"
  local dst_dir="$2"
  local marker_flag="${dst_dir}/.saltbox_initialized"

  if [ ! -f "${marker_flag}" ]; then
    echo "Initializing ${dst_dir} from ${src_dir}"

    mkdir -p "${dst_dir}"

    # Copy only if source exists and destination is empty
    if [ -d "${src_dir}" ] && [ -z "$(ls -A "${dst_dir}" 2>/dev/null)" ]; then
      cp -r "${src_dir}"/. "${dst_dir}/"
      echo "Copied content to ${dst_dir}"
    fi

    touch "${marker_flag}"
    echo "Marked ${dst_dir} as initialized"
  else
    echo "Volume ${dst_dir} already initialized, skipping"
  fi
}
init_volume_if_empty "/opt/saltbox/salt_extmod" "/srv/salt_extmod"
init_volume_if_empty "/opt/saltbox/salt_local" "/srv/salt_local"
init_volume_if_empty "/opt/saltbox/salt_master_local" "/srv/salt_master_local"
mkdir -p /srv/saltbox_salt

# Generate GPG keys if missing
/usr/local/bin/gen_gpg.sh

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

echo "${0} args to eval: ${*}"
exec "$@"
