void mainImage(out vec4 f, in vec2 c) {
    vec2 uv = c / iResolution.xy;
    float r = fract(sin(dot(vec2(floor(uv.x * 50.0), floor(uv.y * 30.0 + iTime * 15.0)), vec2(12.9898, 78.233))) * 43758.5453);
    f = vec4(0.0, r > 0.92 ? r : 0.0, 1.0) * 0.25;
}
