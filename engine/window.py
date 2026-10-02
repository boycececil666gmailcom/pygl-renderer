# region Imports
import sys

import glfw
from OpenGL.GL import GL_RENDERER, GL_VENDOR, GL_VERSION, glGetString, glViewport

# endregion


# region Window Backend
class Window:
    """Window abstraction configured for OpenGL ES 3.0."""

    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height

        if not glfw.init():
            print("[Window-Init] Failed to initialize GLFW.")
            sys.exit(1)

        # OpenGL ES 3.0 Profile
        glfw.window_hint(glfw.CLIENT_API, glfw.OPENGL_ES_API)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)

        self.handle = glfw.create_window(width, height, title, None, None)
        if not self.handle:
            print("[Window-Init] Failed to create OpenGL ES 3.0 window context.")
            glfw.terminate()
            sys.exit(1)

        glfw.make_context_current(self.handle)

        # Log active graphics pipeline details
        vendor = glGetString(GL_VENDOR).decode("utf-8", errors="ignore")
        renderer = glGetString(GL_RENDERER).decode("utf-8", errors="ignore")
        version = glGetString(GL_VERSION).decode("utf-8", errors="ignore")
        print(f"[Window-Init] OpenGL Vendor: {vendor}")
        print(f"[Window-Init] OpenGL Renderer: {renderer}")
        print(f"[Window-Init] OpenGL Version: {version}")

        glfw.set_framebuffer_size_callback(self.handle, self._framebuffer_size_callback)

    def _framebuffer_size_callback(self, window, width, height):
        glViewport(0, 0, width, height)

    def should_close(self) -> bool:
        return glfw.window_should_close(self.handle)

    def swap_buffers(self) -> None:
        glfw.swap_buffers(self.handle)

    def poll_events(self) -> None:
        glfw.poll_events()

    def process_input(self) -> None:
        if glfw.get_key(self.handle, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(self.handle, True)

    def get_size(self) -> tuple:
        return glfw.get_framebuffer_size(self.handle)

    def get_aspect(self) -> float:
        width, height = self.get_size()
        return width / height if height > 0 else 1.0

    def terminate(self) -> None:
        glfw.terminate()


# endregion
