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
const E = { ajustes: false, ia: null, enlaces: [], propio: null, paso: 1, deshecho: 0, galeria: false, busqueda: "", campo: "" };
const attr = (v) => String(v).replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");
const IAS = [{ id: "claude", nombre: "Claude Code", instalada: true }, { id: "codex", nombre: "Codex <i>", instalada: false }];
const host = PiezaHost.crearHost({ nombre: "prueba", global: "Prueba", simular: {
  ...PiezaHost.simulacionesComunes({ espera: 40 }),
  config: (d) => { if (d.ia) E.ia = d.ia; },
  abrirEnlace: (d) => { E.enlaces.push(d.url); },
} });
const raiz = document.getElementById("app");
const ui = PiezaComponentes.crear({ i18n, host, app: "Prueba", repo: "ana-app/ana", version: "1.0", pintar, duracion: 300, pausa: 50, mantenerCampos: true,
  cerrar: () => { E.ajustes = false; E.propio = null; E.galeria = false; pintar(); } });
const tema = PiezaTema.crear({ guardar: (v) => host.enviar("config", { tema: v }) });
host.responder({ iaProbada: (r) => ui.iaProbada(r), actualizacionRevisada: (r) => ui.actualizacionRevisada(r), actualizacionProgreso: (a) => ui.actualizacionProgreso(a) });
function ajustes() {
  return "<h3>Apariencia</h3>" + tema.selectorHTML() + "<h3>Tu IA</h3>" + ui.filasIA({ ias: IAS, elegida: E.ia, guia: "https://ana-app.github.io/ana/ia.html" })
    + ui.filaActualizacion() + ui.acercaDe({ version: "1.0", enlaces: { codigo: "https://github.com/ana-app/ana" } });
}
// Un diálogo armado por la app (envolver), con pasos que comparten el título y un campo: el foco va al título al abrir y al
// cambiar de paso, y se queda en el campo si la app vuelve a pintar.
function propio() {
  return ui.envolver('<h2 id="t-propio">Ajustes</h2><p class="pz-error-texto" id="error">Abrir</p><label class="pz-campo"><span>Abrir</span><input id="campo" type="text" value="' + attr(E.campo) + '"></label>'
    + '<div class="pz-pie"><button type="button" class="pz-boton" id="paso" data-paso-siguiente>Un botón</button><button type="button" class="pz-boton pz-principal" data-pz-cerrar>Listo</button></div>',
    { id: "t-propio", clave: "paso-" + E.paso });
}
function pintar() {
  raiz.innerHTML = '<main data-tema="de-la-app"><button type="button" class="pz-boton" id="abrir">Ajustes</button> <button type="button" class="pz-boton" data-otro="1">Un botón</button> <button type="button" class="pz-boton" id="abrir-propio">Abrir</button>'
    + ' <button type="button" class="pz-boton" id="abrir-galeria">Tu IA</button> <input id="buscar" type="search" value="' + attr(E.busqueda) + '"><p id="vacio">Listo</p></main>'
    // Una ventana propia de la app (como la galería de Minuta): aria-modal, sin las clases de la pieza.
    + (E.galeria ? '<div class="galeria" role="dialog" aria-modal="true" aria-labelledby="t-gal"><h2 id="t-gal">Tu IA</h2><button type="button" data-pz-cerrar>Listo</button></div>' : "")
    + (E.ajustes ? ui.dialogo({ id: "t-aj", titulo: "Ajustes", cuerpo: ajustes(), pie: '<button type="button" class="pz-boton pz-principal" id="listo" data-pz-cerrar data-autofoco>Listo</button>' }) : "")
    + (E.propio ? propio() : "")
    + ui.capas();
  i18n.traducirDOM(raiz);
  ui.despuesDePintar();
}
document.addEventListener("click", (ev) => {
  if (tema.manejarClic(ev)) return pintar();
  if (ui.manejarClic(ev)) return;
  if (ev.target.closest("#abrir")) { E.ajustes = true; pintar(); }
  if (ev.target.closest("#abrir-propio")) { E.propio = true; E.paso = 1; pintar(); }
  if (ev.target.closest("[data-paso-siguiente]")) { E.paso++; pintar(); }
  if (ev.target.closest("#abrir-galeria")) { E.galeria = true; pintar(); }
  E.temaApp = ev.target.closest("[data-tema]")?.getAttribute("data-tema") || null;
});
document.addEventListener("keydown", (ev) => { ui.manejarTecla(ev); });
// Un buscador que vuelve a pintar todo en cada letra; el campo del diálogo solo guarda lo escrito.
document.addEventListener("input", (ev) => {
  if (ev.target.id === "buscar") { E.busqueda = ev.target.value; pintar(); }
  if (ev.target.id === "campo") E.campo = ev.target.value;
});
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
const PARES = [["sobre-rojo", "rojo"], ["sobre-texto", "texto"], ["texto", "fondo"], ["texto", "panel"], ["texto", "panel-2"], ["texto-suave", "fondo"], ["texto-suave", "panel"], ["texto-suave", "panel-2"],
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
  }, ["fondo", "panel", "panel-2", "texto", "texto-suave", "acento", "sobre-acento", "rojo", "verde", "sobre-rojo", "sobre-texto"]);
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

