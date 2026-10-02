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
    if not buffer.uri:
        return gltf.binary_blob()
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
    return arr.reshape((accessor.count, num_elements)) if num_elements > 1 else arr


def get_node_transform_matrix(node) -> glm.mat4:
    """Build local transformation matrix (glm.mat4) for a glTF Node."""
    if hasattr(node, "matrix") and node.matrix and len(node.matrix) == 16:
        return glm.mat4(*node.matrix)

    mat = glm.mat4(1.0)
    if getattr(node, "translation", None):
        mat = glm.translate(mat, glm.vec3(*node.translation))
    if getattr(node, "rotation", None):
        r = node.rotation
        mat = mat * glm.mat4_cast(glm.quat(r[3], r[0], r[1], r[2]))
    if getattr(node, "scale", None):
        mat = glm.scale(mat, glm.vec3(*node.scale))
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
            pbr = getattr(mat, "pbrMetallicRoughness", None)
            if pbr and getattr(pbr, "baseColorTexture", None):
                tex_idx = pbr.baseColorTexture.index
                if self.gltf.textures and tex_idx < len(self.gltf.textures):
                    img_idx = self.gltf.textures[tex_idx].source
                    if self.gltf.images and img_idx < len(self.gltf.images):
                        img_uri = self.gltf.images[img_idx].uri
                        if img_uri:
                            img_path = os.path.join(self.base_dir, img_uri)
                            if os.path.exists(img_path):
                                mat.load_texture(img_path)
            self.materials.append(mat)

    def _create_vbo(self, data: np.ndarray, index: int, size: int) -> int:
        if data is None or len(data) == 0:
            return 0
        raw = data.astype("float32").reshape(-1)
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, raw.nbytes, raw, GL_STATIC_DRAW)
        glVertexAttribPointer(index, size, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(index)
        return vbo

    def _init_gpu_buffers(self):
        if not self.gltf.meshes:
            return

        for mesh_idx, mesh in enumerate(self.gltf.meshes):
            for prim_idx, primitive in enumerate(mesh.primitives):
                positions = extract_accessor_data(
                    self.gltf, primitive.attributes.POSITION, self.base_dir
                )
                if positions is None:
                    continue

                normals = extract_accessor_data(
                    self.gltf, primitive.attributes.NORMAL, self.base_dir
                )
                uvs = extract_accessor_data(
                    self.gltf, primitive.attributes.TEXCOORD_0, self.base_dir
                )
                indices = extract_accessor_data(self.gltf, primitive.indices, self.base_dir)

                mat = (
                    self.materials[primitive.material]
                    if primitive.material is not None and primitive.material < len(self.materials)
                    else Material()
                )

                has_indices = indices is not None and len(indices) > 0
                count = len(indices.reshape(-1)) if has_indices else len(positions)

                VAO = glGenVertexArrays(1)
                glBindVertexArray(VAO)

                vbo_pos = self._create_vbo(positions, 0, 3)
                vbo_norm = self._create_vbo(normals, 1, 3)
                vbo_uv = self._create_vbo(uvs, 2, 2)

                ebo = 0
                if has_indices:
                    idx_data = indices.astype("uint32").reshape(-1)
                    ebo = glGenBuffers(1)
                    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
                    glBufferData(GL_ELEMENT_ARRAY_BUFFER, idx_data.nbytes, idx_data, GL_STATIC_DRAW)

                glBindBuffer(GL_ARRAY_BUFFER, 0)
                glBindVertexArray(0)

                self.gpu_primitives[(mesh_idx, prim_idx)] = {
                    "VAO": VAO,
                    "VBOs": [v for v in (vbo_pos, vbo_norm, vbo_uv, ebo) if v],
                    "count": count,
                    "has_indices": has_indices,
                    "material": mat,
                }

    def delete(self):
        for prim in self.gpu_primitives.values():
            glDeleteVertexArrays(1, [prim["VAO"]])
            if prim["VBOs"]:
                glDeleteBuffers(len(prim["VBOs"]), prim["VBOs"])
            if prim["material"]:
                prim["material"].delete()
        self.gpu_primitives.clear()


# endregion
