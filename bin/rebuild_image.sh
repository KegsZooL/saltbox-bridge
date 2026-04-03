#! /bin/sh

# Rebuild salt-master image locally for dev purposes
# Remember to update SALT_MASTER_IMAGE_TAG in override.env

set -e

tag_ver=local
tag="registry.saltbox.pro/saltbox/saltbox-bridge/salt-master:${tag_ver}"
target='salt-master'
docker build --tag "$tag" --target="$target" .
