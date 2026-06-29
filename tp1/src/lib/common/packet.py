import struct 
import zlib
from .constants import *
from .exceptions import *
from .logger import Logger

class Packet:

    # Header format: 
    # | INFO = Package Type (3bits) | Op (1bit) | Prt (1bit) | Payload Length (27bits) |
    # |                             Checksum CRC32 (4bytes)                            |
    # |                                SEQ_NUM (4bytes)                                |


    # TYPE_SYN = 0
    # TYPE_SYN_ACK = 1
    # TYPE_ACK = 2
    # TYPE_DATA = 3
    # TYPE_CLOSE = 4
    # TYPE_NACK = 5

    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, pkt_type, op_type, protocol, data=b"", seq_num=0):
        self.pkt_type = pkt_type
        self.logger = Logger.get_logger("PACKET")
        self.seq_num = seq_num
        self.data = data
        self.op_type = op_type
        self.protocol = protocol
        self.crc = 0
        self.data_length = len(self.data)

    # From Packet to bytes

    def to_bytes(self):
        # Creates header and concatenates with data
        info = self._compose_info_field()

        if isinstance(self.data, str):
            payload = self.data.encode()
        else:
            payload = self.data

        header_part = struct.pack(HEADER_FORMAT, info, 0, self.seq_num)
        self.crc = zlib.crc32(header_part + payload)

        header = struct.pack(HEADER_FORMAT, info, self.crc, self.seq_num)
        return header + payload

    def _compose_info_field(self):
        info = 0
        
        # pktType: bits 31-29
        info |= (self.pkt_type << (INFO_FIELD_SIZE - PKT_TYPE_FIELD_SIZE))
        
        # Op: bit 28
        info |= (self.op_type << (INFO_FIELD_SIZE - PKT_TYPE_FIELD_SIZE - OP_TYPE_FIELD_SIZE))
        
        # Protocol: bit 27
        info |= (self.protocol << (INFO_FIELD_SIZE - PKT_TYPE_FIELD_SIZE - OP_TYPE_FIELD_SIZE - PROTOCOL_FIELD_SIZE))
        
        info |= (self.data_length & PAYLOAD_LENGTH_MASK)
        
        return info
    
    # From bytes to Packet

    @classmethod 
    def from_bytes(cls, raw):
        if len(raw) < cls.HEADER_SIZE:
            raise ValueError("Paquete corto para procesar")
        info, crc, seq = struct.unpack(
            HEADER_FORMAT, raw[:cls.HEADER_SIZE])
        pkt_type, op_type, protocol, payload_length = cls.parse_info_bytes(info)
        if not cls.compare_checksum(raw, crc):
            logger = Logger.get_logger("PACKET")
            logger.debug(f"Paquete {seq} corrupto: invalid Checksum")
            raise ChecksumError(seq)
        return cls(pkt_type, 
                   op_type, 
                   protocol, 
                   raw[cls.HEADER_SIZE: cls.HEADER_SIZE + payload_length],
                   seq)
    
    @classmethod
    def parse_info_bytes(cls, info):
        # Bitwise operations
        pkt_type = (info >> (INFO_FIELD_SIZE - PKT_TYPE_FIELD_SIZE)) & PKT_TYPE_MASK
        op_type = (info >> (INFO_FIELD_SIZE - PKT_TYPE_FIELD_SIZE - OP_TYPE_FIELD_SIZE)) & OP_TYPE_MASK
        protocol = (info >> (INFO_FIELD_SIZE - PKT_TYPE_FIELD_SIZE - OP_TYPE_FIELD_SIZE - PROTOCOL_FIELD_SIZE)) & PROTOCOL_MASK
        payload_length = info & PAYLOAD_LENGTH_MASK
        return pkt_type, op_type, protocol, payload_length
    
    @staticmethod
    def compare_checksum(raw_packet, expected):
        # Get checksum from raw bytes
        # Recompose packet with 0 in checksum field
        packet_to_validate = raw_packet[:4] + b'\x00\x00\x00\x00' + raw_packet[8:]
        real_checksum = zlib.crc32(packet_to_validate)
        return expected == real_checksum

