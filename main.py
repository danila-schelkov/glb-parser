import os
from json import dump, loads

from utils.reader import Reader


class Glb(Reader):
    def __init__(self, filename):
        self.filename = ''.join(filename.split('.')[:-1])
        self.json_data = b''
        self.bin_data = b''

        with open(f'glb/{filename}', 'rb') as file:
            self.data = file.read()

            file.close()

        super().__init__(self.data, '<')

    def parse(self):
        magic = self.readChar(4)  # File MAGIC
        if magic == 'glTF':
            version = self.readUInt32()
            if version == 2:
                self.readUInt32()  # file_length

                json_length = self.readUInt32()
                self.read(4)  # json_magic
                self.json_data = self.readChar(json_length)

                dump(loads(self.json_data), open(f'parsed/{self.filename}.parsed', 'w'), indent=4)

                bin_length = self.readUInt32()
                print(bin_length)
                self.read(4)  # bin_magic
                self.bin_data = self.read(bin_length)

                open(f'parsed/{self.filename}.bin', 'wb').write(self.bin_data)


# Test
if __name__ == '__main__':
    if not os.path.exists('glb'):
        os.mkdir('glb')

    if not os.path.exists('parsed'):
        os.mkdir('parsed')

    for filename in os.listdir('glb'):
        glb = Glb(filename)
        glb.parse()
