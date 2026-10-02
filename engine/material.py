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
    glGetUniformLocation,
    glTexImage2D,
    glTexParameteri,
    glUniform1f,
    glUniform1i,
    glUniform4fv,
)
from PIL import Image
from pygltflib import Material as GLTFMaterial

# endregion


# region Material Class
class Material(GLTFMaterial):
    """OpenGL GPU Material extending pygltflib.Material directly."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.texture_id = 0
        self.has_texture = False

    @property
    def base_color_vec4(self) -> glm.vec4:
        """Returns baseColorFactor as glm.vec4."""
        if self.pbrMetallicRoughness and self.pbrMetallicRoughness.baseColorFactor:
            c = self.pbrMetallicRoughness.baseColorFactor
            return glm.vec4(c[0], c[1], c[2], c[3] if len(c) > 3 else 1.0)
        return glm.vec4(1.0, 1.0, 1.0, 1.0)

    @property
    def metallic_val(self) -> float:
        """Returns metallicFactor."""
        if self.pbrMetallicRoughness and self.pbrMetallicRoughness.metallicFactor is not None:
            return float(self.pbrMetallicRoughness.metallicFactor)
        return 0.0

    @property
    def roughness_val(self) -> float:
        """Returns roughnessFactor."""
        if self.pbrMetallicRoughness and self.pbrMetallicRoughness.roughnessFactor is not None:
            return float(self.pbrMetallicRoughness.roughnessFactor)
        return 0.5

    @property
    def is_transparent(self) -> bool:
        """Determines if the material requires an alpha blending pass."""
        if self.alphaMode in ["BLEND", "MASK"]:
            return True
        return self.base_color_vec4.a < 0.99

    def load_texture(self, img_source):
        """Loads a texture from a file path or PIL Image instance."""
        try:
            if isinstance(img_source, str):
                pil_img = Image.open(img_source)
            else:
                pil_img = img_source
            self.texture_id = self._load_texture_from_pil(pil_img)
            self.has_texture = True
        except Exception as e:
            print(f"[Material-Load] Error loading texture '{img_source}': {e}")
            self.has_texture = False

    def _load_texture_from_pil(self, pil_image):
        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")

        img_data = np.array(pil_image, dtype=np.uint8)
        width, height = pil_image.size

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width,
            height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            img_data,
        )
        glGenerateMipmap(GL_TEXTURE_2D)

        glBindTexture(GL_TEXTURE_2D, 0)
        return tex_id

    def bind(self, shader):
        glUniform4fv(
            glGetUniformLocation(shader.program_id, "materialColor"),
            1,
            glm.value_ptr(self.base_color_vec4),
        )
        glUniform1f(glGetUniformLocation(shader.program_id, "metallic"), self.metallic_val)
        glUniform1f(glGetUniformLocation(shader.program_id, "roughness"), self.roughness_val)
        glUniform1i(
            glGetUniformLocation(shader.program_id, "useTexture"),
            1 if self.has_texture else 0,
        )

        if self.has_texture:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glUniform1i(glGetUniformLocation(shader.program_id, "ourTexture"), 0)

    def unbind(self):
        if self.has_texture:
            glBindTexture(GL_TEXTURE_2D, 0)

    def delete(self):
        if self.has_texture:
            glDeleteTextures(1, [self.texture_id])


# endregion
