void mainImage(out vec4 f, in vec2 c) {
    vec2 p = (c.xy * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float t = iTime * 0.5;
    float grid = max(step(0.98, fract(p.x * 10.0 + t)), step(0.98, fract(p.y * 10.0 + t)));
    f = vec4(0.1, 0.3, 0.8, 1.0) * grid * 0.3 + vec4(0.02, 0.02, 0.05, 1.0);
}
