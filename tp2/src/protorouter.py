# Import some POX stuff
from pox.core import core                       # Main POX object
import pox.openflow.libopenflow_01 as of        # OpenFlow 1.0 library
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.tcp import tcp
from pox.lib.packet.udp import udp
from pox.lib.packet.icmp import icmp, echo, TYPE_ECHO_REQUEST, TYPE_ECHO_REPLY


import sys
import os
# ignorar: esto hace que el path de python apunte a donde 
# está el archivo protorouter.py original
# y se puedan importar módulos como arp_handler y nat_handler
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import util.logger as logger
from util.constants import (
    PRIVATE_SUBNET,
    PRIVATE_MASK,
    PRIVATE_IP,
    PUBLIC_IP,
    PUBLIC_MAC,
    PRIVATE_MAC,
    PUBLIC_PORT,
    SUPPORTED_PROTOCOLS,
    ENTRY_TIMEOUT,
)
from handlers.arp_handler import ArpHandler
from handlers.nat_handler import NatHandler
from handlers.icmp_handler import IcmpHandler

import time

class ProtoRouter(object):
    def __init__(self, connection):
        self.connection = connection
        self.arp_handler = ArpHandler()
        self.nat_handler = NatHandler()
        self.icmp_handler = IcmpHandler()
        connection.addListeners(self)

    def _install_flow(self, match, actions):
        fm = of.ofp_flow_mod()
        fm.idle_timeout = ENTRY_TIMEOUT
        for field, value in match.items():
            setattr(fm.match, field, value)
        for action in actions:
            fm.actions.append(action)
        self.connection.send(fm)

    def _resolve_mac(self, ip_addr, event, arp_out_port, arp_src_ip, arp_src_mac):
        mac = self.arp_handler.get_mac(ip_addr)
        if not mac:
            self.arp_handler.enqueue_packet(ip_addr, event)
            self._send_arp_request(target_ip=ip_addr, out_port=arp_out_port, source_ip=arp_src_ip, source_mac=arp_src_mac)
            return None
        return mac

    def _resolve_mac_and_port(self, ip_addr, event, arp_out_port, arp_src_ip, arp_src_mac):
        mac = self.arp_handler.get_mac(ip_addr)
        port = self.arp_handler.get_port(ip_addr)
        if not mac or not port:
            self.arp_handler.enqueue_packet(ip_addr, event)
            self._send_arp_request(target_ip=ip_addr, out_port=arp_out_port, source_ip=arp_src_ip, source_mac=arp_src_mac)
            return None, None
        return mac, port

    def _clear_checksums(self, ip_pkt):
        ip_pkt.csum = None
        ip_pkt.next.csum = None

    def _send_packet(self, packet, src_mac, dst_mac, out_port, log_msg):
        packet.src = src_mac
        packet.dst = dst_mac
        msg = of.ofp_packet_out()
        msg.data = packet.pack()
        msg.actions.append(of.ofp_action_output(port=out_port))
        logger.log_color(logger.CYAN, log_msg)
        self.connection.send(msg)

    def _handle_PacketIn(self, event):
        if not event.parsed.parsed:
            logger.log.warning("[DROP] PacketIn con trama no reconocida. POX no pudo decodificar el paquete.")
            return

        if event.parsed.type == ethernet.ARP_TYPE:
            self.handle_arp(event)
        elif event.parsed.type == ethernet.IP_TYPE:
            self.handle_ip(event)
        else:
            logger.log_color(logger.YELLOW, f"Paquete ignorado: protocolo distinto de IPv4.")

    def _get_transport_fields(self, ip_pkt):
        transport = ip_pkt.next

        if isinstance(transport, tcp):
            return "TCP", transport.srcport, transport.dstport

        if isinstance(transport, udp):
            return "UDP", transport.srcport, transport.dstport
        
        if isinstance(transport, icmp):
            return "ICMP", transport.next.id, transport.next.id

        return None, None, None

    def _send_arp_reply(self, target_ip, target_mac, target_port, source_ip, source_mac):
        msg = self.arp_handler.create_arp_reply(target_ip, target_mac, target_port, source_ip, source_mac)
        logger.log_color(logger.CYAN, f"ARP Reply generado por el controlador: {source_ip} is-at {source_mac} -> {target_ip}")
        self.connection.send(msg)

    def _send_arp_request(self, target_ip, out_port, source_ip, source_mac):
        msg = self.arp_handler.create_arp_request(target_ip, out_port, source_ip, source_mac)
        logger.log_color(logger.CYAN, f"ARP Request generado por el controlador: {source_ip} ({source_mac}) pregunta por {target_ip}")
        self.connection.send(msg)

    def handle_arp(self, event):
        packet = event.parsed
        arp_pkt = packet.payload
        in_port = event.port

        if arp_pkt is None:
            logger.log.warning("[DROP] Trama ARP sin payload válido.")
            return

        sender_ip = arp_pkt.protosrc
        sender_mac = arp_pkt.hwsrc
        target_ip = arp_pkt.protodst

        if arp_pkt.opcode == arp.REQUEST:
            logger.log_color(logger.YELLOW, f"ARP Request recibido: {sender_ip} ({sender_mac}) -> {target_ip}")
        elif arp_pkt.opcode == arp.REPLY:
            logger.log_color(logger.YELLOW, f"ARP Reply recibido: {sender_ip} ({sender_mac}) -> {target_ip}")
        else:
            logger.log_color(logger.YELLOW, f"ARP recibido con opcode no soportado: {arp_pkt.opcode}")

        self.arp_handler.learn_arp_entry(sender_ip, sender_mac, in_port)

        # Desencolar y procesar paquetes que estaban esperando esta MAC
        events_to_resume = self.arp_handler.dequeue_packets(sender_ip)
        for ev in events_to_resume:
            self._handle_PacketIn(ev)

        # ARP entre hosts privados → flood para que el destino/remitente lo reciba
        if sender_ip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK) \
                and target_ip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK) \
                and target_ip != PRIVATE_IP:
            self._send_packet(event.parsed, packet.src, packet.dst, of.OFPP_FLOOD,
                f"ARP flooded: {sender_ip} → {target_ip}")
            return

        if arp_pkt.opcode != arp.REQUEST:
            return

        if target_ip == PUBLIC_IP:
            source_ip = PUBLIC_IP
            source_mac = PUBLIC_MAC
        elif target_ip == PRIVATE_IP:
            source_ip = PRIVATE_IP
            source_mac = PRIVATE_MAC
        else:
            # Si alguien pregunta por una IP que no es nuestra, ignoramos el paquete.
            # (El switch se encargará de forwardearlo si es tráfico L2 normal, o lo ignoramos)
            return
            
        self._send_arp_reply(
            target_ip=sender_ip,
            target_mac=sender_mac,
            target_port=in_port,
            source_ip=source_ip,
            source_mac=source_mac, # Acá es donde el switch/router comparte su MAC address (ya sea de su interfaz pública o privada)
        )

    def handle_ip(self, event):
        packet = event.parsed
        ip_pkt = packet.payload

        logger.log_color(logger.YELLOW, f"RECIBIDO: {ip_pkt.srcip} → {ip_pkt.dstip} | "
            f"MAC: {packet.src} → {packet.dst} | In Port: {event.port}")

        protocol, src_port, dst_port = self._get_transport_fields(ip_pkt)

        if protocol not in SUPPORTED_PROTOCOLS:
            logger.log_color(logger.RED, "Tráfico descartado (No es TCP, UDP ni ICMP)")
            return

        if ip_pkt.srcip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
            if ip_pkt.dstip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
                self._handle_private_to_private(event)
            else:
                self._handle_outgoing(event, protocol, src_port, dst_port)
        else:
            self._handle_incoming(event, protocol, src_port, dst_port)

    def _handle_outgoing(self, event, protocol, src_port, dst_port):
        packet = event.parsed
        ip_pkt = packet.payload

        logger.log_color(logger.GREEN, f"MATCH: {ip_pkt.srcip} pertenece a la red privada {PRIVATE_SUBNET}/{PRIVATE_MASK}")

        target_mac = self._resolve_mac(ip_pkt.dstip, event, PUBLIC_PORT, PUBLIC_IP, PUBLIC_MAC)
        if not target_mac:
            return

        if protocol == "ICMP":
            icmp_entry = self.icmp_handler.create_entry(
                private_ip=ip_pkt.srcip,
                private_id=src_port,
                public_ip=PUBLIC_IP,
            )
            if not icmp_entry:
                logger.log_color(logger.RED, "[DROP] No se pudo crear entrada ICMP")
                return

            public_id = icmp_entry["public_id"]
            ip_pkt.next.next.id = public_id
            ip_pkt.srcip = PUBLIC_IP
            self._clear_checksums(ip_pkt)
            self._send_packet(packet, PUBLIC_MAC, target_mac, PUBLIC_PORT,
                f"ICMP OUT: {ip_pkt.srcip} → {ip_pkt.dstip} | id: {public_id}")
            return

        pat_entry = self.nat_handler.create_pat_entry(
            protocol=protocol,
            private_ip=ip_pkt.srcip,
            private_port=src_port,
            public_ip=PUBLIC_IP,
        )
        if not pat_entry:
            logger.log_color(logger.RED, "[DROP] No se pudo crear entrada PAT")
            return

        public_port = pat_entry["public_port"]

        self._install_flow(
            match={
                "nw_src": ip_pkt.srcip, "nw_dst": ip_pkt.dstip,
                "dl_type": 0x800, "nw_proto": ip_pkt.protocol,
                "tp_src": src_port, "tp_dst": dst_port,
                "in_port": event.port,
            },
            actions=[
                of.ofp_action_nw_addr.set_src(PUBLIC_IP),
                of.ofp_action_tp_port.set_src(public_port),
                of.ofp_action_dl_addr.set_src(PUBLIC_MAC),
                of.ofp_action_dl_addr.set_dst(target_mac),
                of.ofp_action_output(port=PUBLIC_PORT),
            ]
        )

        self._install_flow(
            match={
                "nw_src": ip_pkt.dstip, "nw_dst": PUBLIC_IP,
                "dl_type": 0x800, "nw_proto": ip_pkt.protocol,
                "tp_src": dst_port, "tp_dst": public_port,
                "in_port": PUBLIC_PORT,
            },
            actions=[
                of.ofp_action_nw_addr.set_dst(ip_pkt.srcip),
                of.ofp_action_tp_port.set_dst(src_port),
                of.ofp_action_dl_addr.set_src(PRIVATE_MAC),
                of.ofp_action_dl_addr.set_dst(packet.src),
                of.ofp_action_output(port=event.port),
            ]
        )

        ip_pkt.srcip = PUBLIC_IP
        ip_pkt.next.srcport = public_port
        self._clear_checksums(ip_pkt)
        self._send_packet(packet, PUBLIC_MAC, target_mac, PUBLIC_PORT,
            f"NAT OUT: {ip_pkt.srcip}:{public_port} → {ip_pkt.dstip}:{dst_port} | Out: {PUBLIC_PORT}")

    def _handle_private_to_private(self, event):
        packet = event.parsed
        ip_pkt = packet.payload

        logger.log_color(logger.GREEN, f"PRIV->PRIV: {ip_pkt.srcip} → {ip_pkt.dstip}")

        target_mac, target_port = self._resolve_mac_and_port(
            ip_pkt.dstip, event, of.OFPP_FLOOD, PRIVATE_IP, PRIVATE_MAC)
        if not target_mac:
            return

        self._install_flow(
            match={
                "nw_src": ip_pkt.srcip, "nw_dst": ip_pkt.dstip,
                "dl_type": 0x800,
                "in_port": event.port,
            },
            actions=[
                of.ofp_action_dl_addr.set_src(PRIVATE_MAC),
                of.ofp_action_dl_addr.set_dst(target_mac),
                of.ofp_action_output(port=target_port),
            ]
        )

        self._install_flow(
            match={
                "nw_src": ip_pkt.dstip, "nw_dst": ip_pkt.srcip,
                "dl_type": 0x800,
                "in_port": target_port,
            },
            actions=[
                of.ofp_action_dl_addr.set_src(PRIVATE_MAC),
                of.ofp_action_dl_addr.set_dst(packet.src),
                of.ofp_action_output(port=event.port),
            ]
        )

        self._clear_checksums(ip_pkt)
        self._send_packet(packet, PRIVATE_MAC, target_mac, target_port,
            f"PRIV->PRIV: {ip_pkt.srcip} → {ip_pkt.dstip} | Out Port: {target_port}")

    def _handle_incoming(self, event, protocol, src_port, dst_port):
        packet = event.parsed
        ip_pkt = packet.payload

        logger.log_color(logger.GREEN, f"Tráfico entrante: {ip_pkt.srcip} -> {ip_pkt.dstip}")

        if protocol == "ICMP":
            reverse_icmp_entry = self.icmp_handler.get_reverse_entry(PUBLIC_IP, dst_port)
            if not reverse_icmp_entry:
                logger.log_color(logger.RED, "[DROP] ICMP sin entrada activa")
                return

            private_ip = reverse_icmp_entry["private_ip"]
            private_id = reverse_icmp_entry["private_id"]

            target_mac, target_port = self._resolve_mac_and_port(private_ip, event, of.OFPP_FLOOD, PRIVATE_IP, PRIVATE_MAC)
            if not target_mac:
                return

            ip_pkt.next.next.id = private_id
            ip_pkt.dstip = private_ip
            self._clear_checksums(ip_pkt)
            self._send_packet(packet, PRIVATE_MAC, target_mac, target_port,
                f"ICMP IN: {ip_pkt.srcip} → {private_ip} | id: {private_id}")
            return

        if ip_pkt.dstip != PUBLIC_IP:
            logger.log_color(logger.RED, f"Tráfico entrante descartado (Destino no es la IP pública {PUBLIC_IP})")
            return

        reverse_pat_entry = self.nat_handler.get_reverse_entry(protocol, ip_pkt.dstip, dst_port)
        if not reverse_pat_entry:
            logger.log_color(logger.RED, f"[DROP] No hay conexión PAT activa para {protocol} puerto {dst_port}")
            return

        private_ip = reverse_pat_entry["private_ip"]
        private_port = reverse_pat_entry["private_port"]

        target_mac, target_port = self._resolve_mac_and_port(private_ip, event, of.OFPP_FLOOD, PRIVATE_IP, PRIVATE_MAC)
        if not target_mac:
            return

        self._install_flow(
            match={
                "nw_src": ip_pkt.srcip, "nw_dst": PUBLIC_IP,
                "dl_type": 0x800, "nw_proto": ip_pkt.protocol,
                "tp_src": src_port, "tp_dst": dst_port,
                "in_port": event.port,
            },
            actions=[
                of.ofp_action_nw_addr.set_dst(private_ip),
                of.ofp_action_tp_port.set_dst(private_port),
                of.ofp_action_dl_addr.set_src(PRIVATE_MAC),
                of.ofp_action_dl_addr.set_dst(target_mac),
                of.ofp_action_output(port=target_port),
            ]
        )

        self._install_flow(
            match={
                "nw_src": private_ip, "nw_dst": ip_pkt.srcip,
                "dl_type": 0x800, "nw_proto": ip_pkt.protocol,
                "tp_src": private_port, "tp_dst": src_port,
                "in_port": target_port,
            },
            actions=[
                of.ofp_action_nw_addr.set_src(PUBLIC_IP),
                of.ofp_action_tp_port.set_src(dst_port),
                of.ofp_action_dl_addr.set_src(PUBLIC_MAC),
                of.ofp_action_dl_addr.set_dst(packet.src),
                of.ofp_action_output(port=event.port),
            ]
        )

        ip_pkt.dstip = private_ip
        ip_pkt.next.dstport = private_port
        self._clear_checksums(ip_pkt)
        self._send_packet(packet, PRIVATE_MAC, target_mac, target_port,
            f"NAT IN: {ip_pkt.srcip}:{src_port} → {private_ip}:{private_port} | Out: {target_port}")


def launch():

    def start_switch(event):
        logger.log_color(logger.YELLOW, f"Iniciando ProtoRouter para Switch {event.connection.dpid}")
        ProtoRouter(event.connection)

    core.openflow.addListenerByName("ConnectionUp", start_switch)