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
  grain='lsb_distrib_id'
) %}

{% if os_family %}
OS family is set:
  grains.present:
    - value: {{ os_family }}
{% endif %}

Dependencies intalled:
  saltutil.sync_modules:
    - refresh: True
{% if grains.kernel.lower() == 'windows' %}
  test.configurable_test_state:
    - result: false
    - changes: false
    - warnings:
      - Installing inventory agent is not supported on Microsoft™ Windows™ based minions for the moment.
      - Please decide to deploy FusionInventory Agent to default location in "Program Files".
    - failhard: true
    - onfail:
      - module: inventory.agent_bin
  module.run:
    - name: inventory.agent_bin
{% else %}
    {% if 'ALT' in grains.get('lsb_distrib_id', '') %}
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
{% endif %}

Inventory:
  module.run:  # MUST be in the single form to get return processed on Bridge
    - name: inventory.get
    - only: ''  # TODO parametrize with a pillar
    - exclude: ''
