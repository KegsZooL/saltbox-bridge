#! /bin/sh
set -e

conf_file=/etc/salt/master.d/master_id.conf

if [ ! -f "$conf_file" ]; then
  master_id="$(hostnamectl hostname)-$(date +%s)"
  mkdir --parent "$(dirname "$conf_file")"
  echo "salt_box_master_id: $master_id" > "$conf_file"
  echo "Set salt_box_master_id=${master_id}"
else
  1>&2 echo "${conf_file} already exists"
  exit 1
fi
