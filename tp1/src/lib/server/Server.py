import os
from socket import *
from ..common.constants import *
from lib.common.protocol_factory import *
from lib.common.exceptions import *
from lib.common.file_handling import *
from lib.common.logger import Logger
import threading
import queue
from queue import Empty

class Server:

    def __init__(self, storage_path: str, host: str, port: int):
        self.init_storage_dir(storage_path)
        self.storage_path = storage_path
        self.host = host
        self.port = port
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((host, port))
        self.logger = Logger.get_logger("SERVER")
        # multithreading
        self.clientDataQueues = {}
        self.clientDataQueueLock = threading.Lock() # Lock para clientDataQueues
        self.socketLock = threading.Lock() # Lock para socket
        
        print(f"Socket listening on {host}:{port}")

    def init_storage_dir(self, storage_path: str):
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

    def start(self):
        while True:
            try:
                self.socket.settimeout(1.0)
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                self._raise_thread(addr, data)
                # agregar al cliente a la cola
                self.clientDataQueues[addr].put(data)
            except timeout:
                continue
            except Exception as e:
                print(f"[MAIN ERROR] {e}")

    
    def _raise_thread(self, addr, data):
        with self.clientDataQueueLock:
            if addr not in self.clientDataQueues:
                # crea un protocolo para el cliente
                clientDataQueue = queue.Queue()
                self.clientDataQueues[addr] = clientDataQueue
                thread = threading.Thread(target=self.handle_clientt, args=(addr, clientDataQueue))
                thread.daemon = True
                thread.start()

    def handle_clientt(self, addr, que):
        event = None
        initialized = False
        protocol = None
        file_handler = FileHandler("storage")
        inactivity = 0
        while True:
            try:
                data = que.get(timeout=ACK_TIMEOUT)
                inactivity = 0

                if not initialized:
                    protocol = protocol_factory_create(data)
                    event = protocol.handle_handshake(data)
                    initialized = True
                else: 
                    event = protocol.handle_packet(data)

                if event:
                    self._handle_event(event, addr, protocol, file_handler)
                    if event.type == EVENT_TYPE_CLOSE_FIN:
                        self.logger.info(f"Cerrando hilo para {addr} por fin de conexión.")
                        break

            except Empty:
                inactivity += ACK_TIMEOUT
                if inactivity >= 60:
                    self.logger.info(f"Cerrando hilo para {addr} por inactividad.")
                    break
                if initialized and protocol:
                    for b in protocol.get_timedouts():
                        self.socket.sendto(b, addr)
            except HandshakeError:
                self.logger.info(
                    f"No pudo establecerse conexión con el cliente {addr[0]}:{addr[1]}"
                )
                break
            # except Exception as e:
            #     self.logger.error(f"Error inesperado en hilo {addr}: {e}")
            #     break
    
    def _handle_event(self, event, addr, protocol, file_handler):
        if event.type == EVENT_TYPE_HANDSHAKE:
            self._handle_handshake(addr, event, protocol, file_handler)
        if event.type == EVENT_TYPE_DATA:
            self._handle_data(event, addr, protocol, file_handler)
        if event.type == EVENT_TYPE_ACK:
            self._handle_ack(event, addr, protocol, file_handler)
        if event.type == EVENT_TYPE_CLOSE:
            self._handle_close(addr, event, protocol, file_handler)
        if event.type == EVENT_TYPE_ACK_INIT:
            self._handle_init(addr, event, protocol, file_handler)
        if event.type == EVENT_TYPE_CLOSE_FIN:
            self.handle_close_fin(addr, file_handler)

    def _handle_handshake(self, addr, event, protocol, file_handler):
        self.socket.sendto(protocol.syn_ack_to_bytes(), addr)
        file_handler.set_filename(event.filename)
            
    def _handle_init(self, addr, event, protocol, file_handler):
        if(event.op_type == OP_TYPE_DOWNLOAD):
            file_handler.open_for_read()
            self._handle_ack(event, addr, protocol, file_handler)
        else:
            file_handler.create_file()
        self.logger.info(
            f"Conexión con {addr[0]}:{addr[1]} establecida"
        )

    def _handle_data(self, event, addr, protocol, file_handler):
        # data es el chunk de bytes que tiene que ir al archivo
        # llega seq_num = los sequence numbers que hay que hacer ack
        # llega data = la data que hay que ubicar en el archivo
        #self.logger.info(f"llegaron los sequence: {event.ack}")
        self.socket.sendto(protocol.ack(event.ack), addr)
        #self.logger.debug(f"Escribiendo: {event.data}")
        
        if hasattr(event, "data") and event.data:

            self.logger.debug(f"DATA: {len(event.data[0])}")

            file_handler.write(b"".join(event.data))

    def _handle_ack(self, event, addr, protocol, file_handler):
        for b in protocol.get_timedouts():
            self.socket.send(b)
        advance = event.next
        package_window = file_handler.read(advance*PAYLOAD_SIZE) 
        if package_window:
            for i in protocol.push_payload(package_window):
                self.socket.sendto(i, addr)
        
        waiting_ack = getattr(protocol, '_waiting_ack', False)
        if file_handler.eof() and not protocol.window and not waiting_ack:
            self.logger.debug("FIN")
            fin = protocol.fin()
            self.socket.sendto(fin, addr)

    def _handle_close(self, addr, event, protocol, file_handler):
        self.logger.debug("HANDLE CLOSE")
        fin_ack = protocol.fin_ack()
        self.socket.sendto(fin_ack, addr)
        file_handler.close()
        

    def handle_close_fin(self, addr, file_handler):
        with self.clientDataQueueLock:
            if addr in self.clientDataQueues:
                file_handler.close()
                del self.clientDataQueues[addr]
