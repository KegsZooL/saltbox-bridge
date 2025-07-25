Dependencies intalled:
# TODO (a.karmanov) :: US372 :: ALTLinux
    saltutil.sync_modules:
        - refresh: True
    pkg.installed:
        - name: fusioninventory-agent

Inventory:
    module.run:
        - name: inventory.get
