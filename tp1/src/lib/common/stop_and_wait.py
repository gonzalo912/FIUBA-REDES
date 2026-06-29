from .protocol import Protocol
from .packet import Packet
from lib.common.constants import *
from socket import socket, timeout
from lib.common.exceptions import *
from lib.common.event import Event
import time
class StopAndWait(Protocol):

    def __init__(
        self,
        op_type,
        window_size=1,
        chunk_size=1400,
    ):
        super().__init__(op_type)
        self.ack_timeout = ACK_TIMEOUT
        self.max_retries = MAX_RETRIES
        self._pending = None
        self._waiting_ack = False
        self._send_time = None
        self.protocol = STOP_AND_WAIT_PROTOCOL
        self.window_size = 1


    def push_payload(self, data):
        # en SAW, mando de a un paquete
        pkt = self.compose(TYPE_DATA, data)
        self._pending = pkt
        self._waiting_ack = True
        self._send_time = time.time()
        self.logger.debug(f"push_payload: {self._send_time}")
        return [pkt.to_bytes()]
    
    def get_timedouts(self):
        now = time.time()
        if self._pending and now > self._send_time + ACK_TIMEOUT:
            self.logger.debug(f"get_timedouts PPPP: {self._pending.seq_num}")
            self._send_time = time.time()  # resetear timer
            self._waiting_ack = True
            return [self._pending.to_bytes()]
        return []

    def compose(self, pkt_type, data):
        #composes data packet and returns packet
        pkt = Packet(pkt_type, self.op_type, self.protocol, data, self.seq_num)
        self.seq_num += 1
        return pkt
    
    def syn_ack_to_bytes(self):
    # creates ACK packet
        syn_ack = Packet(TYPE_SYN_ACK, self.op_type, self.protocol, b"", 0)
        return syn_ack.to_bytes()
    
    def ack(self, seq):
        # creates ACK packet
        ack = Packet(TYPE_ACK, self.op_type, self.protocol, b"", seq)
        return ack.to_bytes()

    def fin_ack(self):
        fin_ack = Packet(TYPE_CLOSE_ACK, self.op_type, self.protocol, b"", 0)
        return fin_ack.to_bytes()

    def fin(self):
        fin = Packet(TYPE_CLOSE, self.op_type, self.protocol, b"", self.seq_num)
        self._pending = fin
        self._waiting_ack = True
        self._send_time = time.time()
        self.seq_num += 1
        return fin.to_bytes()

    def syn(self, filename, filesize):
        data = filename.encode() + b'\0' + str(filesize).encode()
        syn = Packet(TYPE_SYN, self.op_type, self.protocol, data, 0)
        return syn.to_bytes()
    
    def send_data_packet(self, data: bytes, addr=None, clientDataQueue=None):
        pkt = Packet(TYPE_DATA, self.op_type, self.protocol, data, self.seq_num)
        self._send_and_wait_ack(pkt, addr=addr, clientDataQueue=clientDataQueue)


    def handle_close(self, pkt: Packet, addr=None):
        self._send_ack(pkt.seq_num, addr)
        return True

    def _send_ack(self, seq_num, addr=None):
        ack = self.ack(seq_num)
        self.safe_send(ack.to_bytes(), addr)
    

    def end(self, addr=None, clientDataQueue=None):
        pkt = Packet(TYPE_CLOSE, self.op_type, self.protocol, b"", self.seq_num)
        self._send_and_wait_ack(pkt, addr=addr, clientDataQueue=clientDataQueue)

        if not addr:
            # el unico que cierra la conexion es el cliente, el server mantiene siempre el socket activo para escuchar a cualq cliente
            self.socket.close()

    
            #################################
            ##          HANDLERS           ##
            #################################
    def handle_handshake(self, data):
        pkt = Packet.from_bytes(data)
        if(pkt.pkt_type != TYPE_SYN):
            self.logger.debug(
                "ERROR: Tipo de paquete no es de tipo SYN."
            )
            raise HandshakeError()
        return self.handle_packet(data)

    def handle_packet(self, raw):
        try:
            pkt = Packet.from_bytes(raw)
        except ChecksumError as e:
            self._handle_corrupt(e.seq)
        if pkt.pkt_type == TYPE_SYN:
            return self._handle_syn(pkt)
        if pkt.pkt_type == TYPE_SYN_ACK:
            return self._handle_syn_ack(pkt)
        if pkt.pkt_type == TYPE_ACK:
            return self._handle_ack(pkt)
        if pkt.pkt_type == TYPE_NACK:
            return self._handle_nack(pkt)
        if pkt.pkt_type == TYPE_DATA:
            return self._handle_data(pkt)
        if pkt.pkt_type == TYPE_CLOSE:
            return self._handle_fin(pkt)
        if pkt.pkt_type == TYPE_CLOSE_ACK:
            return self._handle_fin_ack(pkt)
        
        self.logger.debug("Tipo de paquete no identificado")
        raise UnidentifiedPackageType()

    def _handle_syn(self, pkt):
        self.logger.debug("SYN HANDLER")
        data = pkt.data.decode().split('\0')
        filename = data[0]
        filesize = int(data[1])
        self.op_type = pkt.op_type
        self.protocol = pkt.protocol
        if filesize > MAX_FILE_SIZE:
            self.logger.debug(
                f"ERROR: Archivo muy grande. Máximo tamaño de archivo permitido {MAX_FILE_SIZE}")
            raise FilesizeError     
        self.logger.debug("RETURN SYN HANDLER")
        return Event(EVENT_TYPE_HANDSHAKE, filename=filename, filesize=filesize, op_type=self.op_type)
        
    def _handle_ack(self, pkt):
        self.logger.debug(f"SEQ RECIBIDO: {pkt.seq_num}")
        self.logger.debug(f"SEQ ESPERADO: {self.next_expected}")
        if pkt.seq_num == 0:
            return Event(EVENT_TYPE_ACK_INIT, op_type=self.op_type, next=1)
        if self._pending and pkt.seq_num == self._pending.seq_num:
            self._pending = None
            self._waiting_ack = False
            return Event(EVENT_TYPE_ACK, next=1)
        
    def _handle_fin_ack(self, pkt):
        return Event(EVENT_TYPE_CLOSE_FIN)
    
    def _handle_data(self, pkt):
        self.logger.debug(f"SEQ RECIBIDO: {pkt.seq_num}")
        self.logger.debug(f"SEQ ESPERADO: {self.next_expected}")
        if pkt.seq_num == self.next_expected:
            self.next_expected += 1
            return Event(EVENT_TYPE_DATA, ack=pkt.seq_num, data=[pkt.data])
        elif pkt.seq_num < self.next_expected:
            return Event(EVENT_TYPE_DATA, ack=pkt.seq_num)
        return None
    
    def _handle_fin(self, pkt):
        return Event(EVENT_TYPE_CLOSE)
    
    def _handle_syn_ack(self, pkt):
        return Event(EVENT_TYPE_SYN_ACK)
    
    def _handle_corrupt(self, pkt):
        pass