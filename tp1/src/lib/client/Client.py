from socket import *
from lib.common.file_handling import *
from lib.common.protocol_factory import *
from ..common.packet import Packet
from ..common.constants import *
from lib.common.logger import Logger
import time
import os
from lib.common.event import Event

class Client:
    
    def __init__(self, 
                 protocol, 
                 server_host: str, 
                 server_port: int,
                 op_type):
        self.logger = Logger.get_logger("CLIENT")
        self.server_addr = (server_host, server_port)
        self.start_socket(self.server_addr)
        self.protocol = create_protocol(protocol, op_type)
        self.file_handler = FileHandler()
        self.op_type = op_type
    
    def start_socket(self, server_addr):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.connect(self.server_addr)
        self.socket.settimeout(ACK_TIMEOUT)
        self.logger.info(
            f"Cliente listo. Puerto: {self.socket.getsockname()[1]}")
        
    def send_message(self, message: bytes):
        self.socket.send(message)
    
    def wait_response(self) -> bytes:
        while True:
            data, addr = self.socket.recvfrom(BUFFER_SIZE)
            return addr, self.protocol.handle_packet(data)

    def upload_file(self, path, save_name):
        init = time.time()
        self.file_handler.open_for_read(path)
        filesize = self.file_handler.size()
        # handshake
        syn = self.protocol.syn(save_name, filesize)
        self.send_message(syn)
        addr, event = self.wait_response()
        if event:
            self.handle_event(event, addr, self.protocol)
        # fin handshake
        while not self.file_handler.is_closed():
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                event = self.protocol.handle_packet(data)
                if event:
                    self.handle_event(event, addr, self.protocol)
            except timeout:
                # no llegó nada, retransmitir el paquete pendiente
                for b in self.protocol.get_timedouts():
                    self.socket.send(b)
        fin = time.time()
        elapsed = fin - init
        self.logger.info(f"Finished in: {elapsed}")


    def download_file(self, dst_path: str, name: str):
        init = time.time()
        self.file_handler.open_for_write(dst_path)
        syn = self.protocol.syn(name, "1000")
        self.send_message(syn)
        addr, event = self.wait_response()
        if event:
            self.handle_event(event, addr, self.protocol)
        # fin handshake
        while not self.file_handler.is_closed():
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                event = self.protocol.handle_packet(data)
                if event:
                    self.handle_event(event, addr, self.protocol)
            except timeout:
                # no llegó nada, retransmitir el paquete pendiente
                for b in self.protocol.get_timedouts():
                    self.socket.send(b)
        fin = time.time()
        elapsed = fin - init
        self.logger.info(f"Finished in: {elapsed}")

    def handle_event(self, event, addr, protocol):
        if event.type == EVENT_TYPE_SYN_ACK:
            self.handle_syn_ack(event, addr, protocol)
        if event.type == EVENT_TYPE_DATA:
            self.handle_data(event, addr, protocol)
        if event.type == EVENT_TYPE_ACK:
            self.handle_ack(event, protocol)
        if event.type == EVENT_TYPE_CLOSE:
            self.handle_close(protocol)
        if event.type == EVENT_TYPE_ACK_INIT:
            pass
        if event.type == EVENT_TYPE_CLOSE_FIN:
            self.handle_close_fin()
            
    def handle_syn_ack(self, event, addr, protocol):
        self.logger.debug(f"SUCCESS: Conexion establecida con {addr[0]}:{addr[1]}")
        ack = self.protocol.ack(0)
        self.socket.send(ack)
        if self.op_type == OP_TYPE_UPLOAD:
            event = Event(EVENT_TYPE_ACK, next=protocol.window_size)
            self.handle_event(event, addr, protocol)
            
    def handle_data(self, event, addr, protocol):
        #self.logger.debug(f"Escribiendo: {event.data}")}
        self.send_message(protocol.ack(event.ack))
        if hasattr(event, "data") and event.data:
            self.file_handler.write(b"".join(event.data))

    def close(self):
        self.file_handler.close()
        self.logger.debug("Archivo cerrado")

    def handle_handshake():
        pass

    def handle_ack(self, event, protocol):
        for b in protocol.get_timedouts():
            self.socket.send(b)
        advance = event.next
        package_window = self.file_handler.read(advance*PAYLOAD_SIZE) 
        if package_window:
            for i in protocol.push_payload(package_window):
                self.socket.send(i) 
        #self.logger.debug(f"PACKAGE: {len(package_window)}")
        waiting_ack = getattr(protocol, '_waiting_ack', False)
        if not package_window and not protocol.window and not waiting_ack:
            self.logger.debug("FIN")
            fin = protocol.fin()
            self.socket.send(fin)
        # self.logger.debug(f"PACKAGE: {len(package_window)}")
        #if self.file_handler.eof() and not protocol.window:


    def handle_close(self, protocol):
        self.logger.debug("cLose")
        self.file_handler.close()
        fin_ack = protocol.fin_ack()
        self.socket.send(fin_ack)

    def handle_close_fin(self):
        self.logger.debug("FIN:ACK")
        self.file_handler.close()
