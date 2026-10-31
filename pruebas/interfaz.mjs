// Pruebas de las piezas de interfaz (host-ui, tema y componentes) en un navegador de verdad: Chromium con Playwright, una página
// servida con la misma CSP que las apps (script-src 'self'; style-src 'self') y una app mínima de mentira, «Prueba».
//   PLAYWRIGHT=/ruta/a/playwright node pruebas/interfaz.mjs     (o con playwright en NODE_PATH)
// Revisa: sin errores ni violaciones de CSP, ningún texto sin traducir en inglés, foco del diálogo (entra, Tab da la vuelta, Esc
// y el velo cierran, vuelve al botón), confirmar, cola de avisos, crearHost en el navegador (simular), tema elegido y del sistema,
// contraste AA de los tokens en claro y oscuro (los de la pieza y los pares de cada app del README de tema), 44 px y hoja desde
// abajo a 390 px, y movimiento reducido.
import { createRequire } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const BASE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");

// ── La página: los archivos de las piezas + una app mínima, sin nada en línea ──
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pieza-ui-"));
const copiar = (de, a) => fs.copyFileSync(path.join(BASE, de), path.join(dir, a));
copiar("piezas/i18n/ui/i18n.js", "i18n.js");
copiar("piezas/host-ui/ui/host.js", "host.js");
copiar("piezas/tema/ui/tema.js", "tema.js");
copiar("piezas/tema/ui/tema.css", "tema.css");
copiar("piezas/componentes/ui/componentes.js", "componentes.js");
copiar("piezas/componentes/ui/componentes.css", "componentes.css");
const textos = { "Ajustes": "Settings", "Listo": "Done", "Tu IA": "Your AI", "Abrir": "Open", "Un botón": "A button" };
for (const p of ["host-ui", "tema", "componentes", "actualizaciones"]) Object.assign(textos, JSON.parse(fs.readFileSync(path.join(BASE, "piezas", p, "pieza.json"), "utf8")).textos);
fs.mkdirSync(path.join(dir, "idiomas"));
fs.writeFileSync(path.join(dir, "idiomas", "en.json"), JSON.stringify({ codigo: "en", nombre: "English", textos }));
fs.writeFileSync(path.join(dir, "index.html"), `<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Prueba</title>
<link rel="stylesheet" href="tema.css"><link rel="stylesheet" href="componentes.css"></head>
<body><div id="app"></div><div id="toast" role="status" aria-live="polite"></div>
<script src="i18n.js"></script><script src="host.js"></script><script src="tema.js"></script><script src="componentes.js"></script><script src="prueba.js"></script></body></html>`);
fs.writeFileSync(path.join(dir, "prueba.js"), `"use strict";
window._faltantes = new Set();
const i18n = PiezaI18n.crear({ faltantes: window._faltantes });
const E = { ajustes: false, ia: null, enlaces: [] };
const IAS = [{ id: "claude", nombre: "Claude Code", instalada: true }, { id: "codex", nombre: "Codex <i>", instalada: false }];
const host = PiezaHost.crearHost({ nombre: "prueba", global: "Prueba", simular: {
  ...PiezaHost.simulacionesComunes({ espera: 40 }),
  config: (d) => { if (d.ia) E.ia = d.ia; },
  abrirEnlace: (d) => { E.enlaces.push(d.url); },
} });
const raiz = document.getElementById("app");
const ui = PiezaComponentes.crear({ i18n, host, app: "Prueba", repo: "ana-app/ana", version: "1.0", pintar, duracion: 300, pausa: 50,
  cerrar: () => { E.ajustes = false; pintar(); } });
const tema = PiezaTema.crear({ guardar: (v) => host.enviar("config", { tema: v }) });
host.responder({ iaProbada: (r) => ui.iaProbada(r), actualizacionRevisada: (r) => ui.actualizacionRevisada(r), actualizacionProgreso: (a) => ui.actualizacionProgreso(a) });
function ajustes() {
  return "<h3>Apariencia</h3>" + tema.selectorHTML() + "<h3>Tu IA</h3>" + ui.filasIA({ ias: IAS, elegida: E.ia, guia: "https://ana-app.github.io/ana/ia.html" })
    + ui.filaActualizacion() + ui.acercaDe({ version: "1.0", enlaces: { codigo: "https://github.com/ana-app/ana" } });
}
function pintar() {
  raiz.innerHTML = '<main><button type="button" class="pz-boton" id="abrir">Ajustes</button> <button type="button" class="pz-boton" data-otro="1">Un botón</button></main>'
    + (E.ajustes ? ui.dialogo({ id: "t-aj", titulo: "Ajustes", cuerpo: ajustes(), pie: '<button type="button" class="pz-boton pz-principal" id="listo" data-pz-cerrar data-autofoco>Listo</button>' }) : "")
    + ui.capas();
  i18n.traducirDOM(raiz);
  ui.despuesDePintar();
}
document.addEventListener("click", (ev) => {
  if (tema.manejarClic(ev)) return pintar();
  if (ui.manejarClic(ev)) return;
  if (ev.target.closest("#abrir")) { E.ajustes = true; pintar(); }
});
document.addEventListener("keydown", (ev) => { ui.manejarTecla(ev); });
window.prueba = { ui, tema, host, i18n, pintar, E };
(async () => {
  await i18n.cargar(i18n.elegir({}));
  tema.aplicar(tema.elegir({}));
  pintar();
  window.listo = true;
})();
`);
// Los pares de cada app, tal como los dice el README de tema.
const README = fs.readFileSync(path.join(BASE, "piezas/tema/README.md"), "utf8");
const paletas = [...README.matchAll(/```css\n\/\* app: (\w+) \*\/\n([\s\S]*?)```/g)].map((m) => ({ app: m[1], css: m[2] }));
assert.ok(paletas.length >= 5, "el README de tema trae los pares de cada app");
for (const p of paletas) fs.writeFileSync(path.join(dir, `paleta-${p.app}.css`), p.css);

