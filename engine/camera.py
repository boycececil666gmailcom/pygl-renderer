# region Imports
import glm

# endregion


# region Camera Class
class Camera:
    """Encapsulates 3D camera properties and transformation matrices for WebGPU."""

    def __init__(
        self,
        pos: glm.vec3 = glm.vec3(0.0, 0.5, 3.5),
        target: glm.vec3 = glm.vec3(0.0, 0.0, 0.0),
        up: glm.vec3 = glm.vec3(0.0, 1.0, 0.0),
        fov: float = 45.0,
        near: float = 0.1,
        far: float = 100.0,
    ):
        self.pos = pos
        self.target = target
        self.up = up
        self.fov = fov
        self.near = near
        self.far = far

    def get_view_matrix(self) -> glm.mat4:
        """Returns the View transformation matrix."""
        return glm.lookAt(self.pos, self.target, self.up)

    def get_projection_matrix(self, aspect_ratio: float) -> glm.mat4:
        """Returns the Perspective Projection matrix with WebGPU [0, 1] clip space depth."""
        return glm.perspectiveRH_ZO(glm.radians(self.fov), aspect_ratio, self.near, self.far)


# endregion
