# region Imports
import glm
import numpy as np
from OpenGL.GL import (
    GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR,
    GL_REPEAT,
    GL_RGBA,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNSIGNED_BYTE,
    glActiveTexture,
    glBindTexture,
    glDeleteTextures,
    glGenerateMipmap,
    glGenTextures,
    glTexImage2D,
    glTexParameteri,
)
from PIL import Image
from pygltflib import Material as GLTFMaterial

# endregion


# region Material Class
class Material(GLTFMaterial):
    """OpenGL ES 3.0 GPU Material extending pygltflib.Material."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.texture_id = 0
        self.has_texture = False

    @property
    def base_color_vec4(self) -> glm.vec4:
        pbr = self.pbrMetallicRoughness
        if pbr and pbr.baseColorFactor:
            c = pbr.baseColorFactor
            return glm.vec4(c[0], c[1], c[2], c[3] if len(c) > 3 else 1.0)
        return glm.vec4(1.0, 1.0, 1.0, 1.0)

    @property
    def metallic_val(self) -> float:
        pbr = self.pbrMetallicRoughness
        return float(pbr.metallicFactor) if pbr and pbr.metallicFactor is not None else 0.0

    @property
    def roughness_val(self) -> float:
        pbr = self.pbrMetallicRoughness
        return float(pbr.roughnessFactor) if pbr and pbr.roughnessFactor is not None else 0.5

    @property
    def is_transparent(self) -> bool:
        return self.alphaMode in ["BLEND", "MASK"] or self.base_color_vec4.a < 0.99

    def load_texture(self, img_source):
        try:
            pil_img = Image.open(img_source) if isinstance(img_source, str) else img_source
            if pil_img.mode != "RGBA":
                pil_img = pil_img.convert("RGBA")

            img_data = np.array(pil_img, dtype=np.uint8)
            width, height = pil_img.size

            self.texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(
                GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data
            )
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            self.has_texture = True
        except Exception as e:
            print(f"[Material-Load] Error loading texture '{img_source}': {e}")
            self.has_texture = False

    def bind(self, shader):
        shader.set_vec4("materialColor", self.base_color_vec4)
        shader.set_float("metallic", self.metallic_val)
        shader.set_float("roughness", self.roughness_val)
        shader.set_int("useTexture", 1 if self.has_texture else 0)

        if self.has_texture:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            shader.set_int("ourTexture", 0)

    def unbind(self):
        if self.has_texture:
            glBindTexture(GL_TEXTURE_2D, 0)

    def delete(self):
        if self.has_texture:
            glDeleteTextures(1, [self.texture_id])


# endregion
