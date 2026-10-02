# region Imports
import sys

import wgpu

# endregion


# region Shader Module
class Shader:
    """WebGPU WGSL shader module loader and manager."""

    def __init__(self, wgsl_path: str = "shaders/shader.wgsl"):
        self.path = wgsl_path
        self.source = self._load_source(wgsl_path)
        self.module = None

    def _load_source(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"[Shader-Load] Failed to read shader file {path}: {e}")
            sys.exit(1)

    def get_module(self, device: wgpu.GPUDevice) -> wgpu.GPUShaderModule:
        if self.module is None:
            self.module = device.create_shader_module(code=self.source)
        return self.module

    def delete(self) -> None:
        self.module = None


# endregion
