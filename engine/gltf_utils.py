# region Imports
import os

import glm
import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_ELEMENT_ARRAY_BUFFER,
    GL_FALSE,
    GL_FLOAT,
    GL_STATIC_DRAW,
    glBindBuffer,
    glBindVertexArray,
    glBufferData,
    glDeleteBuffers,
    glDeleteVertexArrays,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenVertexArrays,
    glVertexAttribPointer,
)
from pygltflib import GLTF2

from engine.material import Material

# endregion

# region Component Mappings
COMPONENT_TYPES = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}

TYPE_ELEMENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}
# endregion


# region Buffer Extraction
def get_buffer_data(gltf: GLTF2, buffer_idx: int, base_dir: str = ".") -> bytes:
    buffer = gltf.buffers[buffer_idx]
    if buffer.uri is None:
        return gltf.binary_blob()
    else:
        if buffer.uri.startswith("data:"):
            return gltf.get_data_from_buffer_uri(buffer.uri)
        bin_path = os.path.join(base_dir, buffer.uri)
        if os.path.exists(bin_path):
            with open(bin_path, "rb") as f:
                return f.read()
        return gltf.get_data_from_buffer_uri(buffer.uri)


def extract_accessor_data(gltf: GLTF2, accessor_idx: int, base_dir: str = ".") -> np.ndarray:
    if accessor_idx is None or accessor_idx < 0:
        return None

    accessor = gltf.accessors[accessor_idx]
    if accessor.bufferView is None:
        return None

    buffer_view = gltf.bufferViews[accessor.bufferView]
    raw_buffer_data = get_buffer_data(gltf, buffer_view.buffer, base_dir)

    byte_offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
    dtype = COMPONENT_TYPES.get(accessor.componentType, np.float32)
    num_elements = TYPE_ELEMENTS.get(accessor.type, 1)

    elem_size = np.dtype(dtype).itemsize
    total_elements = accessor.count * num_elements
    total_bytes = total_elements * elem_size

    buffer_slice = raw_buffer_data[byte_offset : byte_offset + total_bytes]
    arr = np.frombuffer(buffer_slice, dtype=dtype)

    if num_elements > 1:
        arr = arr.reshape((accessor.count, num_elements))

    return arr


def get_node_transform_matrix(node) -> glm.mat4:
    """Build local transformation matrix (glm.mat4) for a glTF Node."""
    if hasattr(node, "matrix") and node.matrix is not None and len(node.matrix) == 16:
        m = node.matrix
        return glm.mat4(
            m[0],
            m[1],
            m[2],
            m[3],
            m[4],
            m[5],
            m[6],
            m[7],
            m[8],
            m[9],
            m[10],
            m[11],
            m[12],
            m[13],
            m[14],
            m[15],
        )

    mat = glm.mat4(1.0)

    if hasattr(node, "translation") and node.translation is not None:
        t = node.translation
        mat = glm.translate(mat, glm.vec3(t[0], t[1], t[2]))

    if hasattr(node, "rotation") and node.rotation is not None:
        r = node.rotation
        quat = glm.quat(r[3], r[0], r[1], r[2])
        mat = mat * glm.mat4_cast(quat)

    if hasattr(node, "scale") and node.scale is not None:
        s = node.scale
        mat = glm.scale(mat, glm.vec3(s[0], s[1], s[2]))

    return mat


# endregion


