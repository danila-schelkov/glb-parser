import os
from json import dump, loads

from utilities.bytestream.reader import Reader


PARSED_DIRECTORY = 'parsed'
GLB_DIRECTORY = 'glb'


class GLTFParser:
    """glTF file format parser"""

    def __init__(self, filename: str):
        self.filename = os.path.basename(filename)

        self.json_data: str or None = None
        self.bin_data: bytes or None = None

    def parse(self, data: bytes) -> None:
        reader = Reader(data, endian='little')

        magic = reader.read(4)  # File MAGIC
        if magic != b'glTF':
            raise TypeError('Unknown file MAGIC!')

        version = reader.read_unsigned_int32()
        if version != 2:
            raise ValueError('Unsupported version: ' + version)

        reader.read_unsigned_int32()  # file_length

        while reader.tell() < len(data):
            chunk_type, chunk_data = self.parse_chunk(reader)
            if chunk_type == b'JSON':
                self.json_data = chunk_data.decode()
            elif chunk_type == b'BIN\0':
                self.bin_data = chunk_data
            else:
                raise TypeError('Unknown chunk type.')

    def dump_data(self, directory: str) -> None:
        """Dumps json and binary data to directory into files 'filename.json' and 'filename.bin' respectively.

        :parameter directory: a directory for the parsed data
        :return: None
        """

        dump(loads(self.json_data), open(f'{directory}/{self.filename}.json', 'w'), indent=4)
        open(f'{directory}/{self.filename}.bin', 'wb').write(self.bin_data)

    @staticmethod
    def parse_chunk(reader: Reader) -> tuple[bytes, bytes]:
        """

        :return: a tuple of chunk type and chunk data.
        """

        chunk_length = reader.read_unsigned_int32()
        chunk_type = reader.read(4)
        chunk_data = reader.read(chunk_length)
        return chunk_type, chunk_data


def create_directories() -> None:
    """Creates directories for glb files and parsed data

    :return:
    """

    os.makedirs(GLB_DIRECTORY, exist_ok=True)
    os.makedirs(PARSED_DIRECTORY, exist_ok=True)


def main():
    create_directories()

    for filename in os.listdir(GLB_DIRECTORY):
        with open(f'{GLB_DIRECTORY}/{filename}', 'rb') as file:
            data = file.read()

        glb_parser = GLTFParser(filename)
        glb_parser.parse(data)
        glb_parser.dump_data(PARSED_DIRECTORY)


if __name__ == '__main__':
    main()
