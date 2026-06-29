#!/usr/bin/python3

import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI

class MininetTopology(Topo):
    def build(self):
        # Nombres descriptivos para el equipo
        server = self.addHost('server', ip='10.0.0.1/24')
        client = self.addHost('client', ip='10.0.0.2/24')
        
        s1 = self.addSwitch('s1')
        
        # 10% de pérdida como pide el enunciado
        self.addLink(server, s1, cls=TCLink, loss=5)
        self.addLink(client, s1, cls=TCLink, loss=5)

def open_terminals(net):
    """
    Intenta abrir terminales
    Si fallan, Mininet avisará en la consola.
    """
    hosts = [('server', 'SERVIDOR'), ('client', 'CLIENTE')]
    
    # Lista de terminales modernas en orden de preferencia
    terminal_cmds = ['konsole', 'gnome-terminal', 'xfce4-terminal', 'alacritty', 'xterm']
    
    selected_term = 'xterm'
    for term in terminal_cmds:
        if os.system(f'which {term} > /dev/null 2>&1') == 0:
            selected_term = term
            break
    
    print(f"[*] Usando {selected_term} para las ventanas de los hosts...")

    for name, title in hosts:
        node = net.get(name)
        if selected_term == 'konsole':
            node.popen(['konsole', '--title', title, '-e', 'bash'])
        elif selected_term == 'gnome-terminal':
            node.popen(['gnome-terminal', '--title', title, '--', 'bash'])
        elif selected_term == 'xfce4-terminal':
            node.popen(['xfce4-terminal', '--title', title, '-e', 'bash'])
        else:
            # Fallback a xterm si no se encuentra ninguna moderna
            node.popen(['xterm', '-T', title, '-e', 'bash'])

def run_simulation():
    topo = MininetTopology()
    net = Mininet(topo=topo, link=TCLink)
    net.start()
    
    print("\n" + "="*50)
    print(" TOPOLOGÍA GRUPO 5: 10% PACKET LOSS")
    print(" SERVER IP: 10.0.0.1 | CLIENT IP: 10.0.0.2")
    print("="*50 + "\n")
    
    open_terminals(net)
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    try:
        run_simulation()
    except Exception as e:
        print(f"\n[!] Error: {e}")
