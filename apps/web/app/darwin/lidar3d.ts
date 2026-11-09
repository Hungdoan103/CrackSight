
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyNS = any;

function vertSrc(isWebGL2: boolean) {
  if (isWebGL2) {
    return `#version 300 es
uniform mat4 u_matrix;
uniform float u_pointSize;
in vec3 a_pos;
in vec3 a_color;
out vec3 v_color;
void main() {
  v_color = a_color;
  gl_Position = u_matrix * vec4(a_pos, 1.0);
  gl_PointSize = u_pointSize;
}`;
  }
  return `
uniform mat4 u_matrix;
uniform float u_pointSize;
attribute vec3 a_pos;
attribute vec3 a_color;
varying vec3 v_color;
void main() {
  v_color = a_color;
  gl_Position = u_matrix * vec4(a_pos, 1.0);
  gl_PointSize = u_pointSize;
}`;
}

function fragSrc(isWebGL2: boolean) {
  if (isWebGL2) {
    return `#version 300 es
precision mediump float;
in vec3 v_color;
out vec4 fragColor;
void main() {
  fragColor = vec4(v_color, 1.0);
}`;
  }
  return `
precision mediump float;
varying vec3 v_color;
void main() {
  gl_FragColor = vec4(v_color, 1.0);
}`;
}

function compile(gl: WebGLRenderingContext, type: number, src: string) {
  const sh = gl.createShader(type);
  if (!sh) throw new Error("shader");
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(sh);
    gl.deleteShader(sh);
    throw new Error(info || "shader compile failed");
  }
  return sh;
}

function asMat4(m: AnyNS): Float32Array | null {
  if (!m) return null;
  if (m instanceof Float32Array && m.length >= 16) return m;
  if (m instanceof Float64Array && m.length >= 16) return new Float32Array(m);
  if (Array.isArray(m) && m.length >= 16) return new Float32Array(m);
  return null;
}

export function decodeF32(b64: string): Float32Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  return new Float32Array(bytes.buffer);
}

export function colorsFromIntensity(
  intensity: Float32Array,
  lo: number,
  hi: number,
): Float32Array {
  const n = intensity.length;
  const col = new Float32Array(n * 3);
  const span = Math.max(1e-6, hi - lo);
  for (let i = 0; i < n; i += 1) {
    let t = (intensity[i] - lo) / span;
    if (t < 0) t = 0;
    else if (t > 1) t = 1;
    const g = Math.pow(t, 0.65);
    const v = 0.55 + 0.45 * g;
    col[i * 3] = v;
    col[i * 3 + 1] = v;
    col[i * 3 + 2] = v * 0.92;
  }
  return col;
}

export function colorsFromHeight(xyz: Float32Array, lo: number, hi: number): Float32Array {
  const n = Math.floor(xyz.length / 3);
  const col = new Float32Array(n * 3);
  const span = Math.max(1e-6, hi - lo);
  for (let i = 0; i < n; i += 1) {
    let t = (xyz[i * 3 + 2] - lo) / span;
    if (t < 0) t = 0;
    else if (t > 1) t = 1;
    let r = 0;
    let g = 0;
    let b = 0;
    if (t < 0.33) {
      const u = t / 0.33;
      r = 30 / 255;
      g = (80 + 140 * u) / 255;
      b = (200 + 55 * u) / 255;
    } else if (t < 0.66) {
      const u = (t - 0.33) / 0.33;
      r = (30 + 225 * u) / 255;
      g = (220 - 40 * u) / 255;
      b = (255 - 200 * u) / 255;
    } else {
      const u = (t - 0.66) / 0.34;
      r = 1;
      g = (180 - 140 * u) / 255;
      b = (55 - 40 * u) / 255;
    }
    col[i * 3] = r;
    col[i * 3 + 1] = g;
    col[i * 3 + 2] = b;
  }
  return col;
}

export function buildMercatorCloud(
  maplibregl: AnyNS,
  xyz: Float32Array,
  colors: Float32Array,
  exaggerate: number,
  zFloor: number,
) {
  const n = Math.floor(xyz.length / 3);
  const pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i += 1) {
    const lon = xyz[i * 3];
    const lat = xyz[i * 3 + 1];
    const z = xyz[i * 3 + 2];
    const alt = Math.max(1, (z - zFloor) * exaggerate + 1);
    const m = maplibregl.MercatorCoordinate.fromLngLat({ lng: lon, lat }, alt);
    pos[i * 3] = m.x;
    pos[i * 3 + 1] = m.y;
    pos[i * 3 + 2] = m.z;
  }
  return { pos, col: colors, count: n };
}

