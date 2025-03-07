ARG ALPINE_VERSION='3.18'
ARG PYTHON_VERSION='3.10'

# TODO Altlinux
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS salt-base

ARG SALT_VERSION='3006.7'

ARG BUILD_DEPS="gcc g++ autoconf make libffi-dev libgit2-dev"

RUN \
  --mount=type=cache,target=/var/cache/apk/,sharing=locked \
  apk add binutils libgit2 libffi openssl-dev

RUN \
  --mount=type=cache,target=/var/cache/apk/,sharing=locked \
  --mount=type=cache,target=/root/.cache/pip/ \
<<EOF
set -e
echo 'cython<3' > /root/constraint.txt
apk add $BUILD_DEPS
PIP_CONSTRAINT=/root/constraint.txt USE_STATIC_REQUIREMENTS=1 \
    pip3 install --no-build-isolation \
    pyOpenSSL "salt==${SALT_VERSION}" 'pygit2<1.12'
rm /root/constraint.txt
apk del $BUILD_DEPS
EOF

FROM salt-base AS salt-master
LABEL name='salt-box-salt-master'
LABEL version='1.1'
RUN --mount=type=cache,target=/var/cache/apk/,sharing=locked \
  apk add gettext-envsubst
RUN \
  --mount=type=bind,target=/mnt/,readwrite \
  --mount=type=cache,target=/root/.cache/pip/ \
  pip3 install /mnt/

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
LABEL version='0.5'
COPY docker/minion/minion.yaml /etc/salt/minion.d/minion.conf
CMD ["/usr/local/bin/salt-minion"]
