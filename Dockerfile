ARG ALPINE_VERSION='3.20'
ARG PYTHON_VERSION='3.10'

# TODO Altlinux branch US49_altlinux
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS salt-base

ARG SALT_VERSION='3006.9'

ARG BUILD_DEPS="gcc g++ autoconf make libffi-dev libgit2-dev"

RUN \
  --mount=type=cache,target=/var/cache/apk/,sharing=locked \
  apk add binutils libgit2 libffi openssl-dev

# pygit2 depends on specific libgit2 version
RUN \
  --mount=type=cache,target=/var/cache/apk/,sharing=locked \
  --mount=type=cache,target=/root/.cache/pip/ \
<<EOF
set -e
apk add $BUILD_DEPS
echo 'cython<3' > /root/constraint.txt
PIP_CONSTRAINT=/root/constraint.txt USE_STATIC_REQUIREMENTS=1 \
  pip3 install --no-build-isolation "salt==${SALT_VERSION}" 'pygit2==1.13.1'
rm /root/constraint.txt
apk del $BUILD_DEPS
EOF

FROM salt-base AS salt-master
LABEL name='salt-box-salt-master'
LABEL version='1.2'
RUN --mount=type=cache,target=/var/cache/apk/,sharing=locked \
  apk add gettext-envsubst
RUN \
  --mount=type=bind,target=/mnt/,readwrite \
  --mount=type=cache,target=/root/.cache/pip/ \
  pip3 install /mnt/
# To avoid error messag on cleanup keys
RUN mkdir --parents /var/cache/salt/master/

COPY docker/config/master_id.conf /etc/salt/master.d/
COPY docker/templates/ /root/templates/

COPY engines /srv/salt_extmod/engines/
COPY runners /srv/salt_extmod/runners/
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/

ENV REDIS_USERNAME=redis
ENV REDIS_PASSWORD_FILE=
ENV SALT_MASTER_LOG_LEVEL=warning
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["salt-master"]
EXPOSE 4505 4506 8000


FROM salt-base AS salt-minion
LABEL name='salt-box-salt-minion'
LABEL version='0.6'
COPY docker/minion/minion.yaml /etc/salt/minion.d/minion.conf
CMD ["/usr/local/bin/salt-minion"]
