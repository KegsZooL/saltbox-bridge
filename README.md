# salt.box bridge

Bridge component is an additional Salt modules set to be connected with the
whole salt.box system.

Modules need to be placed at respective Salt paths. Some modules requires
some salt-master configuration.

Set `salt_box_master_id` option in master config. The value must be uniq for
salt.box installation. Use `./make_maser_id.sh` helper script to create id with
hostname and timestamp.