await caso("confirmar: con peligro el foco empieza en «Cancelar» (Enter no borra), Esc es «no»; sin peligro, en el título", async (page) => {
  await abrir(page);
  await page.evaluate(() => { window.r1 = window.prueba.ui.confirmar({ titulo: "¿Borrar «{x}»?", valores: { x: "<b>nota</b>" }, si: "Aceptar", peligro: true }); });
  assert.equal(await page.locator('[role="alertdialog"] h2 b').count(), 0, "el valor va escapado");
  assert.match(await page.locator('[role="alertdialog"] h2').innerText(), /<b>nota<\/b>/);
  assert.equal(await page.evaluate(() => document.activeElement.dataset.pzConfirmar), "no");
  await page.keyboard.press("Enter");
  assert.equal(await page.evaluate(() => window.r1), false, "un Enter apurado responde «no»");
  await page.evaluate(() => { window.r3 = window.prueba.ui.confirmar({ titulo: "¿Borrar?", peligro: true }); });
  await page.keyboard.press("Escape");
  assert.equal(await page.evaluate(() => window.r3), false);
  const peligro = await page.evaluate(() => { window.prueba.ui.confirmar({ titulo: "¿Borrar?", si: "Aceptar", peligro: true });
    const b = document.querySelector(".pz-principal.pz-peligro"), c = getComputedStyle(b); return [c.color, c.backgroundColor]; });
  assert.notEqual(peligro[0], peligro[1], "el texto del botón de peligro se ve");
  await page.keyboard.press("Escape");
  await page.evaluate(() => { window.r2 = "sin respuesta"; window.prueba.ui.confirmar({ titulo: "¿Seguro?" }).then((v) => { window.r2 = v; }); });
  assert.equal((await activo(page)).id, "pz-t-conf", "sin peligro, el foco va al título como en todo diálogo");
  assert.equal(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), "none", "el título no lleva anillo");
  await page.keyboard.press("Enter");
  assert.equal(await page.evaluate(() => window.r2), "sin respuesta", "un Enter sobre el título no elige nada");
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
  assert.equal(await page.evaluate(() => document.documentElement.dataset.pzModo), "claro");
  assert.equal(await page.evaluate(() => "tema" in document.documentElement.dataset), false, "data-tema queda para la app");
  assert.equal(await fondo(), "rgb(246, 247, 249)");
  assert.equal(await page.locator('[data-pz-tema="claro"]').getAttribute("aria-pressed"), "true");
  await page.click('[data-pz-tema="sistema"]');
  assert.equal(await page.evaluate(() => "pzModo" in document.documentElement.dataset), false);
  await page.emulateMedia({ colorScheme: "light" });
  assert.equal(await fondo(), "rgb(246, 247, 249)", "sigue al sistema cuando cambia");
  const otra = await contexto.newPage();
  await otra.goto(URL_BASE + "?tema=oscuro");
  await otra.waitForFunction(() => window.listo === true);
  assert.equal(await otra.evaluate(() => document.documentElement.dataset.pzModo), "oscuro");
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


await caso("tema 0.2: la sombra es válida en claro y oscuro, y un closest(\"[data-tema]\") de la app no llega a <html>", async (page) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await abrir(page, "?tema=oscuro");
  await page.click("#abrir");
  for (const m of ["oscuro", "claro", "sistema"]) {
    await page.evaluate((x) => window.prueba.tema.aplicar(x), m);
    const sombra = await page.evaluate(() => getComputedStyle(document.querySelector(".pz-dialogo")).boxShadow);
    assert.notEqual(sombra, "none", `sombra en ${m}`);
  }
  await page.keyboard.press("Escape");
  await page.click('[data-otro="1"]');
  assert.equal(await page.evaluate(() => window.prueba.E.temaApp), "de-la-app", "encuentra el data-tema de la app");
  await page.mouse.click(1000, 700);
  assert.equal(await page.evaluate(() => window.prueba.E.temaApp), null, "fuera de él, no encuentra <html>");
});

