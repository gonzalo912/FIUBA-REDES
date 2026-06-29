local protocol = Proto('ProtocoloGrupo5', 'TP Redes Grupo 5')

--[[
Header  12 Bytes

    INFO:
    -- infoField (32 bits)
    3 bits de tipo de paquete 
    1 bit tipo de operación 
    1 bit protocolo (indicar StopAndWait (0) o SelectiveRepeat (1))
    27 bits de tamaño del payload

    Cheksum CRC32:
    -- checksumField (32 bits)
    32 bits de checksum 

    SEQ_NUM:
    -- seqnumField (32 bits)
    32 bits de identificador

-- dataField
DATA (hasta 1400 bytes)


Tipo paquete:
000  SYN
001  SYN-ACK
010  ACK
011  DATA
100  CLOSE
101  NACK

Tipo operación:
0 Download 
1 Upload 
]]

local infoField = ProtoField.uint32('infoField', 'Principal', base.HEX)

local packetTypeSubfield = ProtoField.uint32('packetTypeSubfield', 'Tipo de Paquete', base.DEC, {
    [0]='SYN', [1]='SYN-ACK', [2]='ACK', [3]='DATA', [4]='CLOSE', [5]='NACK', [6]='CLOSE_ACK'
}, 0xE0000000)

local operationTypeSubfield = ProtoField.uint32('operationTypeSubfield', 'Tipo de Operacion', base.DEC, {
    [0]='Download', [1]='Upload'
}, 0x10000000)

local protocolSubfield = ProtoField.uint32('protocolSubfield', 'Protocolo', base.DEC, {
    [0]='StopAndWait', [1]='SelectiveRepeat'
}, 0x08000000)

local payloadSizeSubfield = ProtoField.uint32('payloadSizeSubfield', 'Tamanio del Payload', base.DEC, nil, 0x07FFFFFF)


local checksumField = ProtoField.uint32('checksumField', 'Checksum', base.HEX)

local seqnumField = ProtoField.uint32('seqnumField', 'Numero Secuencia', base.DEC)


local dataField = ProtoField.bytes('dataField', 'DATA')


protocol.fields = {infoField, packetTypeSubfield, operationTypeSubfield, protocolSubfield, payloadSizeSubfield, checksumField, seqnumField, dataField}


-- Funcion para leer el header del paquete - hook dissector de lua
function protocol.dissector(buffer, pinfo, tree)

    local headerLen = buffer:len()
    if headerLen < 12 then
        pinfo.cols.protocol = 'ProtocoloGrupo5'
        tree:add(protocol, buffer(), 'ProtocoloGrupo5 (Paquete corto)')
        return 
    end
    
    pinfo.cols.protocol = 'ProtocoloGrupo5'

    local subtree = tree:add(protocol, buffer(), 'ProtocoloGrupo5')

    local mainTree = subtree:add(infoField, buffer(0,4))
    mainTree:add(packetTypeSubfield, buffer(0,4))
    mainTree:add(operationTypeSubfield, buffer(0,4))
    mainTree:add(protocolSubfield, buffer(0,4))
    mainTree:add(payloadSizeSubfield, buffer(0,4))

    subtree:add(checksumField, buffer(4,4))

    subtree:add(seqnumField, buffer(8,4))

    local type_val = buffer(0,4):uint() >> 29
    local types = {[0]='SYN', [1]='SYN-ACK', [2]='ACK', [3]='DATA', [4]='CLOSE', [5]='NACK', [6]='CLOSE_ACK'}
    local type_name = types[type_val] or "Unknown"
    local seq_val = buffer(8,4):uint()

    local info_text = type_name .. " | Seq_Num: " .. seq_val

    local headerLen = buffer:len()
    if (headerLen > 12) then
        subtree:add(dataField, buffer(12))
        info_text = info_text .. " | Data_Len: " .. (headerLen - 12)
    end

    pinfo.cols.info:clear()
    pinfo.cols.info = info_text

end

-- Registrar el protocolo en un puerto UDP
local portUPD = 9000
local tableUDP = DissectorTable.get('udp.port')
tableUDP:add(portUPD, protocol)

