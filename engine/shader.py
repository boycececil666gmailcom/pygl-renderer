#region Imports
import sys
from OpenGL.GL import (
    GL_COMPILE_STATUS,
    GL_FALSE,
    GL_FRAGMENT_SHADER,
    GL_LINK_STATUS,
    GL_VERTEX_SHADER,
    glAttachShader,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDeleteProgram,
    glDeleteShader,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glGetUniformLocation,
    glLinkProgram,
    glShaderSource,
    glUniform1f,
    glUniform1i,
    glUniform3fv,
    glUniform4fv,
    glUniformMatrix4fv,
    glUseProgram,
)
import glm
#endregion

#region Shader Program
class Shader:
    """OpenGL ES 3.0 shader program management with uniform caching."""

    def __init__(self, vert_path: str, frag_path: str):
        self._uniform_locs = {}
        self.program_id = self._create_shader_program(vert_path, frag_path)

    def use(self) -> None:
        glUseProgram(self.program_id)

    def get_loc(self, name: str) -> int:
        if name not in self._uniform_locs:
            self._uniform_locs[name] = glGetUniformLocation(self.program_id, name)
        return self._uniform_locs[name]

    def set_mat4(self, name: str, matrix: glm.mat4) -> None:
        glUniformMatrix4fv(self.get_loc(name), 1, GL_FALSE, glm.value_ptr(matrix))

    def set_vec3(self, name: str, vector: glm.vec3) -> None:
        glUniform3fv(self.get_loc(name), 1, glm.value_ptr(vector))

    def set_vec4(self, name: str, vector: glm.vec4) -> None:
        glUniform4fv(self.get_loc(name), 1, glm.value_ptr(vector))

    def set_float(self, name: str, value: float) -> None:
        glUniform1f(self.get_loc(name), value)

    def set_int(self, name: str, value: int) -> None:
        glUniform1i(self.get_loc(name), value)

    def delete(self) -> None:
        glDeleteProgram(self.program_id)

    def _compile_shader(self, shader_type: int, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            print(f"[Shader-Load] Failed to read shader file {path}: {e}")
            sys.exit(1)

        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            info = glGetShaderInfoLog(shader).decode("utf-8", errors="ignore")
            print(f"[Shader-Compile] {path} failed: {info}")
            glDeleteShader(shader)
            sys.exit(1)
        return shader

    def _create_shader_program(self, vert_path: str, frag_path: str) -> int:
        vs = self._compile_shader(GL_VERTEX_SHADER, vert_path)
        fs = self._compile_shader(GL_FRAGMENT_SHADER, frag_path)

        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        if not glGetProgramiv(program, GL_LINK_STATUS):
            info = glGetProgramInfoLog(program).decode("utf-8", errors="ignore")
            print(f"[Shader-Link] Linking failed: {info}")
            glDeleteShader(vs)
            glDeleteShader(fs)
            glDeleteProgram(program)
            sys.exit(1)

        glDeleteShader(vs)
        glDeleteShader(fs)
        return program
#endregion