await caso("componentes 0.2: envolver: foco al título, se queda en el campo al repintar, el paso nuevo lo lleva al título; error rojo; sin anillo en la caja", async (page) => {
  await abrir(page);
  await page.click("#abrir-propio");
  assert.equal((await activo(page)).id, "t-propio", "al abrir, el foco va al título");
  const c = await page.evaluate(() => {
    const rojo = getComputedStyle(document.getElementById("error")).color;
    const el = document.createElement("i"); el.style.setProperty("color", "var(--rojo)"); document.body.appendChild(el);
    const r = getComputedStyle(el).color; el.remove(); return [rojo, r];
  });
  assert.equal(c[0], c[1], "un .pz-error-texto dentro del diálogo es rojo, no gris");
  await page.click("#campo");
  await page.keyboard.type("hola");
  await page.evaluate(() => window.prueba.pintar());
  assert.equal((await activo(page)).id, "campo", "repintar con el diálogo abierto no saca el foco del campo");
  await page.click("#paso");
  assert.equal((await activo(page)).id, "t-propio", "otro paso (otra clave, mismo título): el foco va al título");
  assert.equal(await page.evaluate(() => { const d = document.querySelector(".pz-dialogo"); d.focus(); return getComputedStyle(d).outlineStyle; }), "none");
  await page.keyboard.press("Escape");
  assert.equal((await activo(page)).id, "abrir-propio");
});

await caso("componentes 0.2: aviso con botón y avisos legibles con fondos transparentes", async (page) => {
  await abrir(page, "?idioma=en");
  await page.evaluate(() => { document.documentElement.style.setProperty("--fondo-claro", "transparent"); document.documentElement.style.setProperty("--panel-claro", "transparent");
    window.prueba.tema.aplicar("claro");
    window.prueba.ui.aviso("Guardar", { accion: { texto: "Abrir", f: () => { window.prueba.E.deshecho++; } } }); });
  const t = page.locator("#toast");
  await page.waitForFunction(() => document.getElementById("toast").classList.contains("visible"));
  assert.equal(await page.locator("#toast button.pz-toast-accion").innerText(), "Open");
  const [color, fondo] = await page.evaluate(() => { const c = getComputedStyle(document.getElementById("toast")); return [c.color, c.backgroundColor]; });
  assert.notEqual(color, "rgba(0, 0, 0, 0)", "el texto del aviso es sólido");
  assert.notEqual(color, fondo);
  await page.click("#toast button.pz-toast-accion");
  assert.equal(await page.evaluate(() => window.prueba.E.deshecho), 1);
  await page.waitForFunction(() => !document.getElementById("toast").classList.contains("visible"));
  assert.match(await t.getAttribute("class"), /pz-toast/);
});

