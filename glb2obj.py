import os
from json import loads

from utils.reader import Reader


class Glb2Obj(Reader):
    def __init__(self, base_name):
        super().__init__(open(f'glb/{base_name}.glb', 'rb').read(), '<')

        magic = self.readChar(4)  # File MAGIC
        if magic == 'glTF':
            version = self.readUInt32()
            if version == 2:
                self.readUInt32()  # file_length

                json_length = self.readUInt32()
                self.read(4)  # json_magic
                self.json_data = self.readChar(json_length)

                self.json_data = loads(self.json_data)

                bin_length = self.readUInt32()
                self.read(4)  # bin_magic
                self.bin_data = self.read(bin_length)

        super().__init__(self.bin_data)
        self.base_name = base_name

        self.meshes = self.json_data['meshes']
        self.nodes = self.json_data['nodes']

        self.buffer_views = []
        self.accessors = []
        self.buffers = []

    def node_parse(self, node_id: int, iter_count: int = 0):
        node = self.nodes[node_id]
        # node_name = node['name']

        if 'mesh' in node:
            mesh_id = node['mesh']
            mesh = self.meshes[mesh_id]
            primitives = mesh['primitives']
            mesh_name = mesh['name']

            if '|' in mesh_name:
                mesh_name = mesh_name.split('|')[-1]

            if not os.path.exists(f'obj/{self.base_name}'):
                os.mkdir(f'obj/{self.base_name}')
            obj = open(f'obj/{self.base_name}/{mesh_name}.obj', 'w')

            offsets = {
                'POSITION': 0,
                'NORMAL': 0,
                'TEXCOORD': 0
            }

            for primitive in primitives:
                if primitive is not None:
                    position_accessor_id = primitive['attributes']['POSITION']
                    position_accessor = self.accessors[position_accessor_id]
                    for item in position_accessor:
                        line = f'v {item[0]} {item[1]} {item[2]}\n'
                        obj.write(line)

                    normal_accessor_id = primitive['attributes']['NORMAL']
                    normal_accessor = self.accessors[normal_accessor_id]
                    for item in normal_accessor:
                        line = f'vn {item[0]} {item[1]} {item[2]}\n'
                        obj.write(line)

                    texcoord_accessor_id = primitive['attributes']['TEXCOORD_0']
                    texcoord_accessor = self.accessors[texcoord_accessor_id]
                    for item in texcoord_accessor:
                        line = f'vt {item[0]} {1 - item[1]}\n'
                        obj.write(line)

                    indices_accessor_id = primitive['indices']
                    indices_accessor = self.accessors[indices_accessor_id]
                    for item_id in range(0, int(len(indices_accessor)), 3):
                        v1 = indices_accessor[item_id][0] + 1 + offsets['POSITION']
                        v2 = indices_accessor[item_id + 1][0] + 1 + offsets['NORMAL']
                        v3 = indices_accessor[item_id + 2][0] + 1 + offsets['TEXCOORD']
                        line = f'f {v1}/{v1}/{v1} {v2}/{v2}/{v2} {v3}/{v3}/{v3}\n'
                        obj.write(line)

                    offsets['POSITION'] += len(position_accessor)
                    offsets['NORMAL'] += len(normal_accessor)
                    offsets['TEXCOORD'] += len(normal_accessor)
            obj.close()

        if 'children' in node:
            for child_id in node['children']:
                self.node_parse(child_id, iter_count + 1)

    def parse(self):
        for buffer in self.json_data['buffers']:
            self.buffers.append(self.read(buffer['byteLength']))

        for buffer_view in self.json_data['bufferViews']:
            super().__init__(self.buffers[buffer_view['buffer']])

            if 'byteOffset' in buffer_view:
                self.read(buffer_view['byteOffset'])

            self.buffer_views.append(self.read(buffer_view['byteLength']))

        for accessor in self.json_data['accessors']:
            super().__init__(self.buffer_views[accessor['bufferView']], '<')
            temp_accessor = []

            if 'byteOffset' in accessor:
                self.read(accessor['byteOffset'])

            types = {
                5120: self.readByte,
                5121: self.readUByte,
                5122: self.readShort,
                5123: self.readUShort,
                5125: self.readUInt32,
                5126: self.readFloat
            }

            items_count = {
                'SCALAR': 1,
                'VEC2': 2,
                'VEC3': 3,
                'VEC4': 4,
                'MAT2': 4,
                'MAT3': 9,
                'MAT4': 16
            }

            # print(accessor)
            for x in range(accessor['count']):
                temp_list = []
                for i in range(items_count[accessor['type']]):
                    temp_list.append(types[accessor['componentType']]())
                temp_accessor.append(temp_list)

            self.accessors.append(temp_accessor)

        scene_id = self.json_data['scene']
        scene = self.json_data['scenes'][scene_id]

        for node_id in scene['nodes']:
            self.node_parse(node_id)

        print(len(self.buffers) == len(self.json_data['buffers']),
              len(self.buffer_views) == len(self.json_data['bufferViews']),
              len(self.accessors) == len(self.json_data['accessors']))


if __name__ == '__main__':
    if not os.path.exists('glb'):
        os.mkdir('glb')

    if not os.path.exists('obj'):
        os.mkdir('obj')

    for filename in os.listdir('glb'):
        if filename.endswith('_geo.glb'):
            filename = ''.join(filename.split('.')[:-1])
            glb = Glb2Obj(filename)
            glb.parse()
