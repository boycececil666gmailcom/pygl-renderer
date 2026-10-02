# region Imports
import time

import glm
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FALSE,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_SRC_ALPHA,
    GL_TRIANGLES,
    GL_TRUE,
    GL_UNSIGNED_INT,
    glBindVertexArray,
    glBlendFunc,
    glClear,
    glClearColor,
    glDepthMask,
    glDrawArrays,
    glDrawElements,
    glEnable,
)
from pygltflib import GLTF2

from engine.camera import Camera
from engine.config import Config
from engine.gltf_utils import GLTFBufferCache, get_node_transform_matrix
from engine.shader import Shader
from engine.window import Window

# endregion


# region Renderer Class
class Renderer:
    """glTF 2.0 OpenGL ES 3.0 Renderer."""

    def __init__(self, window: Window, config: Config):
        self.window = window
        self.config = config
        self.clear_color = (0.094, 0.094, 0.106, 1.0)
        self._buffer_caches = {}

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def render_frame(
        self, shader: Shader, gltf: GLTF2, camera: Camera, base_dir: str = "."
    ) -> None:
        """Executes a single render frame pass directly from a pygltflib.GLTF2 instance."""
        gltf_id = id(gltf)
        if gltf_id not in self._buffer_caches:
            self._buffer_caches[gltf_id] = GLTFBufferCache(gltf, base_dir)
        cache = self._buffer_caches[gltf_id]

        glClearColor(*self.clear_color)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        shader.use()
        shader.set_mat4("view", camera.get_view_matrix())
        shader.set_mat4("projection", camera.get_projection_matrix(self.window.get_aspect()))
        shader.set_vec3("lightDir", self.config.light_dir)

        # Get root scene nodes
        scene_nodes = (
            gltf.scenes[gltf.scene or 0].nodes
            if gltf.scenes
            else list(range(len(gltf.nodes or [])))
        ) or []

        # Two-pass rendering: Pass 1 Opaque, Pass 2 Transparent
        for is_transparent in (False, True):
            glDepthMask(GL_FALSE if is_transparent else GL_TRUE)
            for root_idx in scene_nodes:
                self._render_node(shader, gltf, cache, root_idx, glm.mat4(1.0), is_transparent)

        glDepthMask(GL_TRUE)
        self.window.swap_buffers()
        self.window.poll_events()

    def _render_node(
        self,
        shader: Shader,
        gltf: GLTF2,
        cache: GLTFBufferCache,
        node_idx: int,
        parent_transform: glm.mat4,
        is_transparent: bool,
    ) -> None:
        node = gltf.nodes[node_idx]
        world_transform = parent_transform * get_node_transform_matrix(node)

        if node.mesh is not None and node.mesh < len(gltf.meshes):
            shader.set_mat4("model", world_transform)
            for prim_idx in range(len(gltf.meshes[node.mesh].primitives)):
                gpu_prim = cache.gpu_primitives.get((node.mesh, prim_idx))
                if not gpu_prim:
                    continue

                mat = gpu_prim["material"]
                if mat.is_transparent != is_transparent:
                    continue

                mat.bind(shader)
                glBindVertexArray(gpu_prim["VAO"])
                if gpu_prim["has_indices"]:
                    glDrawElements(GL_TRIANGLES, gpu_prim["count"], GL_UNSIGNED_INT, None)
                else:
                    glDrawArrays(GL_TRIANGLES, 0, gpu_prim["count"])
                glBindVertexArray(0)
                mat.unbind()

        for child_idx in getattr(node, "children", []) or []:
            self._render_node(shader, gltf, cache, child_idx, world_transform, is_transparent)

    def clean_cache(self, gltf: GLTF2 = None):
        """Cleans GPU buffer caches."""
        if gltf is not None:
            cache = self._buffer_caches.pop(id(gltf), None)
            if cache:
                cache.delete()
        else:
            for cache in self._buffer_caches.values():
                cache.delete()
            self._buffer_caches.clear()

    def limit_frame_rate(self, frame_start_time: float) -> None:
        """Applies software frame rate limiting based on Config settings."""
        if self.config.target_frame_time > 0:
            remaining = self.config.target_frame_time - (time.time() - frame_start_time)
            if remaining > 0:
                time.sleep(remaining)


# endregion
