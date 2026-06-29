from lib.common.cli import download_parser
from lib.client.Client import Client
from lib.common.logger import Logger
from lib.common.constants import  OP_TYPE_DOWNLOAD

def main():

    args = download_parser()

    Logger.configure(args.verbose, args.quiet, "CLIENT")
    
    client = Client(args.protocol, args.host, args.port, OP_TYPE_DOWNLOAD)
    client.download_file(args.dst, args.name)

if __name__ == "__main__":
    main()