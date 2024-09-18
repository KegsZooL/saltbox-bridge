ARG ALPINE_VERSION='3.18'
ARG PYTHON_VERSION='3.10'

FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS salt-base

ARG SALT_VERSION='3006.7'

ARG BUILD_DEPS="gcc g++ autoconf make libffi-dev libgit2-dev"

RUN --mount=type=cache,target=/var/cache/apk/,sharing=locked <<EOF
set -e
apk add binutils libgit2 libffi openssl-dev
addgroup -g 450 -S salt && adduser -s /bin/sh -SD -G salt salt
mkdir -p /etc/pki /etc/salt/pki /etc/salt/minion.d/ /etc/salt/master.d \
    /etc/salt/proxy.d /var/cache/salt /var/log/salt /var/run/salt
chmod -R 2775 /etc/pki /etc/salt /var/cache/salt /var/log/salt /var/run/salt
chgrp -R salt /etc/pki /etc/salt /var/cache/salt /var/log/salt /var/run/salt
EOF

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
su - salt -c 'salt-run salt.cmd tls.create_self_signed_cert'
EOF


FROM alpine:${ALPINE_VERSION} AS envsubstr
ARG SALT_API_USER
RUN --mount=type=cache,target=/var/cache/apk/,sharing=locked apk add gettext
RUN --mount=type=bind,target=/mnt/ \
  envsubst '$SALT_API_USER' < /mnt/config/api.conf.tpl > /root/api.conf


FROM salt-base AS salt-master
LABEL name='fastms-salt-master'
LABEL version='0.3'
RUN \
  --mount=type=bind,target=/mnt/ \
  --mount=type=cache,target=/root/.cache/pip/ \
  pip3 install --upgrade -r /mnt/requirements.txt
COPY config/master.conf config/netapi.conf /etc/salt/master.d/
COPY --from=envsubstr /root/api.conf /etc/salt/master.d/

COPY engines /srv/salt_extmod/engines/
COPY runners /srv/salt_extmod/runners/
COPY write_auth_file.sh /usr/local/bin/
COPY supervisor.conf /etc/

ENV SALT_MASTER_LOG_LEVEL=warning SALT_API_LOG_LEVEL=info
CMD ["/usr/local/bin/supervisord", "--configuration", "/etc/supervisor.conf"]
EXPOSE 4505 4506 8000


FROM salt-base AS salt-minion
LABEL name='fastms-salt-minion'
LABEL version='0.2'
COPY ./config/minion.yaml /etc/salt/minion.d/minion.conf
CMD ["/usr/local/bin/salt-minion"]
