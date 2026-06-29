import logging
import sys


class Logger:

    _configured = False

    @classmethod
    def configure(cls, verbose = False, quiet = False, role: str = "app"):
        ## SINGLETON
        if cls._configured:
            return
        
        # only verbose when verbose = True and quiet = False
        verbosity = verbose and (not quiet)
        level = logging.DEBUG if verbosity else logging.INFO

        formatter = logging.Formatter(
            fmt=(
                "%(asctime)s | "
                "%(levelname)s | "
                "%(name)s | "
                "%(threadName)s | "
                "%(message)s"
            ),
            datefmt="%H:%M:%S",
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.setLevel(level)
        root.handlers.clear()
        root.addHandler(handler)

        cls._configured = True

        logging.getLogger(role).info(
            "Logging initialized (verbose=%s)",
            verbose
        )

    @staticmethod
    def get_logger(name: str):

        return logging.getLogger(name)