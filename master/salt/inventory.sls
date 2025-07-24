Dependencies intalled:
# TODO ALT
    saltutil.sync_modules:
        - refresh: True
    pkg.installed:
        - fusioninventory-agent

Inventory:
    module.run:
        - name: inventory.get
