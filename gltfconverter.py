import json
import os

from parser import GLTFParser
from utilities.bytestream.reader import Reader

GLB_DIRECTORY = 'glb'
OBJ_DIRECTORY = 'obj'


class GLTFConverter:
    def __init__(self, filename: str):
        self.filename = filename
        self.basename = os.path.splitext(filename)[0]

        self.meshes = {}
        self.nodes = []

        self.buffer_views = []
        self.accessors = []
        self.buffers = []

    def convert(self, json_chunk_data: str, bin_data: bytes):
        json_data = json.loads(json_chunk_data)

        self.meshes = json_data['meshes']
        self.nodes = json_data['nodes']

        reader = Reader(bin_data, endian='little')

        for buffer in json_data['buffers']:
            self.buffers.append(reader.read(buffer['byteLength']))

        for buffer_view in json_data['bufferViews']:
            buffer_reader = Reader(self.buffers[buffer_view['buffer']], endian='little')

            if 'byteOffset' in buffer_view:
                buffer_reader.seek(buffer_view['byteOffset'])

            self.buffer_views.append(buffer_reader.read(buffer_view['byteLength']))

        for accessor in json_data['accessors']:
            buffer_view_reader = Reader(self.buffer_views[accessor['bufferView']], endian='little')

            if 'byteOffset' in accessor:
                buffer_view_reader.seek(accessor['byteOffset'])

            types = {
                5120: (buffer_view_reader.read_int8, 1),
                5121: (buffer_view_reader.read_unsigned_int8, 1),
                5122: (buffer_view_reader.read_int16, 2),
                5123: (buffer_view_reader.read_unsigned_int16, 2),
                5125: (buffer_view_reader.read_unsigned_int32, 4),
                5126: (buffer_view_reader.read_float, 4)
            }

            if 'normalized' in accessor and accessor['normalized']:
                types = {
                    5120: (lambda: max(buffer_view_reader.read_int8() / 127, -1), 1),
                    5121: (lambda: buffer_view_reader.read_unsigned_int8() / 255, 1),
                    5122: (lambda: max(buffer_view_reader.read_int16() / 32767, -1), 2),
                    5123: (lambda: buffer_view_reader.read_unsigned_int16() / 65535, 2),
                    5125: (buffer_view_reader.read_unsigned_int32, 4),
                    5126: (buffer_view_reader.read_float, 4)
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

            component_type = accessor['componentType']
            if types.get(component_type) is None:
                raise Exception('Unsupported component type')

            accessor_type = accessor['type']
            if items_count.get(accessor_type) is None:
                raise Exception('Unsupported accessor type')

            accessor_read_method, bytes_per_elem = types[component_type]
            component_count = items_count[accessor_type]

            default_stride = bytes_per_elem * component_count

            stride = json_data['bufferViews'][accessor['bufferView']].get('byteStride') or default_stride

            elements_per_stride = stride // bytes_per_elem
            elements_count = accessor['count'] * elements_per_stride

            temp_list = []
            for i in range(elements_count):
                temp_list.append(accessor_read_method())

            self.accessors.append([
                temp_list[i:i + component_count]
                for i in range(0, elements_count, elements_per_stride)
            ])

        scene_id = json_data['scene']
        scene = json_data['scenes'][scene_id]

        for node_id in scene['nodes']:
            self.convert_node(node_id)

    def convert_node(self, node_id: int):
        node = self.nodes[node_id]
        # node_name = node['name']

        if 'mesh' in node:
            scale = node['scale']

            mesh_id = node['mesh']
            mesh = self.meshes[mesh_id]
            mesh_name = mesh['name']

            if '|' in mesh_name:
                mesh_name = mesh_name.split('|')[-1]

            os.makedirs(f'{OBJ_DIRECTORY}/{self.basename}', exist_ok=True)

            position_offset = 0
            normal_offset = 0
            texcoord_offset = 0

            with open(f'{OBJ_DIRECTORY}/{self.basename}/{mesh_name}.obj', 'w') as obj_file:
                for primitive in mesh['primitives']:
                    if primitive is not None:
                        material = 0
                        if 'material' in primitive:
                            material = primitive['material']

                        position_accessor_id = primitive['attributes']['POSITION']
                        normal_accessor_id = primitive['attributes']['NORMAL']
                        texcoord_accessor_id = primitive['attributes']['TEXCOORD_0']
                        indices_accessor_id = primitive['indices']

                        position_accessor = self.accessors[position_accessor_id]
                        normal_accessor = self.accessors[normal_accessor_id]
                        texcoord_accessor = self.accessors[texcoord_accessor_id]
                        indices_accessor = self.accessors[indices_accessor_id]

                        obj_file.write(f'o {mesh_name}_{material}\n\n')

                        for item in position_accessor:
                            obj_file.write(f'v {item[0] * scale[0]} {item[1] * scale[1]} {item[2] * scale[2]}\n')
                        obj_file.write('\n')

                        for item in normal_accessor:
                            obj_file.write(f'vn {item[0] * scale[0]} {item[1] * scale[1]} {item[2] * scale[2]}\n')
                        obj_file.write('\n')

                        for item in texcoord_accessor:
                            obj_file.write(f'vt {item[0]} {1 - item[1]}\n')
                        obj_file.write('\n')

                        for item_index in range(len(indices_accessor) // 3):
                            v1 = indices_accessor[item_index * 3][0] + 1
                            v2 = indices_accessor[item_index * 3 + 1][0] + 1
                            v3 = indices_accessor[item_index * 3 + 2][0] + 1
                            obj_file.write(
                                f'f '
                                f'{v1 + position_offset}/{v1 + texcoord_offset}/{v1 + normal_offset} '
                                f'{v2 + position_offset}/{v2 + texcoord_offset}/{v2 + normal_offset} '
                                f'{v3 + position_offset}/{v3 + texcoord_offset}/{v3 + normal_offset}\n'
                            )
                        obj_file.write('\n')

                        position_offset += len(position_accessor)
                        texcoord_offset += len(texcoord_accessor)
                        normal_offset += len(normal_accessor)

        if 'children' in node:
            for child_id in node['children']:
                self.convert_node(child_id)


def create_directories():
    """Creates directories for glb and obj files

    :return:
    """

    os.makedirs(GLB_DIRECTORY, exist_ok=True)
    os.makedirs(OBJ_DIRECTORY, exist_ok=True)


def main():
    create_directories()

    for filename in os.listdir(GLB_DIRECTORY):
        if not filename.endswith('_geo.glb'):
            continue

        filename = os.path.basename(filename)

        with open(f'{GLB_DIRECTORY}/{filename}', 'rb') as file:
            data = file.read()

        gltf_parser = GLTFParser(filename)
        gltf_parser.parse(data)

        glb = GLTFConverter(filename)
        glb.convert(
            gltf_parser.json_data,
            gltf_parser.bin_data
        )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
