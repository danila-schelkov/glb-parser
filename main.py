import os
from json import dump, loads

from utils.reader import Reader


class Glb(Reader):
    def __init__(self, filename):
        self.json_filename = ''.join(filename.split('.')[:-1]) + '.json'

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
                json_data = self.readChar(json_length)

                dump(loads(json_data), open(f'json/{self.json_filename}', 'w'), indent=4)

                bin_length = self.readUInt32()
                self.read(4)  # bin_magic
                self.read(bin_length)  # bin_data


if __name__ == '__main__':
    if not os.path.exists('glb'):
        os.mkdir('glb')

    if not os.path.exists('json'):
        os.mkdir('json')

    for filename in os.listdir('glb'):
        glb = Glb(filename)
        glb.parse()
