{% set agent = salt['grains.filter_by'](
  {
    'default': 'fusioninventory-agent',
    'RED*':    'ocsinventory-agent'
  },
  grain='lsb_distrib_id',
  default='default'
) %}

{% set os_family = salt['grains.filter_by'](
  {
    'Astra*': 'Debian',
    'RED*':   'RedHat'
  },
  grain='os_family'
) %}

{% if os_family %}
OS family is set:
  grains.present:
    - value: {{ os_family }}
{% endif %}

Dependencies intalled:
  saltutil.sync_modules:
    - refresh: True
{% if 'ALT' in grains.lsb_distrib_id %}
{# FIXME: Write pkg module for ALT 乁[ ° ᴥ ° ]ㄏ  #}
  cmd.run:
    - names:
      - apt-get update
      - apt-get install -y {{ agent }}
{% else %}
  pkg.installed:
    - name: {{ agent }}
    - refresh: True
{% endif %}
    - unless: command -v {{ agent }}

Inventory:
  module.run:
    - name: inventory.get
