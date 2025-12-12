#! /bin/sh
# shellcheck disable=SC2016
#
set -e

generate_gpg_if_missing() {
  if ! command -v gpg >/dev/null 2>&1; then
    echo "gpg not installed, skipping GPG key generation"
    return 0
  fi

  GPG_DIR="/etc/salt/gpgkeys"
  BATCH_FILE="/root/templates/gpg_key_params.conf"

  if [ -f "$GPG_DIR" ] && [ ! -d "$GPG_DIR" ]; then
    echo "Path $GPG_DIR exists and is not a directory" >&2
    return 1
  fi

  if [ -d "$GPG_DIR" ] && gpg --homedir "$GPG_DIR" --list-keys >/dev/null 2>&1; then
    echo "GPG keys already present in $GPG_DIR, skipping generation."
    return 0
  fi

  echo "Generating GPG key for pillar encryption..."
  mkdir -p "$GPG_DIR"
  chmod 700 "$GPG_DIR"

  if ! gpg --homedir "$GPG_DIR" --batch --gen-key "$BATCH_FILE" >/dev/null 2>&1; then
    echo "GPG key generation failed" >&2
    return 1
  fi

  GPG_KEY_ID=$(gpg --homedir "$GPG_DIR" --list-keys --with-colons | awk -F: '/^pub/ {print $5; exit}')
  if [ -z "$GPG_KEY_ID" ]; then
    echo "Failed to obtain generated GPG key id" >&2
    return 1
  fi

  PUB_OUT="$GPG_DIR/saltBox.gpg"
  gpg --homedir "$GPG_DIR" --armor --export "$GPG_KEY_ID" > "$PUB_OUT"
  chmod 600 "$PUB_OUT" || true

  echo "GPG key generated in $GPG_DIR and public key exported to $PUB_OUT"
}

generate_gpg_if_missing
