"""
Constantes compartidas por el router (ProtoRouter) y sus handlers
(ARP, NAT/PAT, ICMP).

Se centralizan acá para evitar definiciones duplicadas o inconsistentes
entre módulos.
"""

from pox.lib.addresses import EthAddr, IPAddr


# --- Topología / Red ---------------------------------------------------

PRIVATE_SUBNET = IPAddr("192.168.1.0")      # Red interna
PRIVATE_MASK = 24                           # Máscara de la red interna
PRIVATE_IP = IPAddr("192.168.1.254")        # IP del router en la red privada
PUBLIC_IP = IPAddr("200.0.0.254")           # IP del router en la red pública
PUBLIC_MAC = EthAddr("00:00:00:aa:aa:aa")   # MAC del router hacia la red pública
PRIVATE_MAC = EthAddr("00:00:00:bb:bb:bb")  # MAC del router hacia la red privada
PUBLIC_PORT = 1                             # Puerto del switch conectado a la red pública

SUPPORTED_PROTOCOLS = ("TCP", "UDP", "ICMP")


# --- Tablas de estado (ARP / NAT-PAT / ICMP) ----------------------------

ENTRY_TIMEOUT = 30  # Tiempo (s) tras el cual una entrada se considera expirada

# Rango de puertos públicos para PAT (NAT)
PAT_PORT_MIN = 1024
PAT_PORT_MAX = 65535  # Numero magico de Hamelin

# Rango de IDs públicos para el seguimiento de sesiones ICMP
ICMP_ID_MIN = 1024
ICMP_ID_MAX = 65535
