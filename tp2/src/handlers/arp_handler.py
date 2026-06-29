import time
import util.logger as logger
from util.constants import ENTRY_TIMEOUT
from pox.lib.addresses import EthAddr
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet
import pox.openflow.libopenflow_01 as of

class ArpHandler():
    def __init__(self):
        self.arp_table = {}
        self.waiting_queue = {}


    def _build_eth(self, src_mac, dst_mac, payload):
        eth = ethernet()
        eth.type = ethernet.ARP_TYPE
        eth.src = src_mac
        eth.dst = dst_mac
        eth.payload = payload
        return eth
    
    def _build_arp(self, opcode, source_ip, source_mac, target_ip, target_mac):
        pkt = arp()
        pkt.hwtype = arp.HW_TYPE_ETHERNET
        pkt.prototype = ethernet.IP_TYPE
        pkt.hwlen = 6
        pkt.protolen = 4
        pkt.opcode = opcode
        pkt.hwsrc = source_mac
        pkt.protosrc = source_ip
        pkt.hwdst = target_mac
        pkt.protodst = target_ip
        return pkt

    def _build_packet_out(self, packet, out_port):
        msg = of.ofp_packet_out()
        msg.data = packet.pack()
        msg.actions.append(of.ofp_action_output(port=out_port))
        return msg

    def enqueue_packet(self, ip_addr, event):
        if ip_addr not in self.waiting_queue:
            self.waiting_queue[ip_addr] = []
        self.waiting_queue[ip_addr].append(event)
        logger.log_color(logger.YELLOW, f"Paquete hacia {ip_addr} encolado (esperando ARP). Total encolados: {len(self.waiting_queue[ip_addr])}")

    def dequeue_packets(self, ip_addr):
        if ip_addr in self.waiting_queue:
            packets = self.waiting_queue.pop(ip_addr)
            logger.log_color(logger.GREEN, f"Desencolando {len(packets)} paquetes hacia {ip_addr}")
            return packets
        return []

    def _dump_arp_table(self):
        logger.log_color(logger.CYAN, "--- ARP TABLE ---")
        logger.log_color(logger.CYAN, "IP\t\tMAC\t\t\tPORT\tAGE")
        for ip, data in self.arp_table.items():
            age = time.time() - data["timestamp"]
            logger.log_color(logger.CYAN, f"{ip}\t{data['mac']}\t{data['port']}\t{age:.2f}s")
        logger.log_color(logger.CYAN, "-----------------")
    
    def learn_arp_entry(self, ip_addr, mac_addr, port):
        self._reap_arp_table()
        if ip_addr not in self.arp_table:
            logger.log_color(logger.GREEN, f"Entrada aprendida: {ip_addr} -> {mac_addr} en puerto {port}")
        else:
            logger.log_color(logger.GREEN, f"Entrada refrescada: {ip_addr} -> {mac_addr} en puerto {port}")
        self.arp_table[ip_addr] = {
            "mac": mac_addr,
            "port": port,
            "timestamp": time.time(),
        }
        self._dump_arp_table()

    def _reap_arp_table(self):
        now = time.time()
        expired = [ip for ip, data in self.arp_table.items()
                   if now - data["timestamp"] > ENTRY_TIMEOUT]
        for ip in expired:
            del self.arp_table[ip]

    def get_mac(self, ip_addr):
        if ip_addr in self.arp_table:
            return self.arp_table[ip_addr]["mac"]
        return None

    def get_port(self, ip_addr):
        if ip_addr in self.arp_table:
            return self.arp_table[ip_addr]["port"]
        return None
    
    def create_arp_reply(self, target_ip, target_mac, target_port, source_ip, source_mac):

        reply = self._build_arp(
            arp.REPLY, 
            source_ip, 
            source_mac, 
            target_ip, 
            target_mac)

        eth = self._build_eth(
            source_mac, 
            target_mac, 
            reply)
        
        msg = self._build_packet_out(eth, target_port)

        return msg
    
    def create_arp_request(self, target_ip, out_port, source_ip, source_mac):

        request = self._build_arp(
            arp.REQUEST, 
            source_ip, 
            source_mac, 
            target_ip, 
            EthAddr("00:00:00:00:00:00"))

        eth = self._build_eth(
            source_mac, 
            EthAddr("ff:ff:ff:ff:ff:ff"), 
            request)

        msg = self._build_packet_out(eth, out_port)

        return msg