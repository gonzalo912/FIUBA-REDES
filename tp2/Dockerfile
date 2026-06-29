FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    python3 \
    git \
    iproute2 \
    iputils-ping \
    net-tools \
    tcpdump \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/noxrepo/pox.git /opt/pox

WORKDIR /workspace

CMD ["/bin/bash"]

## cd tp2
## docker compose build
## docker compose up -d
## 
## 
## docker exec -it tp2-mininet bash
## service openvswitch-switch start
## ovs-vswitchd --pidfile --detach


## TERMINAL 1 

# docker exec -it tp2-mininet bash

# cd /workspace
# python3 topo.py

## TERMINAL 2

# docker exec -it tp2-mininet bash

# cp /workspace/protorouter.py /opt/pox/ext/

# cd /opt/pox
# python3 pox.py log.level --DEBUG protorouter

## SI SE ROMPE ALGO 

# mn -c
# ovs-vsctl --if-exists del-br s1