await caso("componentes 0.3: al repintar, el cursor queda donde estaba (en un diálogo y en un buscador con mantenerCampos)", async (page) => {
  await abrir(page);
  await page.click("#abrir-propio");
  await page.click("#campo");
  await page.keyboard.type("hola mundo");
  for (let i = 0; i < 3; i++) await page.keyboard.press("ArrowLeft");
  await page.evaluate(() => window.prueba.pintar());
  assert.deepEqual(await page.evaluate(() => [document.activeElement.id, document.activeElement.selectionStart]), ["campo", 7], "el cursor sigue donde estaba");
  await page.keyboard.press("Escape");
  // Fuera de un diálogo: el buscador vuelve a pintar todo en cada letra y se sigue escribiendo sin perder nada.
  await page.click("#buscar");
  await page.keyboard.type("ana pérez");
  assert.deepEqual(await page.evaluate(() => [document.activeElement.id, document.activeElement.value]), ["buscar", "ana pérez"]);
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.type("x");
  assert.deepEqual(await page.evaluate(() => [document.activeElement.value, document.activeElement.selectionStart]), ["axna pérez", 2], "escribir en el medio deja el cursor ahí");
  // Salir del buscador (un clic en otro lado) y que la app vuelva a pintar: el foco no vuelve solo.
  await page.click("#vacio");
  await page.evaluate(() => window.prueba.pintar());
  assert.notEqual((await activo(page)).id, "buscar", "si la persona salió del campo, una pintada no la devuelve");
});

await caso("componentes 0.3: el título de una ventana aria-modal propia de la app no lleva anillo; la ✕ no se achica", async (page) => {
  await abrir(page);
  await page.focus("#abrir-galeria");
  await page.keyboard.press("Enter");   // con el teclado: ahí el navegador dibuja el anillo de :focus-visible
  assert.equal((await activo(page)).id, "t-gal", "la pieza enfoca el título de la ventana de la app");
  assert.equal(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), "none");
  await page.keyboard.press("Tab");
  assert.notEqual(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), "none", "sus controles sí lo llevan");
  await page.keyboard.press("Escape");
  await page.evaluate(() => document.documentElement.style.setProperty("--pz-boton-alto", "0px"));
  await page.click("#abrir");
  const ancho = await page.evaluate(() => { const r = document.querySelector(".pz-cerrar").getBoundingClientRect(); return [r.width, r.height]; });
  assert.ok(ancho[0] >= 36 && ancho[1] >= 36, `la ✕ mide ${ancho}`);
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
  const fuera = await page.evaluate(() => document.getElementById("abrir").getBoundingClientRect().height);
  assert.ok(fuera < 44, `fuera de los componentes de la pieza (un editor compacto) no crece solo: mide ${fuera}px`);
  const seg = await page.evaluate(() => { const s = document.querySelector('[role="dialog"] .pz-seg'); const b = [...s.querySelectorAll("button")].map((x) => Math.round(x.getBoundingClientRect().top)); return new Set(b).size; });
  assert.equal(seg, 1, "el selector segmentado queda en una línea");
  const largo = await page.evaluate(() => { const b = document.createElement("button"); b.className = "pz-boton"; b.textContent = "Un texto muy largo para un botón que en un celular no cabe en una sola línea";
    document.querySelector('[role="dialog"] .pz-pie').appendChild(b); const r = b.getBoundingClientRect(); return [r.right, innerWidth]; });
  assert.ok(largo[0] <= largo[1], "un botón con texto largo se parte en vez de salirse");
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
