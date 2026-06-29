from lib.client.Client import Client
from lib.common.cli import upload_parser
from lib.common.logger import Logger
from lib.common.constants import OP_TYPE_UPLOAD

def main():
    args = upload_parser()
    Logger.configure(args.verbose, args.quiet, "CLIENT")
    client = Client(args.protocol, args.host, args.port, OP_TYPE_UPLOAD)
    client.upload_file(args.src, args.name)

if __name__ == "__main__":
    main()