# region Buffer Cache
class GLTFBufferCache:
    """Manages OpenGL VAO/VBO/EBO GPU buffers for a native pygltflib.GLTF2 scene."""

    def __init__(self, gltf: GLTF2, base_dir: str = "."):
        self.gltf = gltf
        self.base_dir = base_dir
        self.materials = []
        self.gpu_primitives = {}

        self._init_materials()
        self._init_gpu_buffers()

    def _init_materials(self):
        if not self.gltf.materials:
            return

        for mat_data in self.gltf.materials:
            mat = Material.from_dict(mat_data.to_dict())
            mat.texture_id = 0
            mat.has_texture = False

            pbr = getattr(mat, "pbrMetallicRoughness", None)
            if pbr is not None and hasattr(pbr, "baseColorTexture") and pbr.baseColorTexture:
                tex_idx = pbr.baseColorTexture.index
                if self.gltf.textures and tex_idx < len(self.gltf.textures):
                    image_idx = self.gltf.textures[tex_idx].source
                    if self.gltf.images and image_idx < len(self.gltf.images):
                        img_info = self.gltf.images[image_idx]
                        if img_info.uri:
                            img_path = os.path.join(self.base_dir, img_info.uri)
                            if os.path.exists(img_path):
                                mat.load_texture(img_path)

            self.materials.append(mat)

    def _init_gpu_buffers(self):
        if not self.gltf.meshes:
            return

        for mesh_idx, mesh in enumerate(self.gltf.meshes):
            for prim_idx, primitive in enumerate(mesh.primitives):
                pos_idx = primitive.attributes.POSITION
                positions = extract_accessor_data(self.gltf, pos_idx, self.base_dir)
                if positions is None:
                    continue

                normals = extract_accessor_data(
                    self.gltf, primitive.attributes.NORMAL, self.base_dir
                )
                uvs = extract_accessor_data(
                    self.gltf, primitive.attributes.TEXCOORD_0, self.base_dir
                )
                indices = extract_accessor_data(self.gltf, primitive.indices, self.base_dir)

                mat = None
                if primitive.material is not None and primitive.material < len(self.materials):
                    mat = self.materials[primitive.material]
                else:
                    mat = Material()

                pos_data = positions.astype("float32").reshape(-1)
                vertex_count = len(pos_data) // 3

                has_indices = indices is not None and len(indices) > 0
                if has_indices:
                    idx_data = indices.astype("uint32").reshape(-1)
                    count = len(idx_data)
                else:
                    idx_data = None
                    count = vertex_count

                VAO = glGenVertexArrays(1)
                glBindVertexArray(VAO)

                # VBO 0: Position
                VBO_pos = glGenBuffers(1)
                glBindBuffer(GL_ARRAY_BUFFER, VBO_pos)
                glBufferData(GL_ARRAY_BUFFER, pos_data.nbytes, pos_data, GL_STATIC_DRAW)
                glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
                glEnableVertexAttribArray(0)

                # VBO 1: Normal
                VBO_normal = 0
                if normals is not None and len(normals) > 0:
                    norm_data = normals.astype("float32").reshape(-1)
                    VBO_normal = glGenBuffers(1)
                    glBindBuffer(GL_ARRAY_BUFFER, VBO_normal)
                    glBufferData(GL_ARRAY_BUFFER, norm_data.nbytes, norm_data, GL_STATIC_DRAW)
                    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
                    glEnableVertexAttribArray(1)

                # VBO 2: UV
                VBO_uv = 0
                if uvs is not None and len(uvs) > 0:
                    uv_data = uvs.astype("float32").reshape(-1)
                    VBO_uv = glGenBuffers(1)
                    glBindBuffer(GL_ARRAY_BUFFER, VBO_uv)
                    glBufferData(GL_ARRAY_BUFFER, uv_data.nbytes, uv_data, GL_STATIC_DRAW)
                    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 0, None)
                    glEnableVertexAttribArray(2)

                # EBO: Element Indices
                EBO = 0
                if has_indices:
                    EBO = glGenBuffers(1)
                    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
                    glBufferData(
                        GL_ELEMENT_ARRAY_BUFFER,
                        idx_data.nbytes,
                        idx_data,
                        GL_STATIC_DRAW,
                    )

                glBindBuffer(GL_ARRAY_BUFFER, 0)
                glBindVertexArray(0)

                self.gpu_primitives[(mesh_idx, prim_idx)] = {
                    "VAO": VAO,
                    "VBO_pos": VBO_pos,
                    "VBO_normal": VBO_normal,
                    "VBO_uv": VBO_uv,
                    "EBO": EBO,
                    "count": count,
                    "has_indices": has_indices,
                    "material": mat,
                }

    def delete(self):
        for prim in self.gpu_primitives.values():
            glDeleteVertexArrays(1, [prim["VAO"]])
            glDeleteBuffers(1, [prim["VBO_pos"]])
            if prim["VBO_normal"]:
                glDeleteBuffers(1, [prim["VBO_normal"]])
            if prim["VBO_uv"]:
                glDeleteBuffers(1, [prim["VBO_uv"]])
            if prim["EBO"]:
                glDeleteBuffers(1, [prim["EBO"]])
            if prim["material"]:
                prim["material"].delete()
        self.gpu_primitives.clear()


# endregion
