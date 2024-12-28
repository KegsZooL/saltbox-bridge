rest_cherrypy:
  port: 8000
  ssl_crt: /etc/pki/tls/certs/localhost.crt
  ssl_key: /etc/pki/tls/certs/localhost.key

external_auth:
  file:
    ^filename: /etc/salt/auth.txt
    ${SALT_API_USER}:
      - '.*'
      - '@wheel'
      - '@jobs'
      - '@runner'

# True leads to aurh error whith auth modules without acl() #65593
keep_acl_in_token: False

# vi: syn=yaml
