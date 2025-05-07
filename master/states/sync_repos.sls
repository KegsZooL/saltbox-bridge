update_conf:
  file.managed:
    - name: '/etc/salt/master.d/gitfs.conf'
    - source:
      - 'salt://files/gitfs.conf.jinja'
    - template: jinja
  cmd.run:
    - name: 'salt-run fileserver.update gitfs'
