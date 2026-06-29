#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel


import argparse


# Por defecto, la topología es como la de abajo
MIN_PRIVATE_IP_HOST_ADDRESS = 2 # No 1, porque queremos que las IPs coincidan con las MAC por simplificación y como el servidor tiene MAC 1, el primer host privado tiene una MAC 2 (e IP 2)
MAX_PRIVATE_IP_HOST_ADDRESS = 253 # No 254 porque esa es la dirección de la interfaz privada del switch
AVAILABLE_PRIVATE_IP_HOST_ADDRESSES = MAX_PRIVATE_IP_HOST_ADDRESS - MIN_PRIVATE_IP_HOST_ADDRESS + 1


#                                      Tráfico Saliente
#
#                                      <---------------
#
#                           Red Pública                Red Privada
#
#
#                              port 1                     port 2
#        ┌───────┐     IP:  200.0.0.254        /\  IP: 192.168.1.254          ┌───────┐
#        │       │     MAC: 00.00.00.aa.aa.aa /  \ MAC:00.00.00.bb.bb.bb      │       │
#        │  h1   ├───────────────────────────/ s1 \───────────────────────────│  h2   │
#        └───────┘                           \    /                           └───────┘
#       /       /                             \  /                           /       /
#      ─────────                               \/                           ─────────
#  IP:  200.0.0.1/24                                                    IP:  192.168.1.2/24
#  DG:  200.0.0.254                                                     DG:  192.168.1.254
#  MAC: 00:00:00:00:00:01                                               MAC: 00:00:00:00:00:02
#


class NATTopo(Topo):
    def __init__(self, n_hosts=1, **opts):
        self.n_hosts = n_hosts
        super(NATTopo, self).__init__(**opts)

    def build(self):
        # Switch
        s1 = self.addSwitch('s1')

        # Servidor publico
        h1 = self.addHost(
            name="h1",
            ip="200.0.0.1/24",
            mac="00:00:00:00:00:01", # Comentar si se quiere random
            defaultRoute="via 200.0.0.254"
        )
        self.addLink(h1, s1)

        # Hosts privados
        for i in range(MIN_PRIVATE_IP_HOST_ADDRESS, MIN_PRIVATE_IP_HOST_ADDRESS + self.n_hosts):
            hi = self.addHost(
                "h" + str(i),
                ip="192.168.1." + str(i) +"/24",
                mac="00:00:00:00:00:" + f"{i:02x}", # Comentar si se quiere random
                defaultRoute="via 192.168.1.254"
            )
            self.addLink(hi, s1)


def run(n_hosts=1):
    topo = NATTopo(n_hosts=n_hosts)
    net = Mininet(topo=topo, controller=RemoteController, link=TCLink)
    net.start()

    # Deshabilita IPv6 en hosts
    for host in net.hosts:
        host.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        host.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        host.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

    # Deshabilita IPv6 en switch
    s1 = net.get('s1')
    s1.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
    s1.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
    s1.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

    CLI(net)
    net.stop()


def get_private_hosts_count():
    parser = argparse.ArgumentParser(description='Run Mininet topology with a specified number of private hosts.')
    parser.add_argument(
        '-ph', '--private-hosts', type=int, default=1,
        help=f'Number of hosts in the private network (1-{AVAILABLE_PRIVATE_IP_HOST_ADDRESSES}, default: 1)'
    )
    args = parser.parse_args()
    
    if not (1 <= args.private_hosts <= AVAILABLE_PRIVATE_IP_HOST_ADDRESSES):
        parser.error(f"The number of private hosts must be between 1 and {AVAILABLE_PRIVATE_IP_HOST_ADDRESSES}.")
    
    return args.private_hosts

if __name__ == '__main__':
    setLogLevel('info')
    n_hosts = get_private_hosts_count()
    run(n_hosts)
