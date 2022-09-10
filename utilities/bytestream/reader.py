import typing
from io import BufferedReader, BytesIO
from struct import unpack


class Reader(BufferedReader):
    def __init__(self, initial_bytes: bytes, endian: typing.Literal['little', 'big']):
        super().__init__(BytesIO(initial_bytes))
        self.endian = endian

    def read_float(self) -> float:
        return unpack(self.get_endian_symbol_for_struct(self.endian) + 'f', self.read(4))[0]

    def read_unsigned_int64(self) -> int:
        return int.from_bytes(self.read(8), self.endian, signed=False)

    def read_int64(self) -> int:
        return int.from_bytes(self.read(8), self.endian, signed=True)

    def read_unsigned_int32(self) -> int:
        return int.from_bytes(self.read(4), self.endian, signed=False)

    def read_int32(self) -> int:
        return int.from_bytes(self.read(4), self.endian, signed=True)

    def read_unsigned_int16(self):
        return int.from_bytes(self.read(2), self.endian, signed=False)

    def read_int16(self) -> int:
        return int.from_bytes(self.read(2), self.endian, signed=True)

    def read_unsigned_int8(self) -> int:
        return int.from_bytes(self.read(1), self.endian, signed=False)

    def read_int8(self) -> int:
        return int.from_bytes(self.read(1), self.endian, signed=True)

    def read_string(self):
        length = self.read_unsigned_int32()
        return self.read(length).decode('utf-8')

    @staticmethod
    def get_endian_symbol_for_struct(endian: typing.Literal['little', 'big']):
        if endian == 'big':
            return '>'
        elif endian == 'little':
            return '<'
        raise ValueError('Unknown endian')
