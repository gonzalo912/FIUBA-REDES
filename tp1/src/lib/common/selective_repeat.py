from lib.common.constants import *
from lib.common.packet import Packet
from lib.common.logger import Logger
from lib.common.exceptions import *
from lib.common.event import Event
import time

class SelectiveRepeat():
    
    def __init__(
            self,
            op_type,
            window_size=WINDOW_SIZE, 
            chunk_size=PAYLOAD_SIZE):
        self.logger = Logger.get_logger("PROTOCOL")
        self.window_size = window_size
        self.retransmissions = {}
        self.window = {}
        self.buffer = {}
        self.chunk_size = chunk_size
        self.op_type = op_type
        self.protocol = SELECTIVE_REPEAT_PROTOCOL
        self.seq_num = 1
        self.next_expected = 1
        
    def push_payload(self, data):  
        # creates list of packages
        pkts = []
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i: i + self.chunk_size]
            pkt = self.compose(TYPE_DATA, chunk)
            self.window[pkt.seq_num] = {"pkt" : pkt, 
                                        "time":time.time()}
            #self.logger.debug(f"VENTANA: {self.window.keys()}")
            pkts.append(pkt.to_bytes())
        return pkts
    
    def get_timedouts(self):
        now = time.time()
        timed_out = []
        ## implementar window[seq] = { "pkt" = pkt, "send_time" = time.time()}
        for _, entry in self.window.items():
            if now - entry["time"] > ACK_TIMEOUT:
                timed_out.append(entry["pkt"].to_bytes())
                entry["time"] = time.time() # reseteo timer
        return timed_out
    
    def compose(self, pkt_type, data):
        #composes data packet and returns packet
        pkt = Packet(pkt_type, self.op_type, self.protocol, data, self.seq_num)
        self.seq_num += 1
        return pkt
    
    def fin_ack(self):
        fin_ack = Packet(TYPE_CLOSE_ACK, self.op_type, self.protocol, b"", 0)
        return fin_ack.to_bytes()
    
    def syn_ack_to_bytes(self):
        # creates ACK packet
        syn_ack = Packet(TYPE_SYN_ACK, self.op_type, self.protocol, b"", 0)
        return syn_ack.to_bytes()

    def ack(self, seq):
        # creates ACK packet
        ack = Packet(TYPE_ACK, self.op_type, self.protocol, b"", seq)
        return ack.to_bytes()

    def fin(self):
        fin = Packet(TYPE_CLOSE, self.op_type, self.protocol, b"", self.seq_num)
        self.window[fin.seq_num] = {"pkt": fin, "time": time.time()}
        self.seq_num += 1
        return fin.to_bytes()

    def syn(self, filename, filesize):
        data = filename.encode() + b'\0' + str(filesize).encode()
        syn = Packet(TYPE_SYN, self.op_type, self.protocol, data, 0)
        return syn.to_bytes()
    
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
        data = pkt.data.decode().split('\0')
        filename = data[0]
        filesize = int(data[1])
        self.op_type = pkt.op_type
        self.protocol = pkt.protocol
        if filesize > MAX_FILE_SIZE:
            self.logger.debug(
                f"ERROR: Archivo muy grande. Máximo tamaño de archivo permitido {MAX_FILE_SIZE}")
            raise FilesizeError     
        return Event(EVENT_TYPE_HANDSHAKE, filename=filename, filesize=filesize, op_type=self.op_type)
        
    def _handle_fin(self, pkt):
        return Event(EVENT_TYPE_CLOSE)

    def _handle_fin_ack(self, pkt):
        return Event(EVENT_TYPE_CLOSE_FIN)

    def _handle_ack(self, pkt):
        # discard package.
        # package seq can only be higher
        if pkt.seq_num < self.next_expected:
            # ACK DE CONEXION --- corre en 1 la window
            # para empezar a leer.
            if(pkt.seq_num == 0):
                return Event(EVENT_TYPE_ACK_INIT, op_type = pkt.op_type, next=self.window_size)
            return
        next_packages = 0 # desplazamiento de ventana
        # marco ACK
        #self.logger.debug(f"ACK ESPERADO: {self.next_expected}")
        if pkt.seq_num in self.window:
            del self.window[pkt.seq_num]
        # si el numero de secuencia esperado es menor al proximo a enviar
        # y no esta en la ventana (porque ya se le hizo ACK y se borro),
        # significa que fue recibido y podemos correr la ventana.
        while self.next_expected < self.seq_num and self.next_expected not in self.window:
            self.next_expected += 1
            next_packages += 1
        return Event(EVENT_TYPE_ACK, next=next_packages)

    def _handle_data(self, pkt):
        seq = pkt.seq_num
        # if already received and processed, resend ACK
        if seq < self.next_expected:
            return Event(EVENT_TYPE_DATA, ack=seq)
        # ignore packages too far in the future
        if seq >= self.next_expected + self.window_size:
            return None
        # duplicado
        if seq in self.buffer:
            return Event(EVENT_TYPE_DATA, ack=seq)
        # agrego a buffer
        self.buffer[seq] = pkt.data
        data = []
        seq_nums = []
        while self.next_expected in self.buffer:
            data.append(self.buffer[self.next_expected])
            seq_nums.append(self.next_expected)
            del self.buffer[self.next_expected]
            self.next_expected += 1
        # if(seq != self.next_expected):
        #     return Event(EVENT_TYPE_ACK, seq=seq)
        return Event(EVENT_TYPE_DATA, ack=seq, data=data)
        
    def _handle_syn_ack(self, pkt):
        return Event(EVENT_TYPE_SYN_ACK)
        
        