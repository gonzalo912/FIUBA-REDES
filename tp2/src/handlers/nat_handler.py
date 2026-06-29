import time
import util.logger as logger
from util.constants import PAT_PORT_MIN, PAT_PORT_MAX, ENTRY_TIMEOUT

class NatHandler():
    def __init__(self):
        self.nat_table = {}
        self.reverse_nat = {}
        self.public_port_pool = set(range(PAT_PORT_MIN, PAT_PORT_MAX + 1))

    def allocate_public_port(self):
        if not self.public_port_pool:
            return None

        public_port = min(self.public_port_pool)
        self.public_port_pool.remove(public_port)
        return public_port

    def release_public_port(self, public_port):
        if PAT_PORT_MIN <= public_port <= PAT_PORT_MAX:
            self.public_port_pool.add(public_port)

    def _reap_nat_table(self):
        now = time.time()
        expired = []
        for nat_key, data in self.nat_table.items():
            if now - data["timestamp"] > ENTRY_TIMEOUT:
                expired.append(nat_key)

        for nat_key in expired:
            data = self.nat_table.pop(nat_key)
            protocol, private_ip, private_port = nat_key
            reverse_key = (protocol, data["public_ip"], data["public_port"])
            if reverse_key in self.reverse_nat:
                del self.reverse_nat[reverse_key]
            self.release_public_port(data["public_port"])

    def _dump_nat_table(self):
        logger.log_color(logger.CYAN, "--- NAT TABLE ---")
        logger.log_color(logger.CYAN, "PROTO\tPRIVATE\t\tPUBLIC\t\t\tAGE")
        for nat_key, data in self.nat_table.items():
            protocol, private_ip, private_port = nat_key
            public_ip = data["public_ip"]
            public_port = data["public_port"]
            age = time.time() - data["timestamp"]
            logger.log_color(logger.CYAN, f"{protocol}\t{private_ip}:{private_port}\t\t{public_ip}:{public_port}\t\t{age:.2f}s")
        logger.log_color(logger.CYAN, "-----------------")

    def create_pat_entry(self, protocol, private_ip, private_port, public_ip):
        self._reap_nat_table()
        nat_key = (protocol, private_ip, private_port)

        if nat_key in self.nat_table:
            return self.nat_table[nat_key]

        public_port = self.allocate_public_port()

        if public_port is None:
            logger.log_color(logger.RED, "No hay puertos PAT disponibles")
            return None
        
        reverse_nat_key = (protocol, public_ip, public_port)
        nat_timestamp = time.time()

        nat_entry = {
            "public_ip": public_ip,
            "public_port": public_port,
            "timestamp": nat_timestamp,
        }
        self.nat_table[nat_key] = nat_entry
        
        self.reverse_nat[reverse_nat_key] = {
            "private_ip": private_ip,
            "private_port": private_port,
            "timestamp": nat_timestamp,
        }
        
        self._dump_nat_table()

        return nat_entry

    def get_reverse_entry(self, protocol, public_ip, public_port):
        self._reap_nat_table()
        reverse_key = (protocol, public_ip, public_port)
        if reverse_key in self.reverse_nat:
            return self.reverse_nat[reverse_key]
        return None