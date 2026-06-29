from lib.common.cli import server_parser
from lib.server.Server import Server
from lib.common.logger import Logger

def main():
    args = server_parser()
    Logger.configure(args.verbose, args.quiet, "SERVER")
    sv = Server(args.storage, args.host, args.port)
    sv.start()

if __name__ == "__main__":
    main()