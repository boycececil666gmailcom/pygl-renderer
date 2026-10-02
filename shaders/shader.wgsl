struct FrameUniforms {
    view: mat4x4<f32>,
    projection: mat4x4<f32>,
    light_dir: vec3<f32>,
    padding: f32,
};

struct ObjectUniforms {
    model: mat4x4<f32>,
    normal_matrix: mat4x4<f32>,
};

struct MaterialUniforms {
    base_color: vec4<f32>,
    metallic: f32,
    roughness: f32,
    use_texture: u32,
    padding: u32,
};

@group(0) @binding(0) var<uniform> frame: FrameUniforms;
@group(1) @binding(0) var<uniform> obj: ObjectUniforms;
@group(2) @binding(0) var<uniform> mat: MaterialUniforms;
@group(2) @binding(1) var mat_texture: texture_2d<f32>;
@group(2) @binding(2) var mat_sampler: sampler;

struct VertexInput {
    @location(0) position: vec3<f32>,
    @location(1) normal: vec3<f32>,
    @location(2) tex_coords: vec2<f32>,
};

struct VertexOutput {
    @builtin(position) clip_position: vec4<f32>,
    @location(0) normal: vec3<f32>,
    @location(1) tex_coords: vec2<f32>,
};

@vertex
fn vs_main(in: VertexInput) -> VertexOutput {
    var out: VertexOutput;
    out.clip_position = frame.projection * frame.view * obj.model * vec4<f32>(in.position, 1.0);
    let n4 = obj.normal_matrix * vec4<f32>(in.normal, 0.0);
    out.normal = n4.xyz;
    out.tex_coords = in.tex_coords;
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    var base_color = mat.base_color;
    if (mat.use_texture == 1u) {
        base_color = base_color * textureSample(mat_texture, mat_sampler, in.tex_coords);
    }
    if (base_color.a < 0.001) {
        discard;
    }
    let norm = normalize(in.normal);
    let light_direction = normalize(frame.light_dir);
    let view_dir = normalize(vec3<f32>(0.0, 0.5, 1.0));
    let half_dir = normalize(light_direction + view_dir);

    let diff = max(dot(norm, light_direction), 0.0) * 0.4 + 0.6;
    let shininess = mix(128.0, 4.0, mat.roughness);
    let spec = pow(max(dot(norm, half_dir), 0.0), shininess);
    let specular_color = mix(vec3<f32>(0.04), base_color.rgb, mat.metallic) * spec;

    let final_rgb = (base_color.rgb * diff) + specular_color;
    return vec4<f32>(final_rgb, base_color.a);
}
