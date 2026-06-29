import time
import util.logger as logger
from util.constants import ICMP_ID_MIN, ICMP_ID_MAX, ENTRY_TIMEOUT
from pox.lib.packet.icmp import icmp, echo, TYPE_ECHO_REQUEST, TYPE_ECHO_REPLY
from pox.lib.packet.icmp import TYPE_DEST_UNREACH, TYPE_TIME_EXCEED

class IcmpHandler():
    def __init__(self):
        self.icmp_table = {}
        self.reverse_icmp = {}
        self.icmp_id_pool = set(range(ICMP_ID_MIN, ICMP_ID_MAX + 1))

    def allocate_icmp_id(self):
        if not self.icmp_id_pool:
            return None

        icmp_id = min(self.icmp_id_pool)
        self.icmp_id_pool.remove(icmp_id)
        return icmp_id

    def release_icmp_id(self, icmp_id):
        if ICMP_ID_MIN <= icmp_id <= ICMP_ID_MAX:
            self.icmp_id_pool.add(icmp_id)

    def _reap_icmp_table(self):
        now = time.time()
        expired = []
        for key, data in self.icmp_table.items():
            if now - data["timestamp"] > ENTRY_TIMEOUT:
                expired.append(key)

        for key in expired:
            data = self.icmp_table.pop(key)
            private_ip, private_id = key
            reverse_key = (data["public_ip"], data["public_id"])
            if reverse_key in self.reverse_icmp:
                del self.reverse_icmp[reverse_key]
            self.release_icmp_id(data["public_id"])

    def _dump_icmp_table(self):
        logger.log_color(logger.CYAN, "--- ICMP TABLE ---")
        logger.log_color(logger.CYAN, "PRIVATE\t\tPUBLIC\t\t\tAGE")
        for key, data in self.icmp_table.items():
            private_ip, private_id = key
            public_ip = data["public_ip"]
            public_id = data["public_id"]
            age = time.time() - data["timestamp"]
            logger.log_color(logger.CYAN, f"{private_ip}:{private_id}\t\t{public_ip}:{public_id}\t\t{age:.2f}s")
        logger.log_color(logger.CYAN, "-----------------")

    def create_entry(self, private_ip, private_id, public_ip):
        self._reap_icmp_table()
        key = (private_ip, private_id)

        if key in self.icmp_table:
            return self.icmp_table[key]

        public_id = self.allocate_icmp_id()

        if public_id is None:
            logger.log_color(logger.RED, "No hay ICMP IDs disponibles")
            return None

        reverse_key = (public_ip, public_id)
        timestamp = time.time()

        entry = {
            "public_ip": public_ip,
            "public_id": public_id,
            "timestamp": timestamp,
        }
        self.icmp_table[key] = entry

        self.reverse_icmp[reverse_key] = {
            "private_ip": private_ip,
            "private_id": private_id,
            "timestamp": timestamp,
        }

        self._dump_icmp_table()

        return entry

    def get_reverse_entry(self, public_ip, public_id):
        self._reap_icmp_table()
        reverse_key = (public_ip, public_id)
        if reverse_key in self.reverse_icmp:
            return self.reverse_icmp[reverse_key]
        return None