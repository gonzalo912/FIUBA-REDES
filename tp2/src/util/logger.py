from pox.core import core      

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


log = core.getLogger()

def log_color(color, msg):
    log.info(f"{color}{msg}{RESET}")