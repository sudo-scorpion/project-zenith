void mainImage(out vec4 f, in vec2 c) {
    vec2 uv = c / iResolution.xy;
    float t = iTime * 0.08;
    float pulse = sin(iTime * 1.5) * 0.05 + 0.95;
    vec3 col = 0.5 + 0.5 * cos(t + uv.xyx + vec3(0.0, 2.0, 4.0));
    f = vec4(col * 0.1 * pulse, 0.9) * smoothstep(1.2, 0.2, distance(uv, vec2(0.5)));
}
