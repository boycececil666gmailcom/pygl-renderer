#version 300 es
precision mediump float;

out vec4 FragColor;

in vec3 Normal;
in vec2 TexCoords;

uniform vec4 materialColor;
uniform float metallic;
uniform float roughness;
uniform bool useTexture;
uniform sampler2D ourTexture;
uniform vec3 lightDir;

void main()
{
    // Start with the base material color
    vec4 baseColor = materialColor;
    
    // Sample texture in memory if present
    if (useTexture)
    {
        baseColor *= texture(ourTexture, TexCoords);
    }
    
    // Discard completely transparent fragments
    if (baseColor.a < 0.001)
    {
        discard;
    }
    
    // Light direction and normal
    vec3 norm = normalize(Normal);
    vec3 lightDirection = normalize(lightDir);
    vec3 viewDir = normalize(vec3(0.0, 0.5, 1.0));
    vec3 halfDir = normalize(lightDirection + viewDir);
    
    // Diffuse component
    float diff = max(dot(norm, lightDirection), 0.0) * 0.4 + 0.6;
    
    // Specular highlight modulated by metallic and roughness
    float shininess = mix(128.0, 4.0, roughness);
    float spec = pow(max(dot(norm, halfDir), 0.0), shininess);
    vec3 specularColor = mix(vec3(0.04), baseColor.rgb, metallic) * spec;
    
    vec3 finalRGB = (baseColor.rgb * diff) + specularColor;
    FragColor = vec4(finalRGB, baseColor.a);
}
