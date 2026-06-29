import argparse
from .constants import STOP_AND_WAIT, SELECTIVE_REPEAT

def _set_logger_args(parser: argparse.ArgumentParser):
    logger_level = parser.add_mutually_exclusive_group()
    logger_level.add_argument("-v", 
                              "--verbose", 
                              help="increase output verbosity", 
                              action="store_true")
    logger_level.add_argument("-q", 
                              "--quiet", 
                              help="decrease output verbosity", 
                              action="store_true")
    
def _set_connection_args(parser: argparse.ArgumentParser):
    parser.add_argument("-H", 
                        "--host", 
                        help="service IP address", 
                        required=True)
    parser.add_argument("-p", 
                        "--port", 
                        help="service port", 
                        type=int, 
                        required=True)
    
def _set_protocol(parser: argparse.ArgumentParser):
    parser.add_argument(
                    "-r", 
                    "--protocol", 
                    help="error recovery protocol: stop_and_wait | selective_repeat",
                    choices=[STOP_AND_WAIT, SELECTIVE_REPEAT],
                    default=SELECTIVE_REPEAT)
    
def _set_file_name(parser: argparse.ArgumentParser):
    parser.add_argument("-n", 
                        "--name", 
                        help="file name")

def _create_parser(description=""):
    return argparse.ArgumentParser(
        description=description
    )

def _set_client_args(parser):
    _set_connection_args(parser)
    _set_logger_args(parser)
    _set_protocol(parser)
    _set_file_name(parser)

def download_parser():
    parser = _create_parser("download a file from specified server")
    parser.prog = "download"
    parser.usage = (
        '%(prog)s [ -h ] [ -v | -q ] [ -H ADDR ] [ -p PORT ] [ -d FILEPATH ] [ -n FILENAME ] [ -r protocol ]')
    _set_client_args(parser)
    parser.add_argument("-d", 
                        "--dst", 
                        help="dest file path", 
                        required=True)
    return parser.parse_args()


def upload_parser():
    parser = _create_parser("upload a file to specified server")
    parser.prog = "upload"
    parser.usage = (
        '%(prog)s [ -h ] [ -v | -q ] [ -H ADDR ] [ -p PORT ] [ -s FILEPATH ] [ -n FILENAME ] [ -r protocol ]')
    _set_client_args(parser)
    parser.add_argument("-s", 
                        "--src", 
                        help="source file path", 
                        required=True)
    return parser.parse_args()

def server_parser():
    parser = _create_parser(
        "A Stop & Wait UDP server that implements Selective Repeat for error recovery, will accept incoming requests to upload files and download previously stored files.")
    parser.prog = "start-server" 
    parser.usage = (
        '%(prog)s [ -h ] [ -v | -q ] [ -H ADDR ] [ -p PORT ] [ -s DIRPATH ]')
    _set_connection_args(parser)
    _set_logger_args(parser)
    parser.add_argument("-s", 
                        "--storage", 
                        help="storage dir path", 
                        default="./storage")
    return parser.parse_args()
