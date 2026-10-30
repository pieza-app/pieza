// Portada de Pieza en 3D: WebGL propio, sin librerías. Nueve piezas de rompecabezas extruidas (canto, bisel redondeado, luz,
// sombras sobre una rejilla) que llegan como malla de alambre, se «compilan» en sólido y encajan al ritmo de una terminal
// (`pieza agregar ia`…). Si no hay WebGL, si falla o si el equipo no da abasto, queda el rompecabezas CSS de siempre
// (pagina.js lo arma al recibir «sin-gl»). Lo decorativo es aria-hidden; los textos salen del HTML (data-t).
(function () {
  "use strict";
  const escena = document.querySelector(".escena");
  const lienzo = document.getElementById("pz3d");
  if (!escena || !lienzo) return;
  const quieto = window.matchMedia("(prefers-reduced-motion: reduce)");
  const angosto = window.matchMedia("(max-width: 820px)");

  /* ---------- Contexto ---------- */
  const OPC = { alpha: true, antialias: true, premultipliedAlpha: true, depth: true, stencil: false, powerPreference: "high-performance" };
  let gl = null;
  try { gl = lienzo.getContext("webgl2", OPC) || lienzo.getContext("webgl", OPC); } catch (e) { gl = null; }
  if (!gl) { lienzo.remove(); return; }

  function sinGL() {
    // Algo falló: se apaga la 3D y vuelve el rompecabezas CSS.
    detener();
    escena.classList.remove("gl");
    lienzo.remove();
    escena.dispatchEvent(new CustomEvent("sin-gl"));
  }

  /* ---------- Matrices (column-major, como espera WebGL) ---------- */
  function m4() { const m = new Float32Array(16); m[0] = m[5] = m[10] = m[15] = 1; return m; }
  function mul(a, b) {
    const o = new Float32Array(16);
    for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
      o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
    }
    return o;
  }
  function tras(x, y, z) { const m = m4(); m[12] = x; m[13] = y; m[14] = z; return m; }
  function rotX(a) { const m = m4(), c = Math.cos(a), s = Math.sin(a); m[5] = c; m[6] = s; m[9] = -s; m[10] = c; return m; }
  function rotY(a) { const m = m4(), c = Math.cos(a), s = Math.sin(a); m[0] = c; m[2] = -s; m[8] = s; m[10] = c; return m; }
  function rotZ(a) { const m = m4(), c = Math.cos(a), s = Math.sin(a); m[0] = c; m[1] = s; m[4] = -s; m[5] = c; return m; }
  function persp(fov, asp, n, f) {
    const m = new Float32Array(16), k = 1 / Math.tan(fov / 2);
    m[0] = k / asp; m[5] = k; m[10] = (f + n) / (n - f); m[11] = -1; m[14] = (2 * f * n) / (n - f);
    return m;
  }
  function normal3(m) { return new Float32Array([m[0], m[1], m[2], m[4], m[5], m[6], m[8], m[9], m[10]]); }

  /* ---------- Geometría: el contorno de cada pieza (los mismos de index.html) → extrusión con bisel ---------- */
  const CONTORNOS = [
    "M0 0L100 0L100 38A14 14 0 1 0 100 62L100 100L62 100A14 14 0 1 1 38 100L0 100L0 0Z",
    "M0 0L100 0L100 38A14 14 0 1 1 100 62L100 100L62 100A14 14 0 1 0 38 100L0 100L0 62A14 14 0 1 1 0 38L0 0Z",
    "M0 0L100 0L100 100L62 100A14 14 0 1 1 38 100L0 100L0 62A14 14 0 1 0 0 38L0 0Z",
    "M0 0L38 0A14 14 0 1 0 62 0L100 0L100 38A14 14 0 1 1 100 62L100 100L62 100A14 14 0 1 0 38 100L0 100L0 0Z",
    "M0 0L38 0A14 14 0 1 1 62 0L100 0L100 38A14 14 0 1 0 100 62L100 100L62 100A14 14 0 1 1 38 100L0 100L0 62A14 14 0 1 0 0 38L0 0Z",
    "M0 0L38 0A14 14 0 1 0 62 0L100 0L100 100L62 100A14 14 0 1 0 38 100L0 100L0 62A14 14 0 1 1 0 38L0 0Z",
    "M0 0L38 0A14 14 0 1 1 62 0L100 0L100 38A14 14 0 1 0 100 62L100 100L0 100L0 0Z",
    "M0 0L38 0A14 14 0 1 0 62 0L100 0L100 38A14 14 0 1 1 100 62L100 100L0 100L0 62A14 14 0 1 1 0 38L0 0Z",
    "M0 0L38 0A14 14 0 1 1 62 0L100 0L100 100L0 100L0 62A14 14 0 1 0 0 38L0 0Z",
  ];
  const GRUESO = 0.075, BISEL = 0.028, SEGB = 4;

  // Lee M, L, A (círculos) y Z, y devuelve puntos en unidades de pieza (centro en 0, y hacia arriba).
  function leerContorno(d) {
    const tk = d.match(/[MLAZ]|-?\d*\.?\d+/g), pts = [];
    let i = 0, x = 0, y = 0;
    const n = () => parseFloat(tk[i++]);
    while (i < tk.length) {
      const c = tk[i++];
      if (c === "M" || c === "L") { x = n(); y = n(); pts.push([x, y]); }
      else if (c === "A") {
        const r = n(); n(); n(); const fa = n(), fs = n(), x1 = n(), y1 = n();
        // Centro del arco según la especificación de SVG (sin rotación, círculo).
        const xp = (x - x1) / 2, yp = (y - y1) / 2;
        const sg = fa !== fs ? 1 : -1;
        const k = sg * Math.sqrt(Math.max(0, (r * r - xp * xp - yp * yp) / (xp * xp + yp * yp)));
        const cxp = k * yp, cyp = -k * xp, cx = cxp + (x + x1) / 2, cy = cyp + (y + y1) / 2;
        const a0 = Math.atan2((yp - cyp) / r, (xp - cxp) / r);
        let da = Math.atan2((-yp - cyp) / r, (-xp - cxp) / r) - a0;
        if (fs === 0 && da > 0) da -= 2 * Math.PI;
        if (fs === 1 && da < 0) da += 2 * Math.PI;
        const seg = 26;
        for (let s = 1; s <= seg; s++) { const a = a0 + (da * s) / seg; pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); }
        x = x1; y = y1;
      }
    }
    let p = pts.map(([a, b]) => [(a - 50) / 100, -(b - 50) / 100]);
    const u = p[p.length - 1];
    if (Math.hypot(u[0] - p[0][0], u[1] - p[0][1]) < 1e-6) p.pop();
    let area = 0;
    for (let j = 0; j < p.length; j++) { const a = p[j], b = p[(j + 1) % p.length]; area += a[0] * b[1] - b[0] * a[1]; }
    if (area < 0) p.reverse();
    return p;
  }

  // Redondea las esquinas (las del cuadrado y donde la lengüeta nace del borde): el contorno se remuestrea fino, cada esquina
  // se reemplaza por una curva de radio r y después se quitan los puntos que no aportan forma. Así el bisel nunca se cruza.
  function redondear(p, r) {
    const H = 0.004, N0 = p.length, d = [];
    for (let i = 0; i < N0; i++) {
      const a = p[i], b = p[(i + 1) % N0], l = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.round(l / H));
      for (let s = 0; s < n; s++) d.push([a[0] + ((b[0] - a[0]) * s) / n, a[1] + ((b[1] - a[1]) * s) / n]);
    }
    const N = d.length, giro = (i) => {
      const a = d[(i - 1 + N) % N], b = d[i], c = d[(i + 1) % N];
      return Math.abs(Math.atan2((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]), (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])));
    };
    const k = Math.round(r / H), o = d.slice(), esquinas = [];
    for (let i = 0; i < N; i++) if (giro(i) > 0.3) esquinas.push(i);
    for (const c of esquinas) {
      const p1 = d[(c - k + N) % N], p2 = d[(c + k) % N], q = d[c];
      for (let s = -k; s <= k; s++) {
        const t = (s + k) / (2 * k), u = 1 - t;
        o[(c + s + N) % N] = [u * u * p1[0] + 2 * u * t * q[0] + t * t * p2[0], u * u * p1[1] + 2 * u * t * q[1] + t * t * p2[1]];
      }
    }
    // Quitar lo que no aporta: se guarda un punto cuando la curva ya giró lo suficiente o el tramo se hizo largo.
    const res = [o[0]];
    let acum = 0, largo = 0;
    for (let i = 1; i < N; i++) {
      const a = o[i - 1], b = o[i], c = o[(i + 1) % N];
      const t1 = Math.atan2(b[1] - a[1], b[0] - a[0]), t2 = Math.atan2(c[1] - b[1], c[0] - b[0]);
      let g = t2 - t1; if (g > Math.PI) g -= 2 * Math.PI; if (g < -Math.PI) g += 2 * Math.PI;
      acum += g; largo += Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (Math.abs(acum) > 0.09 || largo > 0.3) { res.push(b); acum = 0; largo = 0; }
    }
    return res;
  }

  function normales(p) {
    const N = p.length, n = [];
    for (let i = 0; i < N; i++) {
      const a = p[(i - 1 + N) % N], b = p[i], c = p[(i + 1) % N];
      let x1 = b[1] - a[1], y1 = -(b[0] - a[0]); const l1 = Math.hypot(x1, y1) || 1; x1 /= l1; y1 /= l1;
      let x2 = c[1] - b[1], y2 = -(c[0] - b[0]); const l2 = Math.hypot(x2, y2) || 1; x2 /= l2; y2 /= l2;
      let x = x1 + x2, y = y1 + y2; const l = Math.hypot(x, y) || 1; x /= l; y /= l;
      const ingl = Math.max(0.55, x * x1 + y * y1);
      n.push([x, y, 1 / ingl]);
    }
    return n;
  }
  const desplazar = (p, n, d) => sinLazos(p.map((q, i) => [q[0] + n[i][0] * d * n[i][2], q[1] + n[i][1] * d * n[i][2]]));

  // Al meter el contorno hacia adentro, en las curvas cerradas se forman lazos chicos: cada lazo se junta en su punto de
  // cruce (mismos índices, para que los anillos del bisel sigan calzando) y la tapa no queda con rendijas.
  function sinLazos(p) {
    const N = p.length, cr = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    for (let vuelta = 0; vuelta < 40; vuelta++) {
      let hubo = false;
      for (let i = 0; i < N && !hubo; i++) {
        const a = p[i], b = p[(i + 1) % N];
        for (let k = 2; k < N / 2 && !hubo; k++) {
          const j = (i + k) % N, c = p[j], d = p[(j + 1) % N];
          const d1 = cr(a, b, c), d2 = cr(a, b, d), d3 = cr(c, d, a), d4 = cr(c, d, b);
          if (d1 * d2 < 0 && d3 * d4 < 0) {
            const t = d3 / (d3 - d4), x = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
            for (let m = 1; m <= k; m++) p[(i + m) % N] = x;
            hubo = true;
          }
        }
      }
      if (!hubo) break;
    }
    return p;
  }

  // Triangulación por orejas (polígono en sentido antihorario, cóncavo).
  function triangular(p) {
    const idx = p.map((_, i) => i), tri = [];
    const cruz = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    const dentro = (q, a, b, c) => cruz(a, b, q) > 1e-12 && cruz(b, c, q) > 1e-12 && cruz(c, a, q) > 1e-12;
    let guardia = 0;
    while (idx.length > 3 && guardia++ < 20000) {
      let corto = false;
      for (let i = 0; i < idx.length; i++) {
        const ia = idx[(i - 1 + idx.length) % idx.length], ib = idx[i], ic = idx[(i + 1) % idx.length];
        const a = p[ia], b = p[ib], c = p[ic];
        if (cruz(a, b, c) <= 1e-9) continue;
        let oreja = true;
        for (const j of idx) {
          if (j === ia || j === ib || j === ic) continue;
          const q = p[j];
          if ((q[0] === a[0] && q[1] === a[1]) || (q[0] === c[0] && q[1] === c[1])) continue;
          if (dentro(q, a, b, c)) { oreja = false; break; }
        }
        if (!oreja) continue;
        tri.push(ia, ib, ic); idx.splice(i, 1); corto = true; break;
      }
      if (!corto) break;
    }
    if (idx.length === 3) tri.push(idx[0], idx[1], idx[2]);
    return tri;
  }

  // Vértices: posición (3), normal (3), cara (1 = frente con rótulo).
  function extruir(d) {
    const base = redondear(leerContorno(d), 0.06);
    const nb = normales(base);
    const borde = desplazar(base, nb, -0.006); // una ranura finísima entre piezas
    const nn = normales(borde);
    const v = [];
    const pon = (x, y, z, a, b, c, f) => v.push(x, y, z, a, b, c, f);
    // Anillos del perfil: frente (bisel redondeado) → canto → espalda.
    const an = [];
    for (let k = 0; k <= SEGB; k++) { const a = (k / SEGB) * Math.PI / 2; an.push([BISEL * (1 - Math.sin(a)), GRUESO - BISEL * (1 - Math.cos(a)), Math.sin(a), Math.cos(a)]); }
    for (let k = SEGB; k >= 0; k--) { const r = an[k]; an.push([r[0], -r[1], r[2], -r[3]]); }
    const anillos = an.map((r) => desplazar(borde, nn, -r[0]));
    const N = borde.length;
    for (let j = 0; j < an.length - 1; j++) {
      const A = anillos[j], B = anillos[j + 1], ra = an[j], rb = an[j + 1];
      for (let i = 0; i < N; i++) {
        const i2 = (i + 1) % N;
        const q = [[A[i], ra, nn[i]], [A[i2], ra, nn[i2]], [B[i2], rb, nn[i2]], [B[i], rb, nn[i]]];
        for (const k of [0, 1, 2, 0, 2, 3]) { const [p, r, n] = q[k]; pon(p[0], p[1], r[1], n[0] * r[2], n[1] * r[2], r[3], 0); }
      }
    }
    // La tapa: el contorno del frente sin los puntos repetidos que dejaron los lazos, triangulado y vuelto a sus índices.
    const frente = anillos[0], unicos = [];
    for (let i = 0; i < N; i++) { const q = frente[i], r = frente[(i + 1) % N]; if (Math.hypot(q[0] - r[0], q[1] - r[1]) > 1e-7) unicos.push(i); }
    const tri = triangular(unicos.map((i) => frente[i])).map((k) => unicos[k]);
    for (let i = 0; i < tri.length; i += 3) {
      for (const k of [tri[i], tri[i + 1], tri[i + 2]]) pon(frente[k][0], frente[k][1], GRUESO, 0, 0, 1, 1);
      for (const k of [tri[i], tri[i + 2], tri[i + 1]]) pon(frente[k][0], frente[k][1], -GRUESO, 0, 0, -1, 0);
    }
    return new Float32Array(v);
  }

  /* ---------- Sombreadores ---------- */
  const VS_PIEZA = `
attribute vec3 a_pos; attribute vec3 a_nor; attribute float a_cara;
uniform mat4 u_proy, u_modelo; uniform mat3 u_normal;
varying vec3 v_nor, v_cam, v_loc; varying float v_cara;
void main(){
  vec4 m = u_modelo * vec4(a_pos, 1.0);
  v_cam = m.xyz; v_nor = u_normal * a_nor; v_loc = a_pos; v_cara = a_cara;
  gl_Position = u_proy * m;
}`;
  const FS_PIEZA = `
precision mediump float;
uniform vec3 u_color; uniform sampler2D u_tex; uniform vec3 u_tile;
uniform float u_comp, u_aparece, u_brillo, u_barrido; uniform vec2 u_desp; uniform vec3 u_luz;
varying vec3 v_nor, v_cam, v_loc; varying float v_cara;
const vec3 AMBAR = vec3(1.0, 0.69, 0.125);
void main(){
  vec3 n = normalize(v_nor); if (!gl_FrontFacing) n = -n;
  vec3 v = normalize(-v_cam);
  float fres = pow(1.0 - clamp(dot(n, v), 0.0, 1.0), 3.0);
  // El barrido de «compilar»: de abajo hacia arriba, inclinado; arriba sigue en alambre.
  float y = v_loc.y + v_loc.z * 0.8 + v_loc.x * 0.18;
  float s = mix(-0.9, 0.95, u_comp);
  float banda = 1.0 - smoothstep(0.0, 0.05, abs(y - s));
  if (y > s) {
    vec3 g = abs(fract(v_loc * vec3(9.0, 9.0, 9.0) + 0.5) - 0.5);
    float linea = 1.0 - smoothstep(0.035, 0.07, min(g.x, g.y));
    float a = max(linea * 0.75, smoothstep(0.25, 0.75, fres)) * u_aparece;
    a = max(a, banda * u_aparece);
    if (a < 0.03) discard;
    vec3 c = mix(AMBAR, vec3(1.0, 0.93, 0.75), banda) * (0.75 + banda);
    gl_FragColor = vec4(c * a, a);
    return;
  }
  vec3 alb = u_color;
  if (v_cara > 0.5) {
    vec2 uv = u_tile.xy + (v_loc.xy / 1.5 + 0.5) * u_tile.z;
    float tinta = texture2D(u_tex, uv).a;
    float alto = texture2D(u_tex, uv + vec2(-0.0012, 0.0012)).a;
    alb = mix(alb, vec3(0.17, 0.12, 0.05), tinta * 0.9);
    alb += vec3(1.0, 0.85, 0.6) * clamp(alto - tinta, 0.0, 1.0) * 0.25; // labio del grabado
  } else {
    alb = mix(alb, vec3(0.72, 0.42, 0.02), 0.45 * (1.0 - abs(n.z)));
  }
  vec3 L = normalize(u_luz);
  float dif = max(dot(n, L), 0.0);
  float rel = max(dot(n, normalize(vec3(0.7, -0.4, 0.4))), 0.0) * 0.22;
  vec3 h = normalize(L + v);
  float esp = pow(max(dot(n, h), 0.0), 60.0) * 0.5;
  vec3 c = alb * (0.24 + 0.86 * dif + rel) + vec3(1.0, 0.95, 0.85) * esp;
  c += AMBAR * fres * (0.28 + u_brillo * 1.4);
  // Destello que cruza el conjunto armado, en diagonal, de vez en cuando.
  float d = dot(v_loc.xy + u_desp, vec2(0.707, 0.707));
  c += vec3(1.0, 0.92, 0.75) * exp(-pow((d - u_barrido) * 5.0, 2.0)) * 0.16 * step(0.5, v_cara);
  c = mix(c, vec3(1.0, 0.93, 0.75), banda * 0.8);
  gl_FragColor = vec4(c, 1.0);
}`;
  const VS_PISO = `
attribute vec2 a_pos; uniform mat4 u_proy, u_modelo; varying vec2 v_p;
void main(){ v_p = a_pos; gl_Position = u_proy * u_modelo * vec4(a_pos, 0.0, 1.0); }`;
  const FS_PISO = `
precision mediump float;
uniform vec4 u_sombra[9]; uniform float u_ranura[9]; uniform float u_aparece; uniform vec2 u_luz;
varying vec2 v_p;
void main(){
  float r = length(v_p * vec2(0.9, 1.0));
  float lejos = 1.0 - smoothstep(1.5, 3.4, r);
  float rev = 1.0 - smoothstep(u_aparece * 3.6 - 0.35, u_aparece * 3.6, r);
  vec2 g = abs(fract(v_p * 4.0) - 0.5) / 4.0;
  float menor = 1.0 - smoothstep(0.0025, 0.0075, 0.125 - max(g.x, g.y));
  vec2 G = abs(fract(v_p + 0.5) - 0.5);
  float mayor = 1.0 - smoothstep(0.004, 0.012, 0.5 - max(G.x, G.y));
  vec2 nodo = abs(fract(v_p * 4.0 + 0.5) - 0.5);
  float punto = 1.0 - smoothstep(0.02, 0.05, length(nodo));
  float frente = smoothstep(0.35, 0.0, abs(r - u_aparece * 3.6)) * step(u_aparece, 0.999);
  float a = (menor * 0.06 + mayor * 0.15 + punto * 0.12) * lejos * rev + frente * mayor * 0.5;
  float sh = 0.0, ran = 0.0;
  for (int i = 0; i < 9; i++) {
    vec4 s = u_sombra[i];
    vec2 q = abs(v_p - s.xy - u_luz * s.z) - vec2(0.43);
    float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
    float b = 0.05 + s.z * 0.22;
    sh = max(sh, (1.0 - smoothstep(-b, b, d)) * s.w / (1.0 + s.z * 1.4));
    vec2 q2 = abs(v_p - s.xy) - vec2(0.47);
    float d2 = abs(length(max(q2, 0.0)) + min(max(q2.x, q2.y), 0.0));
    ran = max(ran, (1.0 - smoothstep(0.0, 0.02, d2)) * u_ranura[i]);
  }
  a = max(a, ran * 0.8);
  float k = sh * 0.62 * rev;
  vec3 c = vec3(1.0, 0.69, 0.125) * a;
  gl_FragColor = vec4(c * (1.0 - k), a + k * (1.0 - a));
}`;

  function programa(vs, fs) {
    const mk = (tipo, src) => { const s = gl.createShader(tipo); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS) && !gl.isContextLost()) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const p = gl.createProgram();
    gl.attachShader(p, mk(gl.VERTEX_SHADER, vs)); gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS) && !gl.isContextLost()) throw new Error(gl.getProgramInfoLog(p));
    const u = {}, n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const nom = gl.getActiveUniform(p, i).name.replace(/\[0\]$/, ""); u[nom] = gl.getUniformLocation(p, nom); }
    return { p, u, a: (nom) => gl.getAttribLocation(p, nom) };
  }

  /* ---------- Las piezas: rótulos del HTML, íconos de la página, de dónde llegan ---------- */
  const ICONOS = ["iconos/piezas/ia.svg", "iconos/piezas/i18n.svg", "iconos/piezas/actualizaciones.svg", "iconos/piezas/bienvenida.svg",
    "img/pieza.svg", "iconos/piezas/tema.svg", "iconos/piezas/catalogo.svg", "iconos/piezas/notas-git.svg", "iconos/piezas/cifrado.svg"];
  const COLORES = ["#ffb020", "#ffc04a", "#f7a400", "#ffc65a", "#ffb020", "#ffbb3c", "#f7a400", "#ffc65a", "#ffb020"];
  // Desde dónde llega cada una (unidades de pieza) y cómo viene girada.
  const DESDE = [[-2.6, 2.2, 2.4, 2.2, -1.4, -1.6], [0.3, 3.0, 1.8, -2.4, 0.7, 1.0], [2.8, 2.2, 2.6, 1.6, 2.0, 0.5],
    [-3.2, 0.2, 1.6, -1.1, -2.4, 2.1], [0, 0, 3.2, 3.1, 0, -0.8], [3.1, -0.3, 1.8, 1.2, -1.7, -2.4],
    [-2.5, -2.4, 2.2, -1.9, 1.0, 1.4], [0.4, -3.0, 2.0, 2.6, -0.5, -1.9], [2.7, -2.3, 2.6, -1.4, -2.8, 2.6]];
  const ORDEN = [4, 0, 1, 2, 3, 5, 6, 7, 8]; // primero tu app, después lo que se le enchufa

  const piezas = [];
  let progP, progS, bufPiso, textura, tile = 0.25, listo = false;

  function hex(c) { return [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16) / 255); }

  function iniciarGL() {
    progP = programa(VS_PIEZA, FS_PIEZA);
    progS = programa(VS_PISO, FS_PISO);
    for (let i = 0; i < 9; i++) {
      const datos = extruir(CONTORNOS[i]);
      const b = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, datos, gl.STATIC_DRAW);
      const col = i % 3, fila = Math.floor(i / 3);
      piezas.push({ buf: b, n: datos.length / 7, color: new Float32Array(hex(COLORES[i])), x: col - 1, y: 1 - fila, desde: DESDE[i] });
    }
    bufPiso = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, bufPiso);
    const L = 3.8;
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-L, -L, L, -L, L, L, -L, -L, L, L, -L, L]), gl.STATIC_DRAW);
    textura = gl.createTexture();
    pintarRotulos();
    listo = true;
  }

  // Rótulos e íconos en una textura (atlas 4×4, potencia de dos para tener mipmaps y que se lean nítidos de lado).
  const imagenes = ICONOS.map((src) => { const im = new Image(); im.decoding = "async"; im.src = src; im.addEventListener("load", () => { if (listo) { pintarRotulos(); pedirCuadro(); } }, { once: true }); return im; });
  function pintarRotulos() {
    const lado = angosto.matches ? 1024 : 2048, t = lado / 4;
    const c = document.createElement("canvas"); c.width = c.height = lado;
    const x = c.getContext("2d");
    const textos = [...escena.querySelectorAll(".pz .rotulo")].map((r) => r.textContent.trim());
    const letra = getComputedStyle(document.body).fontFamily;
    for (let i = 0; i < 9; i++) {
      const ox = (i % 4) * t, oy = Math.floor(i / 4) * t, cx = ox + t / 2, cy = oy + t / 2;
      const u = t / 1.5; // una unidad de pieza en la textura
      // Ícono arriba y rótulo abajo: así ninguno cae en los huecos de los lados (que están a media altura).
      const im = imagenes[i], ti = u * 0.22;
      let hay = false;
      if (im.complete && im.naturalWidth !== 0) {
        try { x.drawImage(im, cx - ti / 2, cy - u * 0.13 - ti / 2, ti, ti); hay = true; } catch (e) { hay = false; }
      }
      let px = Math.round(u * 0.125);
      x.font = "800 " + px + "px " + letra;
      const w = x.measureText(textos[i] || "").width, max = u * 0.8;
      if (w > max) { px = Math.floor((px * max) / w); x.font = "800 " + px + "px " + letra; }
      x.fillStyle = "#000"; x.textAlign = "center"; x.textBaseline = "middle";
      x.fillText(textos[i] || "", cx, hay ? cy + u * 0.17 : cy);
    }
    gl.bindTexture(gl.TEXTURE_2D, textura);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, c);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    const an = gl.getExtension("EXT_texture_filter_anisotropic");
    if (an) gl.texParameterf(gl.TEXTURE_2D, an.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(8, gl.getParameter(an.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));
    tile = 0.25;
  }

  /* ---------- La terminal (HTML de index.html, textos con data-t) ---------- */
  const lineas = [...escena.querySelectorAll(".consola li[data-pieza]")];
  const lineaFin = escena.querySelector(".consola li.fin");
  const TECLA = 0.018, PAUSA = 0.11, VUELO = 0.95;
  let guion = [];
  function armarGuion() {
    // Cada comando se escribe, se «ejecuta» y su pieza llega; la siguiente se escribe mientras la anterior vuela.
    let t = 0.5;
    guion = ORDEN.map((p) => {
      const li = lineas.find((l) => Number(l.dataset.pieza) === p);
      const cmd = li && li.querySelector(".cmd");
      const largo = cmd ? cmd.textContent.length : 18;
      const paso = { p, li, cmd, largo, escribe: t, enter: t + largo * TECLA };
      t = paso.enter + PAUSA;
      return paso;
    });
  }
  function terminal(t) {
    for (const g of guion) {
      if (!g.li) continue;
      const ve = t >= g.escribe, n = Math.max(0, Math.min(g.largo, Math.floor((t - g.escribe) / TECLA)));
      const hecha = t >= g.enter + VUELO * 0.82;
      g.li.classList.toggle("ve", ve);
      g.li.classList.toggle("escribe", ve && t < g.enter);
      g.li.classList.toggle("corre", t >= g.enter && !hecha);
      g.li.classList.toggle("hecha", hecha);
      if (g.cmd && g._n !== n) { g._n = n; g.cmd.style.setProperty("--n", String(n)); }
    }
    if (lineaFin) lineaFin.classList.toggle("ve", t >= finTotal());
  }
  const finTotal = () => guion.length ? guion[guion.length - 1].enter + VUELO + 0.25 : 0;

  /* ---------- Animación ---------- */
  const ease = (x) => 1 - Math.pow(1 - x, 3);
  const sstep = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  let tiempo = 0, ultimo = 0, cuadro = 0, visible = true, empezo = false, mx = 0, my = 0, px = 0, py = 0, ancho = 0, alto = 0;
  let medidas = [], cpu = [], vigilando = true;
  const guardia = !window.__pieza3dSinGuardia; // las pruebas con render por software la apagan

  function medir() {
    const r = lienzo.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, angosto.matches ? 1.5 : 2);
    ancho = Math.max(1, Math.round(r.width * dpr)); alto = Math.max(1, Math.round(r.height * dpr));
    if (lienzo.width !== ancho || lienzo.height !== alto) { lienzo.width = ancho; lienzo.height = alto; }
  }

  const sombras = new Float32Array(36), ranuras = new Float32Array(9);
  function dibujar(t) {
    if (!listo || gl.isContextLost()) return;
    gl.viewport(0, 0, ancho, alto);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    const asp = ancho / alto, chico = angosto.matches;
    const fov = 0.52;
    // Distancia para que el conjunto (≈3,4 de ancho) quepa con aire en cualquier proporción.
    const D = Math.max(4.1 / Math.tan(fov / 2) / 2, (4.1 / asp) / Math.tan(fov / 2) / 2) * (chico ? 0.98 : 1.04);
    const proy = persp(fov, asp, 0.1, 60);
    const fin = finTotal(), armado = t >= fin;
    const flota = quieto.matches ? 0 : Math.sin(t * 0.55) * 0.035;
    const gira = quieto.matches ? 0 : Math.sin(t * 0.32) * 0.05;
    const G = mul(mul(mul(mul(tras(0, (chico ? 0.42 : 0.62) + flota, -D), rotX(-0.62 + py * 0.16)), rotY(0.3 + gira + px * 0.24)), rotZ(0.1)), m4());
    const luz = [-0.45, 0.75, 0.6];

    // Piso: la rejilla que se «compila» primero, las sombras y la ranura donde va a caer cada pieza.
    const est = guion.map((g) => {
      const u = Math.max(0, Math.min(1, (t - g.enter) / VUELO));
      return { g, u, antes: t < g.enter };
    });
    for (const e of est) {
      const pz = piezas[e.g.p], i = e.g.p, k = ease(e.u);
      const h = e.antes ? 3 : (1 - k) * pz.desde[2];
      sombras[i * 4] = pz.x + (1 - k) * pz.desde[0] * 0.5; sombras[i * 4 + 1] = pz.y + (1 - k) * pz.desde[1] * 0.5;
      sombras[i * 4 + 2] = h; sombras[i * 4 + 3] = e.antes ? 0 : sstep(0.1, 0.6, e.u);
      ranuras[i] = e.antes ? (t > e.g.escribe ? 0.6 : 0) : (1 - sstep(0.7, 1, e.u)) * 0.9;
    }
    gl.useProgram(progS.p);
    const MP = mul(G, tras(0, 0, -0.62));
    gl.uniformMatrix4fv(progS.u.u_proy, false, proy);
    gl.uniformMatrix4fv(progS.u.u_modelo, false, MP);
    gl.uniform4fv(progS.u.u_sombra, sombras);
    gl.uniform1fv(progS.u.u_ranura, ranuras);
    gl.uniform1f(progS.u.u_aparece, sstep(0.0, 0.9, t + (quieto.matches ? 9 : 0)));
    gl.uniform2f(progS.u.u_luz, 0.16, -0.2);
    gl.depthMask(false);
    gl.bindBuffer(gl.ARRAY_BUFFER, bufPiso);
    const ap = progS.a("a_pos");
    gl.enableVertexAttribArray(ap);
    gl.vertexAttribPointer(ap, 2, gl.FLOAT, false, 8, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.disableVertexAttribArray(ap);
    gl.depthMask(true);

    // Piezas.
    gl.useProgram(progP.p);
    gl.uniformMatrix4fv(progP.u.u_proy, false, proy);
    gl.uniform3fv(progP.u.u_luz, luz);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, textura);
    gl.uniform1i(progP.u.u_tex, 0);
    const brilloFinal = armado ? Math.exp(-(t - fin) * 2.2) : 0;
    const per = 7.5, fase = armado && !quieto.matches ? ((t - fin) % per) / per : -1;
    gl.uniform1f(progP.u.u_barrido, fase < 0 ? -9 : -3 + fase * 9);
    const aPos = progP.a("a_pos"), aNor = progP.a("a_nor"), aCara = progP.a("a_cara");
    gl.enableVertexAttribArray(aPos); gl.enableVertexAttribArray(aNor); gl.enableVertexAttribArray(aCara);
    for (const e of est) {
      if (e.antes) continue;
      const pz = piezas[e.g.p], d = pz.desde, u = e.u, k = ease(u);
      // Encaje: llega un poco por encima y baja con un pequeño rebote al calzar.
      const dt = t - (e.g.enter + VUELO);
      const clic = dt > 0 ? Math.exp(-dt * 7) * Math.sin(dt * 22) * 0.035 : 0;
      const z = (1 - k) * d[2] + (u < 1 ? (1 - sstep(0.75, 1, u)) * 0.12 * k : 0) - clic;
      const x = pz.x + (1 - k) * d[0], y = pz.y + (1 - k) * d[1];
      const r = 1 - ease(Math.min(1, u * 1.05));
      const M = mul(G, mul(tras(x, y, z), mul(rotZ(d[5] * r), mul(rotY(d[4] * r), rotX(d[3] * r)))));
      gl.uniformMatrix4fv(progP.u.u_modelo, false, M);
      gl.uniformMatrix3fv(progP.u.u_normal, false, normal3(M));
      gl.uniform3fv(progP.u.u_color, pz.color);
      const i = e.g.p;
      gl.uniform3f(progP.u.u_tile, (i % 4) * tile, 1 - (Math.floor(i / 4) + 1) * tile, tile);
      gl.uniform1f(progP.u.u_comp, sstep(0.42, 0.98, u));
      gl.uniform1f(progP.u.u_aparece, sstep(0, 0.22, u));
      gl.uniform1f(progP.u.u_brillo, (dt > 0 ? Math.exp(-dt * 4) * 0.9 : 0) + brilloFinal * 0.7);
      gl.uniform2f(progP.u.u_desp, pz.x, pz.y);
      gl.bindBuffer(gl.ARRAY_BUFFER, pz.buf);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 28, 0);
      gl.vertexAttribPointer(aNor, 3, gl.FLOAT, false, 28, 12);
      gl.vertexAttribPointer(aCara, 1, gl.FLOAT, false, 28, 24);
      gl.drawArrays(gl.TRIANGLES, 0, pz.n);
    }
    gl.disableVertexAttribArray(aPos); gl.disableVertexAttribArray(aNor); gl.disableVertexAttribArray(aCara);
  }

  function bucle(ahora) {
    cuadro = 0;
    if (!corriendo()) return;
    const dt = ultimo ? Math.min(0.1, (ahora - ultimo) / 1000) : 1 / 60;
    // En celular, ya armado, basta la mitad de cuadros para flotar: menos batería.
    if (angosto.matches && tiempo > finTotal() + 1 && ahora - ultimo < 30) { cuadro = requestAnimationFrame(bucle); return; }
    if (vigilando && ultimo && tiempo > 1.6 && ahora - ultimo < 1000 && document.hasFocus()) {  // un salto largo es la pestaña dormida, no un equipo lento
      // Se mide cuando ya hay varias piezas en vuelo (lo más pesado). Si el equipo no da abasto (render por software,
      // GPU muy lenta), vuelve al rompecabezas CSS.
      medidas.push(ahora - ultimo);
      if (medidas.length >= 45) {
        vigilando = false;
        const orden = medidas.slice().sort((a, b) => a - b), mediana = orden[orden.length >> 1];
        window.__pieza3d = { mediana, cpu: cpu.slice().sort((a, b) => a - b)[cpu.length >> 1] };
        if (guardia && mediana > 70) { sinGL(); return; }
      }
    }
    ultimo = ahora;
    px += (mx - px) * 0.06; py += (my - py) * 0.06;
    tiempo += dt;
    const t0 = performance.now();
    terminal(tiempo);
    dibujar(tiempo);
    if (cpu.length < 600) cpu.push(performance.now() - t0);
    cuadro = requestAnimationFrame(bucle);
  }
  const corriendo = () => empezo && visible && !document.hidden && !quieto.matches;
  function seguir() { if (!cuadro && corriendo()) { ultimo = 0; cuadro = requestAnimationFrame(bucle); } }
  function detener() { if (cuadro) cancelAnimationFrame(cuadro); cuadro = 0; }
  let pedido = 0;
  function pedirCuadro() {
    // Un cuadro suelto (sin animar): movimiento reducido, cambio de idioma o de tamaño.
    if (cuadro || pedido) return;
    pedido = requestAnimationFrame(() => { pedido = 0; medir(); terminal(quieto.matches ? 1e9 : tiempo); dibujar(quieto.matches ? 1e9 : tiempo); });
  }

  /* ---------- Arranque ---------- */
  try {
    escena.classList.add("gl");
    medir();
    iniciarGL();
    armarGuion();
  } catch (e) {
    sinGL();
    return;
  }
  lienzo.addEventListener("webglcontextlost", (e) => { e.preventDefault(); sinGL(); });
  // ¿Se ve? El observador puede quedarse con un «no» si la página cargó oculta (pestaña de fondo, panel cerrado) y no volver a
  // avisar: por eso, ante cualquier señal (tamaño, foco, visibilidad), se vuelve a mirar la posición real del lienzo.
  const enPantalla = () => { const r = lienzo.getBoundingClientRect(); return r.width > 0 && r.bottom > 0 && r.top < innerHeight; };
  const revisar = () => { visible = enPantalla(); seguir(); if (!cuadro) pedirCuadro(); };
  new ResizeObserver(() => { medir(); revisar(); }).observe(lienzo);
  new IntersectionObserver((e) => { visible = e[0].isIntersecting || enPantalla(); if (visible) seguir(); }).observe(lienzo);
  document.addEventListener("visibilitychange", revisar);
  window.addEventListener("focus", revisar);
  window.addEventListener("pageshow", revisar);
  window.addEventListener("resize", revisar, { passive: true });
  window.addEventListener("pointermove", (e) => {
    mx = e.clientX / window.innerWidth - 0.5; my = e.clientY / window.innerHeight - 0.5;
  }, { passive: true });
  quieto.addEventListener("change", () => { if (quieto.matches) { detener(); pedirCuadro(); } else seguir(); });
  // Al cambiar el idioma (pagina.js cambia lang y los data-t), los rótulos de la textura y la terminal se rehacen.
  new MutationObserver(() => { if (!listo) return; pintarRotulos(); armarGuion(); for (const g of guion) g._n = -1; pedirCuadro(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });

  function partir() {
    empezo = true;
    visible = enPantalla() || visible;
    if (quieto.matches) { pedirCuadro(); return; }
    seguir();
  }
  if (quieto.matches) { empezo = true; pedirCuadro(); return; }
  // Como el rompecabezas CSS: parte cuando la página ya cargó (fuentes incluidas), sin competir con la carga; máximo 1,2 s.
  const fuentes = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
  const cargada = document.readyState === "complete" ? Promise.resolve() : new Promise((r) => window.addEventListener("load", r, { once: true }));
  Promise.race([Promise.all([fuentes, cargada]), new Promise((r) => setTimeout(r, 1200))]).then(() => {
    // Los íconos ya cargaron: rótulos completos antes del primer cuadro.
    pintarRotulos();
    requestAnimationFrame(partir);
  });
})();