const TIPOS = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };
const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'";
const servidor = http.createServer((req, res) => {
  const ruta = path.join(dir, decodeURIComponent(new URL(req.url, "http://x").pathname).replace(/^\/+/, "") || "index.html");
  if (!ruta.startsWith(dir) || !fs.existsSync(ruta) || fs.statSync(ruta).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": TIPOS[path.extname(ruta)] || "text/plain", "Content-Security-Policy": CSP });
  fs.createReadStream(ruta).pipe(res);
});
await new Promise((r) => servidor.listen(0, "127.0.0.1", r));
const URL_BASE = `http://127.0.0.1:${servidor.address().port}/index.html`;

// ── Contraste ──
const lum = ([r, g, b]) => { const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
const contraste = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
const PARES = [["texto", "fondo"], ["texto", "panel"], ["texto", "panel-2"], ["texto-suave", "fondo"], ["texto-suave", "panel"], ["texto-suave", "panel-2"],
  ["acento", "panel"], ["acento", "fondo"], ["sobre-acento", "acento"], ["rojo", "fondo"], ["rojo", "panel"], ["verde", "fondo"], ["verde", "panel"], ["fondo", "texto"]];
async function colores(page) {
  return page.evaluate((tokens) => {
    const el = document.createElement("i");
    document.body.appendChild(el);
    const r = {};
    for (const t of tokens) {
      el.style.setProperty("color", `var(--${t})`);      // CSSOM: lo permite style-src 'self'
      r[t] = getComputedStyle(el).color.match(/[\d.]+/g).slice(0, 3).map(Number);
    }
    el.remove();
    return r;
  }, ["fondo", "panel", "panel-2", "texto", "texto-suave", "acento", "sobre-acento", "rojo", "verde"]);
}
async function revisarContraste(page, donde) {
  const malos = [];
  for (const modo of ["claro", "oscuro"]) {
    await page.evaluate((m) => window.prueba.tema.aplicar(m), modo);
    const c = await colores(page);
    for (const [a, b] of PARES) { const x = contraste(c[a], c[b]); if (x < 4.5) malos.push(`${donde} ${modo}: --${a} sobre --${b} = ${x.toFixed(2)}`); }
  }
  return malos;
}

const navegador = await chromium.launch();
let fallas = 0;
async function caso(nombre, f) {
  const contexto = await navegador.newContext({ viewport: { width: 1100, height: 760 } });
  const page = await contexto.newPage();
  const errores = [];
  page.on("pageerror", (e) => errores.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" || /Content Security Policy/.test(m.text())) errores.push(m.text()); });
  try {
    await f(page, contexto);
    assert.deepEqual(errores, [], "sin errores ni violaciones de la CSP");
    console.log(`✓ ${nombre}`);
  } catch (e) {
    fallas++;
    console.log(`✗ ${nombre}\n  ${String(e.stack || e).split("\n").slice(0, 6).join("\n  ")}`);
  } finally { await contexto.close(); }
}
const abrir = async (page, q = "") => { await page.goto(URL_BASE + q); await page.waitForFunction(() => window.listo === true); };
const activo = (page) => page.evaluate(() => ({ id: document.activeElement?.id || "", dentro: !!document.activeElement?.closest('[role="dialog"],[role="alertdialog"]'), texto: document.activeElement?.textContent?.trim() || "" }));

await caso("diálogo: el foco entra, Tab y Mayús+Tab dan la vuelta adentro, Esc cierra y el foco vuelve", async (page) => {
  await abrir(page);
  await page.click("#abrir");
  assert.equal((await activo(page)).id, "listo", "el foco va a [data-autofoco]");
  const n = await page.locator('[role="dialog"] button:not([disabled])').count();
  for (let i = 0; i < n + 3; i++) { await page.keyboard.press("Tab"); assert.equal((await activo(page)).dentro, true, `Tab ${i + 1} sigue adentro`); }
  await page.locator('[role="dialog"] [data-pz-cerrar].pz-cerrar').focus();
  await page.keyboard.press("Shift+Tab");
  assert.equal((await activo(page)).id, "listo", "Mayús+Tab desde el primero va al último");
  await page.keyboard.press("Tab");
  assert.match((await activo(page)).texto, /✕/, "Tab desde el último vuelve al primero");
  await page.keyboard.press("Escape");
  assert.equal(await page.locator('[role="dialog"]').count(), 0);
  assert.equal((await activo(page)).id, "abrir", "el foco vuelve al botón que lo abrió");
  await page.click("#abrir");
  await page.mouse.click(5, 5);   // el velo
  assert.equal(await page.locator('[role="dialog"]').count(), 0, "el velo cierra");
});

await caso("confirmar: Esc es «no», el botón principal es «sí», el foco en «sí»", async (page) => {
  await abrir(page);
  await page.evaluate(() => { window.r1 = window.prueba.ui.confirmar({ titulo: "¿Borrar «{x}»?", valores: { x: "<b>nota</b>" }, si: "Aceptar", peligro: true }); });
  assert.equal(await page.locator('[role="alertdialog"] h2 b').count(), 0, "el valor va escapado");
  assert.match(await page.locator('[role="alertdialog"] h2').innerText(), /<b>nota<\/b>/);
  assert.equal(await page.evaluate(() => document.activeElement.dataset.pzConfirmar), "si");
  await page.keyboard.press("Escape");
  assert.equal(await page.evaluate(() => window.r1), false);
  await page.evaluate(() => { window.r2 = window.prueba.ui.confirmar({ titulo: "¿Seguro?" }); });
  await page.click('[data-pz-confirmar="si"]');
  assert.equal(await page.evaluate(() => window.r2), true);
  assert.equal(await page.locator('[role="alertdialog"]').count(), 0);
});

await caso("avisos: en cola, de a uno, sin repetir, como texto", async (page) => {
  await abrir(page, "?idioma=es");
  await page.evaluate(() => { const u = window.prueba.ui; u.aviso("Uno <b>", { traducido: true, duracion: 250 }); u.aviso("Uno <b>", { traducido: true }); u.aviso("Dos", { traducido: true, duracion: 250 }); u.aviso("Lista para usar"); });
  const toast = page.locator("#toast");
  assert.equal(await toast.textContent(), "Uno <b>");
  assert.equal(await page.locator("#toast b").count(), 0);
  assert.match(await toast.getAttribute("class"), /pz-toast visible/);
  const vistos = await page.evaluate(() => new Promise((ok) => { const v = []; const t = document.getElementById("toast");
    const m = new MutationObserver(() => { v.push(t.textContent); if (v.includes("Lista para usar")) { m.disconnect(); ok(v); } });
    m.observe(t, { childList: true, characterData: true, subtree: true }); setTimeout(() => ok(v), 4000); }));
  assert.deepEqual(vistos, ["Dos", "Lista para usar"]);
  assert.deepEqual(await page.evaluate(() => window.prueba.ui.avisos.enCola), []);
});

await caso("crearHost en el navegador: probar la IA con la simulación, todo en inglés y sin frases sin traducir", async (page) => {
  await abrir(page, "?idioma=en");
  assert.equal(await page.evaluate(() => document.documentElement.dataset.host), "web");
  await page.click("#abrir");
  assert.equal(await page.locator("#t-aj").innerText(), "Settings");
  await page.click('[data-pz-probar-ia="claude"]');
  assert.equal(await page.locator('[data-pz-probar-ia="claude"]').innerText(), "Testing…");
  await page.waitForSelector(".pz-ok");
  assert.equal(await page.locator(".pz-ok").innerText(), "Ready");
  assert.equal(await page.evaluate(() => window.prueba.E.ia), "claude", "quedó elegida por config {ia}");
  await page.waitForFunction(() => document.getElementById("toast").textContent === "Ready to use");
  assert.match(await page.locator(".pz-filas").innerText(), /Codex <i>[\s\S]*Not installed · How to install it/);
  await page.click('[data-pz-act="buscar"]');
  await page.waitForFunction(() => /latest version/.test(document.querySelector(".pz-act").textContent));
  await page.click('[data-pz-comentarios]');
  assert.equal(await page.locator("#pz-t-coment").innerText(), "Send feedback");
  await page.click("[data-pz-coment-enviar]");
  assert.equal(await page.evaluate(() => document.activeElement.id), "pz-coment-titulo", "sin título, el foco vuelve al campo");
  await page.fill("#pz-coment-titulo", "Falla <b>");
  await page.fill("#pz-coment-texto", "Pasa esto");
  await page.click("[data-pz-coment-enviar]");
  const [url] = await page.evaluate(() => window.prueba.E.enlaces);
  assert.match(url, /^https:\/\/github\.com\/ana-app\/ana\/issues\/new\?title=%F0%9F%90%9E%20Falla%20%3Cb%3E&body=Pasa%20esto%0A%0A---%0APrueba%201\.0%20%C2%B7%20en%20%C2%B7%20Navegador&labels=error$/);
  await page.click('[data-pz-tema="oscuro"]');
  assert.deepEqual(await page.evaluate(() => [...window._faltantes]), [], "cada frase de las piezas tiene su inglés");
});

await caso("tema: elegido gana al sistema; «sistema» sigue al sistema; ?tema= para vistas previas", async (page, contexto) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await abrir(page);
  const fondo = () => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  assert.equal(await fondo(), "rgb(16, 20, 27)", "sistema oscuro");
  await page.click("#abrir");
  await page.click('[data-pz-tema="claro"]');
  assert.equal(await page.evaluate(() => document.documentElement.dataset.tema), "claro");
  assert.equal(await fondo(), "rgb(246, 247, 249)");
  assert.equal(await page.locator('[data-pz-tema="claro"]').getAttribute("aria-pressed"), "true");
  await page.click('[data-pz-tema="sistema"]');
  assert.equal(await page.evaluate(() => "tema" in document.documentElement.dataset), false);
  await page.emulateMedia({ colorScheme: "light" });
  assert.equal(await fondo(), "rgb(246, 247, 249)", "sigue al sistema cuando cambia");
  const otra = await contexto.newPage();
  await otra.goto(URL_BASE + "?tema=oscuro");
  await otra.waitForFunction(() => window.listo === true);
  assert.equal(await otra.evaluate(() => document.documentElement.dataset.tema), "oscuro");
});

await caso("contraste AA de los tokens en claro y oscuro: los de la pieza y los pares de cada app", async (page) => {
  await abrir(page);
  const malos = await revisarContraste(page, "pieza");
  for (const p of paletas) {
    await page.evaluate((app) => new Promise((ok) => { const l = document.createElement("link"); l.rel = "stylesheet"; l.href = `paleta-${app}.css`; l.id = "paleta"; l.onload = ok; document.head.appendChild(l); }), p.app);
    malos.push(...await revisarContraste(page, p.app));
    await page.evaluate(() => document.getElementById("paleta").remove());
  }
  assert.deepEqual(malos, []);
});

await caso("celular (390 px): botones de 44 px, el diálogo sale desde abajo, nada se sale de ancho", async (page, contexto) => {
  await page.setViewportSize({ width: 390, height: 780 });
  await abrir(page);
  await page.click("#abrir");
  await page.waitForFunction(() => document.querySelector(".pz-dialogo").getAnimations().every((a) => a.playState === "finished"));
  const r = await page.evaluate(() => ({
    min: Math.min(...[...document.querySelectorAll('[role="dialog"] .pz-boton, [role="dialog"] .pz-seg button, [role="dialog"] .pz-chip')].filter((b) => b.offsetParent).map((b) => b.getBoundingClientRect().height)),
    abajo: Math.round(document.querySelector(".pz-dialogo").getBoundingClientRect().bottom), alto: innerHeight,
    ancho: document.documentElement.scrollWidth, vista: innerWidth,
  }));
  assert.ok(r.min >= 44, `el más chico mide ${r.min}px`);
  assert.equal(r.abajo, r.alto, "hoja pegada abajo");
  assert.ok(r.ancho <= r.vista, `${r.ancho} > ${r.vista}`);
});

await caso("movimiento reducido: el diálogo y el aviso no se animan", async (page) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await abrir(page);
  await page.click("#abrir");
  assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector(".pz-dialogo")).animationName), "none");
  assert.match(await page.evaluate(() => getComputedStyle(document.getElementById("toast")).transitionDuration), /^0s/);
});

await navegador.close();
servidor.close();
fs.rmSync(dir, { recursive: true, force: true });
if (fallas) { console.log(`${fallas} con problemas`); process.exit(1); }
console.log("Interfaz: todo bien");
