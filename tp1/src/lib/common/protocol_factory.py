from .constants import (
    SELECTIVE_REPEAT,
    SELECTIVE_REPEAT_PROTOCOL,
    STOP_AND_WAIT,
    STOP_AND_WAIT_PROTOCOL,
)

from .stop_and_wait import StopAndWait
from lib.common.selective_repeat import SelectiveRepeat

from lib.common.packet import Packet

def protocol_id_from_choice(protocol_choice):
    if isinstance(protocol_choice, int):
        return protocol_choice
    if protocol_choice == STOP_AND_WAIT:
        return STOP_AND_WAIT_PROTOCOL
    if protocol_choice == SELECTIVE_REPEAT:
        return SELECTIVE_REPEAT_PROTOCOL
    raise ValueError(f"Protocolo desconocido: {protocol_choice}")

def create_protocol(protocol, op_type):
    if protocol == STOP_AND_WAIT:
        return StopAndWait(op_type)
    if protocol == SELECTIVE_REPEAT:
        return SelectiveRepeat(op_type)
    raise ValueError(f"Protocolo desconocido: {protocol}")


def protocol_factory_create(raw):
    pkt = Packet.from_bytes(raw)
    protocol_id = pkt.protocol
    if protocol_id == STOP_AND_WAIT_PROTOCOL:
        return StopAndWait(pkt.op_type)
    if protocol_id == SELECTIVE_REPEAT_PROTOCOL:
        return SelectiveRepeat(pkt.op_type)
    raise ValueError(f"ID de protocolo desconocido: {protocol_id}")
