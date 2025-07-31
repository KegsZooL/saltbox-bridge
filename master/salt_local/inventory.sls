{% set agent = 'fusioninventory-agent' %}

Dependencies intalled:
    saltutil.sync_modules:
        - refresh: True
{% if not grains['os'].startswith('ALT ') %}
    pkg.installed:
        - name: {{ agent }}
{% else %}
{# FIXME: Write pkg module for ALT 乁[ ° ᴥ ° ]ㄏ  #}
    cmd.run:
      - name: |
          set -e
          command -v "{{ agent }}" && exit 0 || true
          apt-get update
          apt-get install "{{ agent }}"
{% endif %}

Inventory:
    module.run:
        - name: inventory.get
