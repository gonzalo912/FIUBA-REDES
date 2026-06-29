from pathlib import Path

BASE_DIR = Path("storage")

class FileHandler:

    def __init__(self, base_path=""):
        self.base_dir = Path(base_path)
        self.file = None
        self.path = None
        self.filename = None

    def create_file(self, filename = None):
        if filename == None:
            filename = self.filename
        self.open_for_write(filename)
    
    def set_filename(self, filename: str):
        self.filename = filename

    # --- OPEN ---

    def open_for_write(self, filename: str):
        self.path = self.base_dir / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "wb")

    def open_for_read(self, filename: str = None):
        if filename == None:
            filename = self.filename
        self.path = self.base_dir / filename
        self.file = open(self.path, "rb")

    # --- WRITE ---

    def write(self, data: bytes):
        if not self.file:
            raise RuntimeError("File not opened")
        self.file.write(data)

    # --- READ ---

    def read(self, size: int) -> bytes:
        if not self.file:
            raise RuntimeError("File not opened")
        return self.file.read(size)

    # --- META ---

    def size(self) -> int:
        if not self.path:
            raise RuntimeError("File not opened")
        return self.path.stat().st_size

    def eof(self) -> bool:
        if not self.file:
            raise RuntimeError("File not opened")

        # solo válido si está en modo lectura
        if "r" not in self.file.mode:
            raise RuntimeError("EOF check only valid in read mode")

        return self.file.tell() >= self.size()
    
    def is_closed(self) -> bool:
        if not self.file:
            return True
        return self.file.closed

    # --- CLOSE ---

    def close(self):
        if self.file:
            self.file.close()
            self.file = None