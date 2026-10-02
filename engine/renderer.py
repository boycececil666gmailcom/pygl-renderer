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

        # Configure global OpenGL pipeline parameters
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def render_frame(
        self, shader: Shader, gltf: GLTF2, camera: Camera, base_dir: str = "."
    ) -> None:
        """Executes a single render frame pass directly from a pygltflib.GLTF2 instance."""
        # 1. Initialize GPU buffers for gltf if not cached
        gltf_id = id(gltf)
        if gltf_id not in self._buffer_caches:
            self._buffer_caches[gltf_id] = GLTFBufferCache(gltf, base_dir)

        cache = self._buffer_caches[gltf_id]

        # 2. Clear color and depth buffers
        glClearColor(*self.clear_color)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # 3. Activate shader program and bind view/projection uniforms
        shader.use()
        shader.set_mat4("view", camera.get_view_matrix())
        shader.set_mat4("projection", camera.get_projection_matrix(self.window.get_aspect()))
        shader.set_vec3("lightDir", self.config.light_dir)

        # 4. Determine root nodes to render
        scene_nodes = []
        if gltf.scenes and len(gltf.scenes) > 0:
            active_scene_idx = gltf.scene if gltf.scene is not None else 0
            scene_nodes = gltf.scenes[active_scene_idx].nodes or []
        elif gltf.nodes:
            scene_nodes = list(range(len(gltf.nodes)))

        # 5. Two-pass rendering: Pass 1 Opaque, Pass 2 Transparent
        for is_transparent_pass in [False, True]:
            if is_transparent_pass:
                glDepthMask(GL_FALSE)
            else:
                glDepthMask(GL_TRUE)

            def render_node(node_idx: int, parent_transform: glm.mat4):
                node = gltf.nodes[node_idx]
                local_transform = get_node_transform_matrix(node)
                world_transform = parent_transform * local_transform

                if node.mesh is not None and node.mesh < len(gltf.meshes):
                    mesh = gltf.meshes[node.mesh]
                    shader.set_mat4("model", world_transform)

                    for prim_idx, primitive in enumerate(mesh.primitives):
                        key = (node.mesh, prim_idx)
                        if key not in cache.gpu_primitives:
                            continue

                        gpu_prim = cache.gpu_primitives[key]
                        mat = gpu_prim["material"]

                        # Filter by pass transparency
                        if mat.is_transparent != is_transparent_pass:
                            continue

                        # Bind material and VAO
                        mat.bind(shader)
                        glBindVertexArray(gpu_prim["VAO"])

                        if gpu_prim["has_indices"]:
                            glDrawElements(GL_TRIANGLES, gpu_prim["count"], GL_UNSIGNED_INT, None)
                        else:
                            glDrawArrays(GL_TRIANGLES, 0, gpu_prim["count"])

                        glBindVertexArray(0)
                        mat.unbind()

                # Process child nodes recursively
                if hasattr(node, "children") and node.children:
                    for child_idx in node.children:
                        render_node(child_idx, world_transform)

            for root_node_idx in scene_nodes:
                render_node(root_node_idx, glm.mat4(1.0))

        glDepthMask(GL_TRUE)

        # 6. Swap buffers and poll OS window events
        self.window.swap_buffers()
        self.window.poll_events()

    def clean_cache(self, gltf: GLTF2 = None):
        """Cleans GPU buffer caches."""
        if gltf is not None:
            gltf_id = id(gltf)
            if gltf_id in self._buffer_caches:
                self._buffer_caches[gltf_id].delete()
                del self._buffer_caches[gltf_id]
        else:
            for cache in self._buffer_caches.values():
                cache.delete()
            self._buffer_caches.clear()

    def limit_frame_rate(self, frame_start_time: float) -> None:
        """Applies software frame rate limiting based on Config settings."""
        if self.config.target_frame_time > 0:
            duration = time.time() - frame_start_time
            remaining = self.config.target_frame_time - duration
            if remaining > 0:
                time.sleep(remaining)


# endregion
