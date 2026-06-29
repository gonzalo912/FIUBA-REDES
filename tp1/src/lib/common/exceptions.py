class ChecksumError(Exception):
    def __init__(self, seq):
        self.seq = seq
        super().__init__()

class FilesizeError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class HandshakeError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class UnidentifiedPackageType(Exception):
    def __init__(self, *args):
        super().__init__(*args)