# PyGL-Renderer

> A modular, real-time 3D rendering engine written in Python — powered by native OpenGL and the glTF 2.0 standard.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![OpenGL](https://img.shields.io/badge/OpenGL-5586A4?style=flat&logo=opengl&logoColor=white)
![GLFW](https://img.shields.io/badge/GLFW-Window%20Manager-black?style=flat)
![glTF](https://img.shields.io/badge/glTF%202.0-Model%20Format-green?style=flat)
![PyOpenGL](https://img.shields.io/badge/PyOpenGL-GPU%20Bindings-orange?style=flat)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat)

A lightweight, zero-framework 3D graphics engine that reads industry-standard glTF 2.0 model files and renders them in real time using raw OpenGL draw calls — zero game engine overhead, full pipeline control.

---

## Core Purpose & Business Value

PyGL-Renderer is a ground-up, dependency-lean 3D renderer that bypasses the abstraction of high-level game engines. It is purpose-built for engineers and researchers who need precise control over every stage of the real-time rendering pipeline.

- **Full Pipeline Visibility**: Every render stage — from glTF buffer parsing to VAO upload, depth sorting, and shader dispatch — is explicit and inspectable. No black boxes.
- **Industry-Standard 3D Asset Support**: Loads any conformant glTF 2.0 scene file, including meshes, PBR materials, textures, and scene hierarchies, allowing real-world assets to be visualised without conversion.
- **Two-Pass Transparency Rendering**: Opaque and transparent primitives are sorted and drawn in separate GPU passes, ensuring correct alpha blending without visual artefacts.
- **Configurable Without Code Changes**: Camera position, field of view, window dimensions, target frame rate, and directional light can all be tuned via a `.env` file, making the renderer easy to embed in pipelines or demonstrations.
- **Predictable Frame Budget**: A software frame-rate limiter caps rendering to a configurable FPS ceiling, preventing CPU/GPU spin on fast hardware and enabling repeatable performance measurements.
- **Extensible Module Architecture**: The engine is split into focused, single-responsibility modules (`Window`, `Shader`, `Camera`, `Renderer`, `Material`, `GLTFBufferCache`) so any subsystem can be replaced or extended independently.

---

## System Architecture & Technical Execution

### Phase-by-Phase Rendering Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Operator
    participant Main as main.py (Entry Point)
    participant Win as Window (GLFW)
    participant Cfg as Config (.env)
    participant Shd as Shader (GLSL Compiler)
    participant Cam as Camera (View / Projection)
    participant Rdr as Renderer
    participant Buf as GLTFBufferCache (GPU Upload)
    participant GPU as OpenGL GPU

    Note over User, Cfg: Phase 1 - Initialization
    User->>Main: python main.py gltf/toyota_supra.gltf
    Main->>Cfg: Load .env (SCR_WIDTH, TARGET_FPS, CAM_POS, LIGHT_DIR, ...)
    Main->>Win: Create GLFW window + OpenGL ES 3.0 context
    Main->>Shd: Compile shader.vert + shader.frag, link GLSL program
    Main->>Cam: Construct Camera (pos, target, fov, near, far)
    Main->>Rdr: Construct Renderer (glEnable DEPTH_TEST + BLEND)

    Note over Main, GPU: Phase 2 - First-Frame GPU Buffer Upload
    Rdr->>Buf: GLTFBufferCache(gltf, base_dir)
    Buf->>Buf: Parse materials, load PBR textures via Pillow -> GL_TEXTURE_2D
    Buf->>GPU: glGenVertexArrays / glGenBuffers per primitive
    Buf->>GPU: Upload Position VBO (attr 0), Normal VBO (attr 1), UV VBO (attr 2)
    Buf->>GPU: Upload EBO (indexed geometry)

    Note over Rdr, GPU: Phase 3 - Render Loop (per frame)
    loop Every Frame
        Rdr->>Win: process_input() - poll GLFW events
        Rdr->>GPU: glClearColor + glClear (COLOR + DEPTH)
        Rdr->>Shd: shader.use() - bind GLSL program
        Rdr->>Cam: Upload view matrix, projection matrix uniforms
        Rdr->>Rdr: Set lightDir uniform

        alt Pass 1 - Opaque Geometry
            rect rgb(235, 247, 238)
                Rdr->>GPU: glDepthMask(TRUE), render opaque primitives
                Rdr->>GPU: mat.bind() -> upload materialColor, metallic, roughness, useTexture
                Rdr->>GPU: glBindVertexArray(VAO), glDrawElements / glDrawArrays
            end
        else Pass 2 - Transparent Geometry
            rect rgb(255, 243, 205)
                Rdr->>GPU: glDepthMask(FALSE), render transparent primitives
                Rdr->>GPU: Alpha blending: GL_SRC_ALPHA + GL_ONE_MINUS_SRC_ALPHA
                Rdr->>GPU: Discard fragments with alpha < 0.001 (in frag shader)
            end
        end

        Rdr->>Win: swap_buffers() + poll_events()
        Rdr->>Rdr: limit_frame_rate(frame_start) - software FPS cap
    end

    Note over Main, GPU: Phase 4 - Teardown
    Main->>Buf: renderer.clean_cache() - glDeleteVertexArrays / glDeleteBuffers / glDeleteTextures
    Main->>Shd: shader.delete() - glDeleteProgram
    Main->>Win: window.terminate() - glfwTerminate
```

---

### High-Level Engine Architecture

```mermaid
---
config:
  layout: elk
  theme: neutral
---
flowchart TB

    subgraph Operator["Operator"]
        CLI["python main.py path/to/model.gltf"]
    end

    subgraph EntryPoint["Entry Point"]
        Main["main.py\nBootstrap + Render Loop"]
    end

    subgraph Configuration["Configuration Layer"]
        DotEnv[".env file\nSCR_WIDTH, SCR_HEIGHT\nTARGET_FPS, CAM_POS\nLIGHT_DIR, CAM_FOV"]
        Cfg["Config\n(python-dotenv)"]
    end

    subgraph WindowLayer["Window and Context"]
        Win["Window\n(GLFW OpenGL ES 3.0)\nKeyboard Input, Swap Buffers"]
    end

    subgraph ShaderLayer["Shader Pipeline"]
        Shd["Shader\n(PyOpenGL GLSL Compiler)\nVertex + Fragment Stages"]
        Vert["shader.vert\nMVP Transform\nNormal Matrix"]
        Frag["shader.frag\nPBR Blinn-Phong\nDiffuse + Specular\nTexture Sampling\nAlpha Discard"]
    end

    subgraph CameraLayer["Camera System"]
        Cam["Camera\n(pyglm)\nView Matrix: glm.lookAt\nProjection: glm.perspective"]
    end

    subgraph RenderEngine["Render Engine"]
        Rdr["Renderer\nTwo-Pass Render Loop\nOpaque + Transparent\nFrame Rate Limiter"]
    end

    subgraph AssetPipeline["Asset and GPU Buffer Pipeline"]
        gltf["pygltflib.GLTF2\nNative glTF 2.0 Parser"]
        Buf["GLTFBufferCache\nVAO / VBO / EBO Upload\nper Mesh Primitive"]
        MatSys["Material\n(extends pygltflib.Material)\nPBR base color, metallic\nroughness, alpha mode"]
        TexLoad["Texture Loader\n(Pillow -> OpenGL)\nMipmap Generation\nGL_LINEAR_MIPMAP_LINEAR"]
    end

    subgraph GPU["GPU (OpenGL ES 3.0)"]
        VAO["VAO\nAttr 0: Position\nAttr 1: Normal\nAttr 2: UV"]
        EBO["EBO\nIndexed Triangles"]
        Tex["GL_TEXTURE_2D\nMipmapped RGBA"]
    end

    subgraph Assets["3D Asset Files"]
        GLTF_File["toyota_supra.gltf\n(Scene Graph + Material Refs)"]
        BIN_File["toyota_supra_data.bin\n(Binary Buffer: vertex data)"]
        IMG_Files["toyota_supra_img*.png\n(PBR Texture Maps x15)"]
    end

    CLI --> Main
    Main --> Cfg
    DotEnv --> Cfg
    Main --> Win
    Main --> Shd
    Vert --> Shd
    Frag --> Shd
    Main --> Cam
    Main --> Rdr
    Rdr --> Buf
    GLTF_File --> gltf
    BIN_File --> gltf
    IMG_Files --> gltf
    gltf --> Buf
    Buf --> MatSys
    MatSys --> TexLoad
    TexLoad --> Tex
    Buf --> VAO
    Buf --> EBO
    Rdr --> VAO
    Rdr --> Shd
    Cam --> Rdr
    Cfg --> Rdr
    Win --> Rdr
```

---

### Component Network & Data Flow Diagram

```mermaid
---
config:
  layout: elk
  theme: neutral
---
flowchart TB

    subgraph CLI["Operator CLI"]
        Op["python main.py gltf/toyota_supra.gltf"]
    end

    subgraph EntryLayer["main.py - Orchestrator"]
        direction TB
        Boot["Bootstrap: Config + Window + Shader + Camera + Renderer"]
        Loop["Render Loop: process_input -> render_frame -> limit_frame_rate"]
        Cleanup["Teardown: clean_cache + shader.delete + window.terminate"]
    end

    subgraph EngineModules["engine/ - Core Modules"]
        direction TB

        subgraph WinMod["window.py (GLFW)"]
            WinInit["glfwCreateWindow(width, height)"]
            WinInput["glfwPollEvents / glfwGetKey(ESCAPE)"]
            WinSwap["glfwSwapBuffers"]
        end

        subgraph ShdMod["shader.py (PyOpenGL)"]
            ShdCompile["glCreateShader + glCompileShader\nGL_VERTEX_SHADER + GL_FRAGMENT_SHADER"]
            ShdLink["glCreateProgram + glLinkProgram"]
            ShdUni["set_mat4(model, view, projection)\nset_vec3(lightDir)"]
        end

        subgraph CamMod["camera.py (pyglm)"]
            CamView["glm.lookAt(pos, target, up)"]
            CamProj["glm.perspective(fov, aspect, near, far)"]
        end

        subgraph RdrMod["renderer.py (Two-Pass)"]
            RdrPass1["Pass 1: Opaque\nglDepthMask(TRUE)"]
            RdrPass2["Pass 2: Transparent\nglDepthMask(FALSE)\nGL_SRC_ALPHA blending"]
            RdrFPS["Frame Limiter\ntime.sleep(remaining)"]
        end

        subgraph MatMod["material.py (PBR)"]
            MatBind["bind(shader)\nupload: materialColor, metallic\nroughness, useTexture uniforms"]
            MatTex["load_texture(path)\nPillow -> glTexImage2D\nglGenerateMipmap"]
            MatProp["Properties:\nbase_color_vec4\nmetallic_val\nroughness_val\nis_transparent"]
        end

        subgraph GltfMod["gltf_utils.py (Buffer Cache)"]
            GltfParse["extract_accessor_data\ncomponentType -> numpy dtype\ntype -> element count"]
            GltfTransform["get_node_transform_matrix\nmatrix / TRS decomposition\nglm.quat rotation"]
            GltfCache["GLTFBufferCache\ngpu_primitives dict\n(mesh_idx, prim_idx) -> VAO"]
        end
    end

    subgraph GPUBuffers["OpenGL GPU Buffers"]
        direction TB
        VAO_buf["VAO\nattr 0: position (vec3)\nattr 1: normal (vec3)\nattr 2: texcoord (vec2)"]
        VBO_pos["VBO_pos\nGL_ARRAY_BUFFER\nfloat32 positions"]
        VBO_nor["VBO_normal\nGL_ARRAY_BUFFER\nfloat32 normals"]
        VBO_uv["VBO_uv\nGL_ARRAY_BUFFER\nfloat32 UVs"]
        EBO_buf["EBO\nGL_ELEMENT_ARRAY_BUFFER\nuint32 indices"]
        Tex_buf["GL_TEXTURE_2D\nGL_RGBA internal format\nMipmap: GL_LINEAR_MIPMAP_LINEAR"]
    end

    subgraph ShaderFiles["shaders/ - GLSL Programs"]
        direction TB
        VertFile["shader.vert (330 core)\ngl_Position = proj * view * model * pos\nNormal = mat3(transpose(inverse(model))) * aNormal"]
        FragFile["shader.frag (330 core)\nBlinn-Phong: diff * 0.4 + 0.6 ambient\nSpecular: shininess = mix(128.0, 4.0, roughness)\nSpecular color = mix(0.04, baseColor, metallic)\nDiscard: alpha < 0.001"]
    end

    subgraph AssetFiles["gltf/ - Asset Files"]
        GltfFile["toyota_supra.gltf\nscene + nodes + meshes\nmaterials + textures + images"]
        BinFile["toyota_supra_data.bin\nbufferView binary blob\nvertex positions, normals, UVs, indices"]
        ImgFiles["toyota_supra_img0-14.png\n15 PBR texture maps"]
    end

    Op --> Boot
    Boot --> Loop
    Loop --> Cleanup

    Boot --> WinInit
    Boot --> ShdCompile
    ShdCompile --> ShdLink
    Boot --> CamView
    Boot --> CamProj

    Loop --> WinInput
    Loop --> RdrPass1
    Loop --> RdrPass2
    Loop --> RdrFPS

    RdrPass1 --> ShdUni
    RdrPass2 --> ShdUni

    RdrPass1 --> MatBind
    RdrPass2 --> MatBind
    MatBind --> MatTex
    MatBind --> MatProp

    GltfFile --> GltfParse
    BinFile --> GltfParse
    GltfParse --> GltfCache
    GltfTransform --> RdrPass1
    GltfCache --> VAO_buf

    VAO_buf --> VBO_pos
    VAO_buf --> VBO_nor
    VAO_buf --> VBO_uv
    VAO_buf --> EBO_buf
    MatTex --> Tex_buf

    ImgFiles --> MatTex
    VertFile --> ShdCompile
    FragFile --> ShdCompile

    WinSwap --> Loop
```

---

## Repository Structure

```
PYGL-RENDERER/
├── engine/
│   ├── __init__.py          # Public API: Config, Window, Shader, Camera, Renderer
│   ├── camera.py            # Camera: view + projection matrix generation (pyglm)
│   ├── config.py            # Config: environment-driven settings loader (python-dotenv)
│   ├── gltf_utils.py        # GLTFBufferCache: VAO/VBO/EBO GPU upload + accessor parser
│   ├── material.py          # Material: PBR properties + OpenGL texture lifecycle
│   ├── renderer.py          # Renderer: two-pass render loop + frame rate limiter
│   ├── shader.py            # Shader: GLSL compile/link/uniform setter
│   └── window.py            # Window: GLFW context + input + swap buffers
├── gltf/
│   ├── toyota_supra.gltf    # glTF 2.0 scene descriptor (JSON)
│   ├── toyota_supra_data.bin # Binary vertex/index buffer blob
│   └── toyota_supra_img*.png # 15 PBR texture maps
├── scripts/
│   └── load_supra.sh        # Convenience launcher for the Toyota Supra demo
├── shaders/
│   ├── shader.vert          # Vertex shader: MVP transform + normal matrix
│   └── shader.frag          # Fragment shader: Blinn-Phong PBR + alpha discard
├── .env                     # Runtime configuration (camera, window, light, FPS)
├── .gitignore
├── main.py                  # Application entry point + render loop orchestration
└── requirements.txt         # Python dependency manifest
```





## License

This project is licensed under the **MIT License**.