export function createLidar3DLayer(
  _maplibregl: AnyNS,
  id: string,
  cloud: { pos: Float32Array; col: Float32Array; count: number },
) {
  let program: WebGLProgram | null = null;
  let posBuf: WebGLBuffer | null = null;
  let colBuf: WebGLBuffer | null = null;
  let aPos = 0;
  let aColor = 0;
  let uMatrix: WebGLUniformLocation | null = null;
  let uPointSize: WebGLUniformLocation | null = null;
  let mapRef: AnyNS = null;

  const layer: AnyNS = {
    id,
    type: "custom",
    renderingMode: "3d",
    visible: true,

    onAdd(map: AnyNS, gl: WebGLRenderingContext) {
      mapRef = map;
      const isWebGL2 =
        typeof WebGL2RenderingContext !== "undefined" && gl instanceof WebGL2RenderingContext;
      const vs = compile(gl, gl.VERTEX_SHADER, vertSrc(isWebGL2));
      const fs = compile(gl, gl.FRAGMENT_SHADER, fragSrc(isWebGL2));
      program = gl.createProgram();
      if (!program) throw new Error("program");
      gl.attachShader(program, vs);
      gl.attachShader(program, fs);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        throw new Error(gl.getProgramInfoLog(program) || "link failed");
      }
      aPos = gl.getAttribLocation(program, "a_pos");
      aColor = gl.getAttribLocation(program, "a_color");
      uMatrix = gl.getUniformLocation(program, "u_matrix");
      uPointSize = gl.getUniformLocation(program, "u_pointSize");

      posBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
      gl.bufferData(gl.ARRAY_BUFFER, cloud.pos, gl.STATIC_DRAW);
      colBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, colBuf);
      gl.bufferData(gl.ARRAY_BUFFER, cloud.col, gl.STATIC_DRAW);

      console.info("[lidar-3d] onAdd", { isWebGL2, count: cloud.count, aPos, aColor });
    },

    setCloud(next: { pos: Float32Array; col: Float32Array; count: number }, gl?: WebGLRenderingContext) {
      cloud.pos = next.pos;
      cloud.col = next.col;
      cloud.count = next.count;
      const g = gl || mapRef?.painter?.context?.gl;
      if (!g || !posBuf || !colBuf) return;
      g.bindBuffer(g.ARRAY_BUFFER, posBuf);
      g.bufferData(g.ARRAY_BUFFER, cloud.pos, g.STATIC_DRAW);
      g.bindBuffer(g.ARRAY_BUFFER, colBuf);
      g.bufferData(g.ARRAY_BUFFER, cloud.col, g.STATIC_DRAW);
    },

    onRemove(_map: AnyNS, gl: WebGLRenderingContext) {
      if (posBuf) gl.deleteBuffer(posBuf);
      if (colBuf) gl.deleteBuffer(colBuf);
      if (program) gl.deleteProgram(program);
      posBuf = colBuf = program = null;
    },

    render(gl: WebGLRenderingContext, matrixArg: AnyNS, options?: AnyNS) {
      if (!program || !this.visible || cloud.count <= 0) return;

      const matrix =
        asMat4(matrixArg) ||
        asMat4(options?.modelViewProjectionMatrix) ||
        asMat4(options?.defaultProjectionData?.mainMatrix);

      if (!matrix) return;

      gl.disable(gl.DEPTH_TEST);
      gl.depthMask(false);

      gl.useProgram(program);
      gl.uniformMatrix4fv(uMatrix, false, matrix);

      const zoom = mapRef?.getZoom?.() ?? 15;
      const size = Math.max(3, Math.min(8, 2 + (zoom - 12) * 1.2));
      gl.uniform1f(uPointSize, size);

      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);

      gl.bindBuffer(gl.ARRAY_BUFFER, colBuf);
      gl.enableVertexAttribArray(aColor);
      gl.vertexAttribPointer(aColor, 3, gl.FLOAT, false, 0, 0);

      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.drawArrays(gl.POINTS, 0, cloud.count);

      gl.depthMask(true);
      gl.enable(gl.DEPTH_TEST);
    },
  };

  return layer;
}
