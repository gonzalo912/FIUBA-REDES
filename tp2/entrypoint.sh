#!/bin/bash

service openvswitch-switch start

# Si ya está corriendo, no falla
ovs-vswitchd --pidfile --detach || true

# Link al controlador
rm -f /opt/pox/ext/protorouter.py
ln -s /workspace/protorouter.py /opt/pox/ext/protorouter.py

exec bash