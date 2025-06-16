{% set salt_src = pillar.get('salt_conf_source', '/srv/master/salt/') %}
{% set salt_dst = pillar.get('salt_conf_destination', '/srv/saltbox-salt/') %}
{%- set ssh_dir = pillar.get('ssh_dir', '/var/lib/saltbox-bridge/ssh/') %}

{% set ssh_conf = ssh_dir + '/ssh.conf' %}

update_ssh_config:
  file.managed:
    - name: {{ ssh_conf | yaml_squote }}
    - source:
      - 'salt://files/ssh.conf.jinja'
    - template: jinja
    - makedirs: yes

sync_salt:
  rsync.synchronized:
    - name: {{ salt_dst | yaml_squote }}
    - source: {{ ('saltbox-salt-conf:' + salt_src) | yaml_squote }}
    - prepare: yes  # Create destination dir
    - delete: yes  # Purge unexisted on source
    - force: yes  # Delete non-empty dirs
    - additional_opts:
      - '-e'
      - "ssh -F '{{ ssh_conf }}'"

{% if pillar.get('sshfs_sync_on', True) %}
  {% set sshfs_src = pillar.get('sshfs_source', '/srv/sshfs/') %}
  {% set sshfs_dst = pillar.get('sshfs_destination', '/srv/sshfs/') %}

sync_sshfs:
  rsync.synchronized:
    - name: {{ sshfs_dst | yaml_squote }}
    - source: {{ ('saltbox-sshfs:' + sshfs_src) | yaml_squote }}
    - prepare: yes  # Create destination dir
    - delete: yes  # Purge unexisted on source
    - force: yes  # Delete non-empty dirs
    - additional_opts:
      - '-e'
      - "ssh -F '{{ ssh_conf }}'"
{%- endif %}

#update_fileserver:
#  cmd.run:
#    - name: 'salt-run fileserver.update gitfs'
