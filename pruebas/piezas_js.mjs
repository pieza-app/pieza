// Pruebas de las piezas de JavaScript (i18n, bienvenida, actualizaciones de Electron). Solo Node, sin dependencias:
//   node --test pruebas/piezas_js.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { execFileSync, spawn as spawnReal } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const BASE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PiezaI18n = require(path.join(BASE, "piezas/i18n/ui/i18n.js"));
const PiezaBienvenida = require(path.join(BASE, "piezas/bienvenida/ui/bienvenida.js"));
const Act = require(path.join(BASE, "piezas/actualizaciones/escritorio/actualizaciones.js"));
const EN = {
  codigo: "en", nombre: "English", bandera: "🇬🇧",
  textos: {
    "Guardar": "Save", "Hola, **{nombre}**": "Hi, **{nombre}**", "Quedan {n} días": "{n} days left",
    "{a} le escribió a {b}": "{b} got a message from {a}", "Comentarios": "Comments", "Atrás": "Back", "Siguiente": "Next",
    "Hola, esto es Ana": "Hi, this is Ana", "Empezar": "Start", "Lo hago después": "I'll do it later",
  },
  palabras: { octubre: "october", lunes: "monday" },
};

// ───────────── i18n ─────────────
function i18nEn(extra) {
  const i = PiezaI18n.crear(extra);
  assert.equal(i.usar(EN).ok, true);
  return i;
}

test("i18n: en español no cambia nada y T escapa igual", () => {
  const i = PiezaI18n.crear();
  assert.equal(i.idioma, "es");
  assert.equal(i.tr("Guardar"), "Guardar");
  assert.equal(i.T("Hola, **{nombre}**", { nombre: "<b>Ana</b>" }), "Hola, <b>&lt;b&gt;Ana&lt;/b&gt;</b>");
});

test("i18n: tr traduce exactos, con espacios, con íconos, por partes y plantillas {n}", () => {
  const i = i18nEn();
  assert.equal(i.tr("Guardar"), "Save");
  assert.equal(i.tr("  Guardar \n"), "  Save \n");
  assert.equal(i.tr("💬 Comentarios ▾"), "💬 Comments ▾");
  assert.equal(i.tr("Guardar · Comentarios"), "Save · Comments");
  assert.equal(i.tr("Quedan 12 días"), "12 days left");
  assert.equal(i.tr("Ana Pérez le escribió a Matías Soto"), "Matías Soto got a message from Ana Pérez", "los marcadores pueden cambiar de orden");
  assert.equal(i.tr("Lunes 18 de octubre"), "Monday 18 october");
  assert.equal(i.tr("Algo sin traducción"), "Algo sin traducción");
});

test("i18n: T traduce, escapa los valores y nunca vuelve a reemplazar lo que trae un valor", () => {
  const i = i18nEn();
  assert.equal(i.T("Hola, **{nombre}**", { nombre: "<img src=x onerror=alert(1)>" }), "Hi, <b>&lt;img src=x onerror=alert(1)&gt;</b>");
  assert.equal(i.T("{a} le escribió a {b}", { a: "{b}", b: "Ana" }), "Ana got a message from {b}");
  assert.equal(i.Tp("Hola, **{nombre}**", { nombre: "<Ana>" }), "Hi, <Ana>");
  assert.equal(i.Thtml("Quedan {n} días", { n: "<b>3</b>" }), "<b>3</b> days left");
  assert.equal(i.frase("Guardar", {}, "small"), "<small data-sin-traducir>Save</small>");
  assert.equal(i.frase("Guardar", {}, "img onerror=x"), "<span data-sin-traducir>Save</span>");
});

test("i18n: marcadores repetidos se llenan en orden (Minuta: «Paso {n} de {n}»)", () => {
  const i = PiezaI18n.crear();
  i.usar({ codigo: "en", nombre: "English", textos: { "Paso {n} de {n}": "Step {n} of {n}" } });
  assert.equal(i.Tp("Paso {n} de {n}", [2, 8]), "Step 2 of 8");
  assert.equal(i.tr("Paso 2 de 8"), "Step 2 of 8");
});

test("i18n: «<nombre>.md» no es HTML, una etiqueta de verdad sí", () => {
  const r = PiezaI18n.validarPaquete({ codigo: "en", nombre: "English", textos: {
    "Se guarda en flujos/<nombre>.md": "Saved in flows/<name>.md", "Mal": "<script>x</script>", "Mal2": "<a href=x>y</a>" } });
  assert.deepEqual([...r.paquete.textos.keys()], ["Se guarda en flujos/<nombre>.md"]);
});

test("i18n: lo que falta se anota para las pruebas de la app", () => {
  const faltantes = new Set();
  const i = i18nEn({ faltantes });
  i.T("Una frase nueva"); i.tr("Otra frase nueva");
  assert.deepEqual([...faltantes].sort(), ["Otra frase nueva", "Una frase nueva"]);
});

test("i18n: valida lo que viene de afuera (solo texto, mismos marcadores)", () => {
  const malo = JSON.parse(`{"codigo": "en", "nombre": "English",
    "textos": {"Guardar": "<img src=x onerror=alert(1)>", "Quedan {n} días": "{x} days left", "Hola, **{nombre}**": "Hi, {nombre}",
      "Comentarios": "Comm\\u202eents", "__proto__": "x", "Bien": "Good", "Vacío": ""},
    "palabras": {"octubre": "<b>", "Mayus": "x", "lunes": "monday"}}`);
  const r = PiezaI18n.validarPaquete(malo);
  assert.equal(r.ok, true);
  assert.deepEqual([...r.paquete.textos.keys()], ["Bien"]);
  assert.deepEqual([...r.paquete.palabras.keys()], ["lunes"]);
  assert.equal(r.errores.length, 8);
  assert.equal(PiezaI18n.validarPaquete({ codigo: "../x", textos: {} }).ok, false);
  assert.equal(PiezaI18n.validarPaquete({ codigo: "en", textos: {} }, "pt").ok, false);
  assert.equal(PiezaI18n.validarPaquete([]).ok, false);
  assert.equal(PiezaI18n.validarPaquete({ codigo: "en", nombre: "<script>", textos: [] }).ok, false);
});

test("i18n: cargar pide solo idiomas/<codigo>.json, valida y si falla queda en español", async () => {
  const pedidos = [];
  const traer = async (u) => { pedidos.push(u); return { json: async () => (u.endsWith("en.json") ? EN : { codigo: "fr", textos: {} }) }; };
  const i = PiezaI18n.crear();
  assert.equal((await i.cargar("../../etc/passwd", { traer })).ok, true);
  assert.equal(i.idioma, "es");
  assert.deepEqual(pedidos, []);
  await i.cargar("en", { traer });
  assert.equal(i.idioma, "en");
  const r = await i.cargar("pt", { traer });
  assert.equal(r.ok, false);
  assert.equal(i.idioma, "es");
  await i.cargar("en", { traer: async () => { throw new Error("sin red"); } });
  assert.equal(i.idioma, "es");
  assert.deepEqual(pedidos, ["idiomas/en.json", "idiomas/pt.json"]);
});

test("i18n: elegir sigue lo elegido > URL > config > sistema", () => {
  const i = PiezaI18n.crear();
  assert.equal(i.elegir({ elegido: "en", config: "es", url: "es", sistema: "es" }), "en");
  assert.equal(i.elegir({ config: "en", url: "es", sistema: "es" }), "es");  // la URL fuerza (vista previa y pruebas)
  assert.equal(i.elegir({ config: "en", url: null, sistema: "es" }), "en");
  assert.equal(i.elegir({ config: null, url: "en", sistema: "es" }), "en");
  assert.equal(i.elegir({ config: "fr", url: null, sistema: "en" }), "en");
  assert.equal(i.idiomaDelSistema(["es-CL"]), "es");
  assert.equal(i.idiomaDelSistema(["de-DE", "en-US"]), "en");
  assert.equal(i.idiomaDelSistema(["fr-FR"]), "en");
  assert.equal(i.idiomaDelSistema([]), "es");
});

// Un DOM mínimo para traducirDOM (solo lo que usa: childNodes, nodeType, matches, closest y atributos).
function el(tag, attrs = {}, hijos = []) {
  const e = {
    nodeType: 1, tagName: tag, attrs: { ...attrs }, childNodes: [], parentNode: null,
    getAttribute(a) { return this.attrs[a] ?? null; }, setAttribute(a, v) { this.attrs[a] = String(v); },
    matches(sel) { return sel.split(",").map((s) => s.trim()).some((s) => (s.startsWith("[") ? s.slice(1, -1) in this.attrs : s === this.tagName)); },
    closest(sel) { for (let n = this; n; n = n.parentNode) if (n.matches(sel)) return n; return null; },
  };
  for (const h of hijos) { const n = typeof h === "string" ? { nodeType: 3, nodeValue: h } : h; n.parentNode = e; e.childNodes.push(n); }
  return e;
}
test("i18n: traducirDOM traduce textos y atributos, nunca lo marcado data-sin-traducir", () => {
  const i = i18nEn();
  const nota = el("p", { "data-sin-traducir": "" }, ["Guardar"]);
  const raiz = el("div", {}, [el("button", { title: "Guardar", "aria-label": "Comentarios" }, ["Guardar"]), nota,
    el("textarea", {}, ["Guardar"]), el("span", {}, ["12"]), el("input", { placeholder: "Comentarios" })]);
  i.traducirDOM(raiz);
  assert.equal(raiz.childNodes[0].childNodes[0].nodeValue, "Save");
  assert.equal(raiz.childNodes[0].attrs.title, "Save");
  assert.equal(raiz.childNodes[0].attrs["aria-label"], "Comments");
  assert.equal(nota.childNodes[0].nodeValue, "Guardar");
  assert.equal(raiz.childNodes[2].childNodes[0].nodeValue, "Guardar");
  assert.equal(raiz.childNodes[4].attrs.placeholder, "Comments");
  i.traducirDOM(nota);
  assert.equal(nota.childNodes[0].nodeValue, "Guardar");
});

test("i18n y bienvenida: sin eval, sin innerHTML ni estilos en línea (CSP script-src 'self'; style-src 'self')", () => {
  for (const f of ["piezas/i18n/ui/i18n.js", "piezas/bienvenida/ui/bienvenida.js"]) {
    const t = fs.readFileSync(path.join(BASE, f), "utf8");
    assert.doesNotMatch(t, /\beval\(|new Function|innerHTML\s*=|style="|\.style\.cssText|setAttribute\("style"|\son[a-z]+=/, f);
  }
});

// ───────────── bienvenida ─────────────
function bienvenida(extra = {}) {
  const i18n = PiezaI18n.crear();
  const registro = { guardado: [], pintadas: 0, terminada: 0, avisos: [] };
  const enfocados = [];
  const documento = {
    activeElement: null,
    querySelector: (s) => ({ focus: () => enfocados.push(s) }),
    querySelectorAll: () => [],
  };
  const bv = PiezaBienvenida.crear({
    i18n, documento,
    sistema: () => "en",
    cargarIdioma: (c) => i18n.usar(c === "en" ? EN : null),
    guardarIdioma: (c) => registro.guardado.push(c),
    pintar: () => registro.pintadas++,
    terminar: () => registro.terminada++,
    mostrarAviso: (...a) => registro.avisos.push(a),
    ...extra,
  });
  return { bv, registro, enfocados, i18n };
}

test("bienvenida: el idioma va primero, solo, bilingüe y sin traducir", () => {
  const { bv } = bienvenida();
  bv.sumarPaso({ id: "hola", titulo: "Hola, esto es Ana", cuerpo: () => "<p>CUERPO-HOLA</p>" });
  assert.equal(bv.abrir({ config: {} }), 0);
  assert.equal(bv.soloIdioma, true);
  const h = bv.html();
  assert.match(h, /data-sin-traducir/);
  assert.match(h, /<span lang="es">Elige tu idioma<\/span> .*<span lang="en">Choose your language<\/span>/);
  assert.match(h, /data-bv-idioma="es" lang="es" aria-keyshortcuts="1">[\s\S]*<b>Español<\/b>/);
  assert.match(h, /class="opcion-idioma sugerido" id="bv-idioma-en"[\s\S]*<b>English<\/b><small>Suggested<\/small>/);
  assert.doesNotMatch(h, /CUERPO-HOLA|Atrás|Siguiente/);
  assert.deepEqual(bv.pasos, ["idioma", "hola", "listo"]);
});

test("bienvenida: elegir guarda por config, carga el idioma, sigue traducida y suelta el último aviso", async () => {
  const { bv, registro, enfocados } = bienvenida();
  bv.sumarPaso({ id: "hola", titulo: "Hola, esto es Ana", cuerpo: () => "<p>x</p>" });
  bv.abrir({ config: {} });
  assert.equal(bv.retener("Hay una versión nueva"), true);
  assert.equal(bv.retener("Otra"), true);
  await bv.elegirIdioma("en");
  assert.deepEqual(registro.guardado, ["en"]);
  assert.equal(bv.paso, 1);
  assert.deepEqual(registro.avisos, [["Otra"]]);
  assert.equal(bv.retener("Ya no espera"), false);
  assert.match(bv.html(), /<h2 id="t-bv" tabindex="-1" data-sin-traducir>Hi, this is Ana<\/h2>/);
  assert.match(bv.html(), />Back<\/button>[\s\S]*>Next<\/button>/);
  assert.deepEqual(enfocados.slice(-1), ["#t-bv"]);
  assert.equal(await bv.elegirIdioma("fr"), false);
});

test("bienvenida: teclas 1 y 2, flechas, y nada si se escribe en un campo", async () => {
  const { bv, registro } = bienvenida();
  bv.abrir({ config: {} });
  const campo = { key: "1", target: { closest: (s) => (s.includes("input") ? {} : null) } };
  assert.equal(bv.manejarTecla(campo), false);
  assert.equal(bv.manejarTecla({ key: "3", target: { closest: () => null } }), false);
  assert.equal(bv.manejarTecla({ key: "1", target: { closest: () => null }, preventDefault() {} }), true);
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(registro.guardado, ["es"]);
  assert.equal(bv.manejarTecla({ key: "2", target: { closest: () => null } }), false, "fuera del paso del idioma no hace nada");
});

test("bienvenida: pasos en orden, «puede» bloquea Siguiente, terminar guarda y cierra", () => {
  const { bv, registro } = bienvenida({ listo: false });
  let listaIA = false;
  bv.sumarPaso({ id: "ia", titulo: "Tu IA", cuerpo: () => "", puede: () => listaIA, orden: 20 });
  bv.sumarPaso({ id: "hola", titulo: "Hola", cuerpo: () => "", orden: 10 });
  assert.throws(() => bv.sumarPaso({ id: "hola", titulo: "x", cuerpo: () => "" }));
  assert.throws(() => bv.sumarPaso({ id: "idioma", titulo: "x", cuerpo: () => "" }));
  assert.throws(() => bv.sumarPaso({ id: "Mal Id", titulo: "x", cuerpo: () => "" }));
  assert.deepEqual(bv.pasos, ["idioma", "hola", "ia"]);
  assert.equal(bv.abrir({ config: { idioma_ui: "es" } }), 1, "con idioma elegido sigue desde el saludo");
  assert.equal(bv.ir(2), true);
  assert.match(bv.html(), /data-bv-fin>Empezar/);
  assert.equal(bv.ir(1), true);
  assert.equal(bv.ir(0), true, "se puede volver al idioma");
  assert.equal(bv.ir(1), false, "del idioma se sale eligiendo");
  assert.equal(bv.abrir({ config: { bienvenida: true } }), null);
  assert.equal(bv.html(), "");
  assert.equal(bv.abrir({ config: { bienvenida: true }, forzar: true }), 0);
  bv.abrir({ config: { idioma_ui: "es" } });
  bv.ir(2);
  assert.match(bv.html(), /data-bv-ir="2" disabled|data-bv-fin/);
  const clic = (attr, valor) => ({ preventDefault() {}, target: { closest: () => ({ hasAttribute: (a) => a === attr, getAttribute: () => valor }) } });
  assert.equal(bv.manejarClic(clic("data-bv-fin")), true);
  assert.equal(bv.activa, false);
  assert.equal(registro.terminada, 1);
  assert.equal(bv.manejarClic(clic("data-bv-fin")), false);
});

test("bienvenida: «puede» en falso deja Siguiente desactivado y no avanza", () => {
  const { bv } = bienvenida();
  bv.sumarPaso({ id: "carpeta", titulo: "Elige tu carpeta", cuerpo: () => "", puede: () => false });
  bv.abrir({ config: { idioma_ui: "es" } });
  assert.match(bv.html(), /data-bv-ir="2" disabled/);
  assert.equal(bv.ir(2), false);
});

test("bienvenida: escapa los nombres de idiomas y exige i18n y guardarIdioma", () => {
  const i18n = PiezaI18n.crear();
  const bv = PiezaBienvenida.crear({ i18n, guardarIdioma() {}, sistema: () => "es",
    idiomas: [{ codigo: "es", nombre: "<img>", sugerido: "<b>" }, { codigo: "../x", nombre: "malo" }] });
  bv.abrir({});
  assert.match(bv.html(), /&lt;img&gt;/);
  assert.doesNotMatch(bv.html(), /malo/);
  assert.throws(() => PiezaBienvenida.crear({ guardarIdioma() {} }));
  assert.throws(() => PiezaBienvenida.crear({ i18n }));
});

// ───────────── actualizaciones (Electron) ─────────────
const REPO = "ana-app/ana";
test("actualizaciones: solo descargas de los Releases del propio repo", () => {
  const bien = `https://github.com/${REPO}/releases/download/v1.2.0/Ana-Linux.AppImage`;
  assert.equal(Act.esDescargaNuestra(bien, REPO), true);
  for (const u of [
    `http://github.com/${REPO}/releases/download/v1/x`, `https://github.com.evil.io/${REPO}/releases/download/v1/x`,
    `https://github.com/otra/ana/releases/download/v1/x`, `https://github.com/${REPO}/releases/download/v1/x?y=1`,
    `https://github.com:8443/${REPO}/releases/download/v1/x`, `https://ana@github.com/${REPO}/releases/download/v1/x`,
    `https://github.com/${REPO}/releases/download/../../otra/x`, `https://github.com/${REPO}/releases/download/v1/%2e%2e/%2e%2e/%2e%2e/otra/x`,
    `https://github.com/${REPO}/archive/main.zip`, "no es url", undefined,
  ]) assert.equal(Act.esDescargaNuestra(u, REPO), false, String(u));
  assert.equal(Act.esDescargaNuestra(bien, "mal repo"), false);
});

test("actualizaciones: versiones, huellas y nombres de archivo", () => {
  assert.equal(Act.esMayor("0.10.0", "0.9.3"), true);
  assert.equal(Act.esMayor("v1.0.0", "1.0.0"), false);
  assert.equal(Act.esMayor("1.0", "0.9.9"), true);
  assert.equal(Act.esMayor("1.0.0-beta", "0.1.0"), false, "lo que no es versión nunca es más nuevo");
  assert.equal(Act.esMayor("99999999.0", "1.0"), false);
  const h = "a".repeat(64);
  assert.equal(Act.leerHuella(`${h.toUpperCase()}  Ana-Linux.AppImage\n`), h);
  assert.equal(Act.leerHuella("no"), null);
  assert.deepEqual(Act.archivosDe("Alcancia").windows, "Alcancia-Windows.exe");
  assert.equal(Act.baseDe("Alcancía"), "Alcancia");
});

test("actualizaciones: comillas() deja todo como texto para bash", () => {
  const raro = `$(touch /tmp/no-debe) \`id\` "; rm -rf x '; echo 'mal`;
  assert.equal(execFileSync("/bin/bash", ["-c", `printf %s ${Act.comillas(raro)}`]).toString(), raro);
  const g = Act.guionTar({ pid: "1; rm -rf /", destino: "/tmp/a'b", nueva: "/tmp/n", tmp: "/tmp/t", lanzador: "/tmp/l", ejecutable: "ana" });
  assert.match(g, /kill -0 NaN/);
  assert.match(g, /'\/tmp\/a'\\''b'/);
});

test("actualizaciones: sin datos de la app no se crea, y ninguna app aparece escrita en el código", () => {
  assert.throws(() => Act.crear({ app: {}, net: {}, repo: "malo", nombre: "Ana" }));
  assert.throws(() => Act.crear({ app: {}, net: {}, repo: REPO, nombre: "Ana", ejecutable: "../x" }));
  const t = fs.readFileSync(path.join(BASE, "piezas/actualizaciones/escritorio/actualizaciones.js"), "utf8")
    + fs.readFileSync(path.join(BASE, "piezas/actualizaciones/mac/Actualizaciones.swift"), "utf8");
  assert.doesNotMatch(t, /esquema|minuta|graba|corta|repasa|alcanc/i);
});

/** Un Release falso servido por un `net.fetch` de mentira, y una app de Electron de mentira. */
function escenario({ contenido = Buffer.from("version nueva"), huella, tag = "v0.2.0", plataforma = "linux", tipo = "appimage", redirige = "https://release-assets.githubusercontent.com/x" } = {}) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pieza-act-"));
  const home = path.join(tmp, "home");
  fs.mkdirSync(home);
  const archivos = Act.archivosDe("Ana");
  const nombre = tipo === "appimage" ? archivos.appimage : tipo === "tar" ? archivos.tar : archivos.windows;
  const url = (n) => `https://github.com/${REPO}/releases/download/${tag}/${n}`;
  const sha = huella ?? crypto.createHash("sha256").update(contenido).digest("hex");
  const pedidos = [];
  const net = {
    async fetch(u) {
      pedidos.push(u);
      if (u.startsWith("https://api.github.com/")) {
        return new Response(JSON.stringify({ tag_name: tag, body: "• Ahora puedes algo\n• Arreglo", assets: [
          { name: nombre, browser_download_url: url(nombre) }, { name: nombre + ".sha256", browser_download_url: url(nombre + ".sha256") }] }), { status: 200 });
      }
      const r = u.endsWith(".sha256") ? new Response(`${sha}  ${nombre}\n`) : new Response(contenido, { headers: { "content-length": String(contenido.length) } });
      Object.defineProperty(r, "url", { value: redirige });
      return r;
    },
  };
  const llamadas = { exit: 0, relaunch: [] };
  const app = { isPackaged: true, getVersion: () => "0.1.0", exit: () => llamadas.exit++, relaunch: (o) => llamadas.relaunch.push(o) };
  return { tmp, home, net, app, pedidos, llamadas, plataforma };
}
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

test("actualizaciones: revisar encuentra la versión y solo acepta URLs propias", async () => {
  const s = escenario();
  const appimage = path.join(s.tmp, "Ana.AppImage");
  fs.writeFileSync(appimage, "vieja");
  const act = Act.crear({ app: s.app, net: s.net, repo: REPO, nombre: "Ana", home: s.home, plataforma: "linux", entorno: { APPIMAGE: appimage }, tmpdir: s.tmp, espera: 0 });
  const r = await act.revisar();
  assert.equal(r.hay, true);
  assert.equal(r.version, "0.2.0");
  assert.equal(r.texto, "Versión {v}");
  assert.match(r.notas, /Ahora puedes algo/);
  assert.deepEqual(r.valores, { v: "0.2.0" });
  // Lo que la app manda en su estado tiene la misma forma (sin «sinConexion»): la interfaz usa una sola función.
  assert.deepEqual(act.disponible, { hay: true, version: "0.2.0", notas: r.notas, texto: "Versión {v}", valores: { v: "0.2.0" }, desarrollo: false });
  assert.deepEqual(act.aviso("error", "errorBajar"), { paso: "error", codigo: "errorBajar", texto: Act.TEXTOS.errorBajar, valores: { app: "Ana" }, total: 3 });
  assert.equal(act.aviso("1", "inventado").codigo, "errorArmar", "un código desconocido no inventa un texto");
  assert.equal(s.pedidos[0], `https://api.github.com/repos/${REPO}/releases/latest`);
  // Sin empaquetar (desarrollo): nunca hay y no sale a internet.
  const dev = Act.crear({ app: { ...s.app, isPackaged: false }, net: s.net, repo: REPO, nombre: "Ana" });
  assert.equal((await dev.revisar()).hay, false);
  assert.equal(s.pedidos.length, 1);
  // Sin conexión
  const sin = Act.crear({ app: s.app, net: { fetch: async () => { throw new Error("x"); } }, repo: REPO, nombre: "Ana", plataforma: "linux", entorno: { APPIMAGE: appimage } });
  assert.deepEqual([(await sin.revisar()).hay, (await sin.revisar()).sinConexion], [false, true]);
  assert.deepEqual(sin.disponible, { hay: false, version: "", notas: "", texto: "", valores: { v: "" }, desarrollo: false });
  fs.rmSync(s.tmp, { recursive: true, force: true });
});

test("actualizaciones: AppImage verificada se reemplaza; con otra huella no se toca nada", async () => {
  for (const [huella, debe] of [[undefined, "version nueva"], ["b".repeat(64), "vieja"], ["no-es-huella", "vieja"]]) {
    const s = escenario({ huella });
    const appimage = path.join(s.tmp, "Ana.AppImage");
    fs.writeFileSync(appimage, "vieja");
    const act = Act.crear({ app: s.app, net: s.net, repo: REPO, nombre: "Ana", home: s.home, plataforma: "linux", entorno: { APPIMAGE: appimage }, tmpdir: s.tmp, espera: 0 });
    await act.revisar();
    const avisos = [];
    await act.instalar((a) => avisos.push(a));
    await esperar(10);
    assert.equal(fs.readFileSync(appimage, "utf8"), debe);
    if (debe === "vieja") {
      assert.equal(avisos.at(-1).paso, "error");
      assert.equal(avisos.at(-1).codigo, "errorBajar");
      assert.equal(s.llamadas.exit, 0);
    } else {
      assert.deepEqual(avisos.map((a) => a.paso).filter((p, i, l) => l.indexOf(p) === i), ["1", "2", "3"]);
      assert.deepEqual(avisos.at(-1).valores, { app: "Ana" });
      assert.equal(avisos.at(-1).texto, "Instalando: {app} se cerrará y volverá a abrirse sola");
      assert.equal(s.llamadas.relaunch[0].execPath, appimage);
      assert.equal(s.llamadas.exit, 1);
    }
    assert.deepEqual(fs.readdirSync(s.tmp).filter((x) => x.startsWith("ana-actualizacion")), [], "no deja temporales");
    fs.rmSync(s.tmp, { recursive: true, force: true });
  }
});

test("actualizaciones: una redirección que termina fuera de https no se acepta", async () => {
  const s = escenario({ redirige: "http://release-assets.githubusercontent.com/x" });
  const appimage = path.join(s.tmp, "Ana.AppImage");
  fs.writeFileSync(appimage, "vieja");
  const act = Act.crear({ app: s.app, net: s.net, repo: REPO, nombre: "Ana", home: s.home, plataforma: "linux", entorno: { APPIMAGE: appimage }, tmpdir: s.tmp, espera: 0 });
  await act.revisar();
  const avisos = [];
  await act.instalar((a) => avisos.push(a));
  assert.equal(avisos.at(-1).codigo, "errorBajar");
  assert.equal(fs.readFileSync(appimage, "utf8"), "vieja");
  fs.rmSync(s.tmp, { recursive: true, force: true });
});

test("actualizaciones: Linux con instalar.sh cambia la carpeta entera cuando la app se cierra y la vuelve a abrir", async () => {
  // Arma un tar.gz con la «versión nueva» (un ejecutable que deja una marca al abrirse).
  const fuente = fs.mkdtempSync(path.join(os.tmpdir(), "pieza-tar-"));
  const marca = path.join(fuente, "abierta");
  fs.mkdirSync(path.join(fuente, "Ana"));
  fs.writeFileSync(path.join(fuente, "Ana", "ana"), `#!/bin/bash\necho nueva > ${Act.comillas(marca)}\n`, { mode: 0o755 });
  fs.writeFileSync(path.join(fuente, "Ana", "LEEME"), "2");
  execFileSync("tar", ["-czf", path.join(fuente, "ana.tar.gz"), "-C", fuente, "Ana"]);
  const s = escenario({ tipo: "tar", contenido: fs.readFileSync(path.join(fuente, "ana.tar.gz")) });
  const destino = path.join(s.home, ".local", "share", "Ana");
  fs.mkdirSync(destino, { recursive: true });
  fs.writeFileSync(path.join(destino, "ana"), "#!/bin/bash\n", { mode: 0o755 });
  fs.writeFileSync(path.join(destino, "LEEME"), "1");
  const muerto = spawnReal("true"); // un pid que ya terminó: la app «ya se cerró»
  await new Promise((r) => muerto.on("close", r));
  const act = Act.crear({ app: s.app, net: s.net, repo: REPO, nombre: "Ana", home: s.home, plataforma: "linux", entorno: {},
    execPath: path.join(destino, "ana"), pid: muerto.pid, tmpdir: s.tmp, espera: 0 });
  assert.equal(act.instalacion().tipo, "tar");
  await act.revisar();
  const avisos = [];
  await act.instalar((a) => avisos.push(a));
  assert.equal(avisos.at(-1).paso, "3", JSON.stringify(avisos.at(-1)));
  for (let i = 0; i < 100 && !fs.existsSync(marca); i++) await esperar(50);
  assert.equal(fs.readFileSync(path.join(destino, "LEEME"), "utf8"), "2");
  assert.equal(fs.readFileSync(marca, "utf8").trim(), "nueva");
  assert.equal(fs.existsSync(destino + ".anterior"), false);
  fs.rmSync(s.tmp, { recursive: true, force: true });
  fs.rmSync(fuente, { recursive: true, force: true });
});

test("actualizaciones: Windows lanza el instalador verificado en silencio", async () => {
  const s = escenario({ tipo: "windows" });
  const lanzados = [];
  const act = Act.crear({ app: s.app, net: s.net, repo: REPO, nombre: "Ana", plataforma: "win32", tmpdir: s.tmp, espera: 0,
    spawn: (cmd, args) => { lanzados.push([path.basename(cmd), args]); return { unref() {} }; } });
  assert.equal((await act.revisar()).hay, true);
  await act.instalar(() => {});
  await esperar(10);
  assert.deepEqual(lanzados, [["Ana-Windows.exe", ["/S"]]]);
  assert.equal(s.llamadas.exit, 1);
  fs.rmSync(s.tmp, { recursive: true, force: true });
});

test("actualizaciones: sin revisar antes, instalar no descarga nada", async () => {
  const s = escenario();
  const act = Act.crear({ app: s.app, net: s.net, repo: REPO, nombre: "Ana", plataforma: "win32", tmpdir: s.tmp });
  const avisos = [];
  await act.instalar((a) => avisos.push(a));
  assert.deepEqual(avisos.map((a) => a.codigo), ["sinDescarga"]);
  assert.equal(s.pedidos.length, 0);
  fs.rmSync(s.tmp, { recursive: true, force: true });
});

test("actualizaciones: los textos de Electron y Swift son los mismos", () => {
  const swift = fs.readFileSync(path.join(BASE, "piezas/actualizaciones/mac/Actualizaciones.swift"), "utf8");
  for (const [k, v] of Object.entries(Act.TEXTOS)) assert.ok(swift.includes(`"${k}": "${v}"`), k);
});

// ───────────── host-ui ─────────────
const PiezaHost = require(path.join(BASE, "piezas/host-ui/ui/host.js"));
function ventanaFalsa(extra = {}) {
  return { console: { warn() {} }, document: { documentElement: { dataset: {} } }, ...extra };
}

test("host-ui: en el navegador responde simular (mapa o función) con copias JSON", async () => {
  const v = ventanaFalsa();
  const vistos = [];
  const host = PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: v, simular: {
    ...PiezaHost.simulacionesComunes({ espera: 0 }),
    guardar: (d, c) => { d.texto = "cambiado"; c.responder("guardado", { ok: true, d }); },
  } });
  assert.equal(host.plataforma, "web");
  assert.equal(host.esWeb, true);
  assert.equal(v.document.documentElement.dataset.host, "web");
  host.responder({ guardado: (r) => vistos.push(r), iaProbada: (r) => vistos.push(r), __proto__: () => {} });
  assert.equal(v.Ana.guardado !== undefined, true, "queda en window.Ana");
  const datos = { texto: "original", raro: () => 1 };
  host.enviar("guardar", datos);
  assert.equal(datos.texto, "original", "la simulación recibe una copia, como por el puente de verdad");
  assert.deepEqual(vistos[0], { ok: true, d: { texto: "cambiado" } });
  host.enviar("probarIA", { ia: "claude" });
  await esperar(5);
  assert.deepEqual(vistos[1], { ia: "claude", ok: true });
  assert.equal(host.enviar("noSimulada", {}), undefined, "una acción sin simular no hace nada");
  const funcion = PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: ventanaFalsa(), simular: (a, d, c) => [a, d, typeof c.responder] });
  assert.deepEqual(funcion.enviar("listo", [1, 2]), ["listo", {}, "function"], "datos que no son objeto viajan como {}");
});

test("host-ui: Mac, Electron y celular reciben {accion, datos}; Minuta puede seguir plano", () => {
  const mensajes = [];
  const mac = ventanaFalsa({ ANA_HOST: "mac", webkit: { messageHandlers: { ana: { postMessage: (m) => mensajes.push(["mac", m]) } } } });
  PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: mac }).enviar("probarIA", { ia: "codex" });
  const win = ventanaFalsa({ ANA_HOST: "windows", anaEscritorio: { enviar: (m) => mensajes.push(["win", m]) } });
  const h = PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: win });
  assert.equal(h.esEscritorio, true);
  h.enviar("config", { tema: "oscuro" });
  const cel = ventanaFalsa({ ANA_HOST: "movil", anaMovil: { enviar: (m) => mensajes.push(["movil", m]) } });
  PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: cel }).enviar("listo");
  const minuta = ventanaFalsa({ ANA_HOST: "linux", anaHost: { enviar: (m) => mensajes.push(["plano", m]) } });
  PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: minuta, plano: true, canales: { escritorio: "anaHost" } }).enviar("probarIA", { ia: "claude", accion: "otra" });
  assert.deepEqual(mensajes, [
    ["mac", { accion: "probarIA", datos: { ia: "codex" } }],
    ["win", { accion: "config", datos: { tema: "oscuro" } }],
    ["movil", { accion: "listo", datos: {} }],
    ["plano", { ia: "claude", accion: "probarIA" }],
  ]);
  const raro = ventanaFalsa({ ANA_HOST: "<script>" });
  assert.equal(PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: raro }).plataforma, "web", "una plataforma desconocida es la vista previa");
});

test("host-ui: nombres, acciones y respuestas validados", () => {
  for (const o of [{ nombre: "Ana", global: "Ana" }, { nombre: "ana app", global: "Ana" }, { nombre: "ana", global: "ana" }, { nombre: "ana", global: "A.b" },
    { nombre: "ana", global: "Ana", canales: { escritorio: "x;y" } }]) assert.throws(() => PiezaHost.crearHost({ ...o, ventana: ventanaFalsa() }), JSON.stringify(o));
  const host = PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: ventanaFalsa(), simular: {} });
  assert.throws(() => host.enviar("../x"));
  assert.throws(() => host.enviar(""));
  assert.equal(host.llamar("__proto__", {}), undefined);
  assert.equal(host.llamar("noExiste", {}), undefined);
  const abiertas = [];
  const v = ventanaFalsa({ open: (...a) => abiertas.push(a) });
  const h2 = PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: v, simular: PiezaHost.simulacionesComunes() });
  h2.enviar("abrirEnlace", { url: "javascript:alert(1)" });
  h2.enviar("abrirEnlace", { url: "http://ejemplo.cl" });
  h2.enviar("abrirEnlace", { url: "https://ejemplo.cl/a" });
  assert.deepEqual(abiertas, [["https://ejemplo.cl/a", "_blank", "noopener"]]);
  h2.cancelarPendientes();
});

// ───────────── tema ─────────────
const PiezaTema = require(path.join(BASE, "piezas/tema/ui/tema.js"));
function temaFalso(oscuroSistema = false) {
  const guardados = [], cambios = [];
  const escuchas = [];
  const ventana = { matchMedia: () => ({ matches: oscuroSistema, addEventListener: (e, f) => escuchas.push(f), removeEventListener() {} }), location: { search: "" } };
  const documento = { documentElement: { dataset: {} } };
  const tema = PiezaTema.crear({ ventana, documento, guardar: (v) => guardados.push(v), alCambiar: (r, v) => cambios.push([r, v]) });
  return { tema, documento, guardados, cambios, escuchas };
}
test("tema: aplicar pone o quita data-pz-modo (nunca data-tema, que puede ser de la app); un valor raro es «sistema»", () => {
  const { tema, documento, cambios } = temaFalso(true);
  assert.equal(tema.aplicar("oscuro"), "oscuro");
  assert.equal(documento.documentElement.dataset.pzModo, "oscuro");
  assert.equal("tema" in documento.documentElement.dataset, false, "data-tema queda libre para la app");
  assert.equal(PiezaTema.ATRIBUTO, "data-pz-modo");
  assert.equal(tema.aplicar("claro"), "claro");
  assert.equal(tema.resuelto(), "claro");
  assert.equal(tema.aplicar("morado"), "sistema");
  assert.equal("pzModo" in documento.documentElement.dataset, false);
  assert.equal(tema.resuelto(), "oscuro", "el sistema está oscuro");
  assert.deepEqual(cambios.at(-1), ["oscuro", "sistema"]);
});
test("tema: elegir sigue ?tema= > config > sistema, y el selector guarda", () => {
  const { tema, guardados, escuchas } = temaFalso();
  assert.equal(tema.elegir({ config: "oscuro", url: null }), "oscuro");
  assert.equal(tema.elegir({ config: "oscuro", url: "claro" }), "claro");
  assert.equal(tema.elegir({ config: "<x>", url: "nada" }), "sistema");
  assert.equal(tema.elegir({ config: "claro" }), "claro", "sin ?tema= en la dirección");
  tema.aplicar("claro");
  const h = tema.selectorHTML();
  assert.match(h, /class="pz-seg" role="group" aria-label="Apariencia"/);
  assert.match(h, /data-pz-tema="claro" aria-pressed="true">Claro</);
  assert.match(h, /data-pz-tema="sistema" aria-pressed="false">Como el sistema</);
  const clic = (v) => ({ preventDefault() {}, target: { closest: (s) => (s === "button[data-pz-tema]" && v ? { getAttribute: () => v } : null) } });
  assert.equal(tema.manejarClic(clic("oscuro")), true);
  assert.equal(tema.manejarClic(clic("rojo")), false);
  assert.equal(tema.manejarClic(clic(null)), false);
  assert.deepEqual(guardados, ["oscuro"]);
  const vistos = [];
  tema.escuchar((r) => vistos.push(r));
  escuchas[0]();
  assert.deepEqual(vistos, [], "con un tema elegido el cambio del sistema no importa");
  tema.aplicar("sistema"); escuchas[0]();
  assert.deepEqual(vistos, ["claro"]);
});
test("tema: cada token tiene su par y el respaldo sin light-dark() los nombra todos", () => {
  const css = fs.readFileSync(path.join(BASE, "piezas/tema/ui/tema.css"), "utf8");
  const tokens = [...css.matchAll(/--([a-z0-9-]+): light-dark\(var\(--\1-claro\), var\(--\1-oscuro\)\)/g)].map((m) => m[1]);
  assert.ok(tokens.length >= 12, tokens.join());
  const respaldo = css.slice(css.indexOf("@supports not"));
  for (const t of tokens) {
    assert.match(css, new RegExp(`--${t}-claro:`), t);
    assert.match(css, new RegExp(`--${t}-oscuro:`), t);
    for (const modo of ["claro", "oscuro"]) assert.equal((respaldo.match(new RegExp(`--${t}: var\\(--${t}-${modo}\\)`, "g")) || []).length, modo === "claro" ? 1 : 2, `${t} ${modo}`);
  }
});

// ───────────── componentes ─────────────
const PiezaComponentes = require(path.join(BASE, "piezas/componentes/ui/componentes.js"));
function componentes(extra = {}) {
  const i18n = i18nEn();
  i18n.usar({ codigo: "en", nombre: "English", textos: { ...EN.textos, "Paso {n} de {total}": "Step {n} of {total}", "Hay una versión nueva de {app}": "There's a new version of {app}" } });
  const enviados = [];
  let pintadas = 0;
  const host = { plataforma: "mac", enviar: (a, d) => enviados.push([a, d]) };
  const ui = PiezaComponentes.crear({ i18n, host, app: "Ana <b>", repo: "ana-app/ana", pintar: () => pintadas++, documento: null, ventana: { navigator: { userAgent: "Mac OS X 15_2" } }, ...extra });
  return { ui, enviados, pintadas: () => pintadas, i18n };
}
const clicEn = (attrs) => ({ preventDefault() {}, target: {
  closest: (sel) => (Object.keys(attrs).some((a) => sel.includes(`[${a}]`)) ? { hasAttribute: (a) => a in attrs, getAttribute: (a) => attrs[a] } : null),
  matches: () => false } });

test("componentes: filas de IA escapan, prueban con {ia} y muestran el error traducido", () => {
  const { ui, enviados } = componentes();
  const ias = [{ id: "claude", nombre: "<img src=x onerror=alert(1)>", instalada: true }, { id: "codex", nombre: "Codex", instalada: false }, { id: "../mal", nombre: "x", instalada: true }];
  let h = ui.filasIA({ ias, elegida: "claude", guia: "https://ana-app.github.io/ana/ia.html" });
  assert.match(h, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.doesNotMatch(h, /<img/);
  assert.doesNotMatch(h, /\.\.\/mal/);
  assert.match(h, /data-pz-enlace="https:\/\/ana-app.github.io\/ana\/ia.html#codex">Cómo instalarla/);
  assert.match(h, />Probar otra vez</);
  assert.equal(ui.manejarClic(clicEn({ "data-pz-probar-ia": "codex" })), true);
  assert.deepEqual(enviados.at(-1), ["probarIA", { ia: "codex" }]);
  assert.match(ui.filasIA({ ias }), /aria-label="Probando…"/);
  ui.iaProbada({ ia: "claude", ok: false, plantilla: "No encontré {ia} en este computador.", valores: { ia: "<Claude>" }, ayuda: "Revisa en Ajustes → Tu IA." });
  h = ui.filasIA({ ias });
  assert.match(h, /pz-error-texto" data-sin-traducir>No encontré &lt;Claude&gt; en este computador\.<\/small>/,
    "sin la «ayuda» de la app: la fila ya está en «Tu IA»");
  ui.iaProbada({ id: "claude", ok: true });   // la forma vieja también se entiende
  assert.deepEqual(enviados.at(-1), ["config", { ia: "claude" }]);
  assert.match(ui.filasIA({ ias, elegida: "claude" }), /class="pz-ok">Lista</);
  assert.equal(ui.probarIA("rm -rf"), false);
  assert.match(ui.filasIA({ ias: [] }), /No encontré ninguna IA instalada/);
});

test("componentes: la fila de actualización sigue la forma de la pieza actualizaciones", () => {
  const { ui, enviados } = componentes();
  assert.match(ui.filaActualizacion(), /<span data-sin-traducir>Ana &lt;b&gt; checks|revisa sola/);
  assert.equal(ui.manejarClic(clicEn({ "data-pz-act": "buscar" })), true);
  assert.deepEqual(enviados.at(-1), ["buscarActualizacion", {}]);
  assert.match(ui.filaActualizacion(), /Buscando…[\s\S]*disabled/);
  ui.actualizacionRevisada({ hay: false, sinConexion: true });
  assert.match(ui.filaActualizacion(), /No pude revisar: sin conexión/);
  ui.actualizacionRevisada({ hay: true, version: "0.2.0", notas: "• <script>x</script>", texto: "Versión {v}", valores: { v: "0.2.0" }, desarrollo: false });
  let h = ui.filaActualizacion();
  assert.match(h, /There&#39;s a new version of Ana &lt;b&gt;/);
  assert.match(h, /&lt;script&gt;x&lt;\/script&gt;/);
  assert.match(h, /data-pz-act="instalar">Actualizar ahora/);
  ui.manejarClic(clicEn({ "data-pz-act": "instalar" }));
  assert.deepEqual(enviados.at(-1), ["actualizar", {}]);
  ui.actualizacionProgreso({ paso: "2", texto: "Preparando la versión nueva…", valores: {}, total: 3, pct: 140 });
  h = ui.filaActualizacion();
  assert.match(h, /Step 2 of 3/);
  assert.match(h, / · 100%/);
  assert.match(h, /<progress class="pz-progreso" max="300" value="200">/);
  ui.actualizacionProgreso({ paso: "error", codigo: "errorBajar", texto: "No pude descargar la versión nueva. Revisa tu conexión e intenta de nuevo.", valores: {} });
  h = ui.filaActualizacion();
  assert.match(h, /pz-error-texto/);
  assert.match(h, /data-pz-act="buscar">Buscar de nuevo/);
  assert.doesNotMatch(h, /Step/);
});

test("componentes: diálogo, confirmar, Acerca de y enlaces solo https", async () => {
  const { ui, enviados } = componentes();
  const d = ui.dialogo({ id: "t-aj", titulo: "Hola, **{nombre}**", valores: { nombre: "<x>" }, cuerpo: "<p>c</p>", pie: "<b>p</b>", clase: "pz-ancho mal\"clase" });
  assert.match(d, /role="dialog" aria-modal="true" aria-labelledby="t-aj"/);
  assert.match(d, /class="pz-dialogo pz-ancho"/);
  assert.match(d, /<h2 id="t-aj" tabindex="-1" data-sin-traducir>Hi, <b>&lt;x&gt;<\/b><\/h2>/);
  assert.match(d, /data-pz-cerrar aria-label="Cerrar"/);
  assert.doesNotMatch(ui.dialogo({ id: "x", titulo: "T", cerrable: false }), /data-pz-cerrar/);
  assert.match(ui.dialogo({ id: "x", titulo: "T", sinEsc: true }), /data-pz-sin-esc/);
  assert.throws(() => ui.dialogo({ id: "a\" onclick=\"x", titulo: "T" }));
  const p = ui.confirmar({ titulo: "¿Borrar «{x}»?", valores: { x: "<b>nota</b>" }, si: "Borrar", peligro: true });
  assert.match(ui.capas(), /role="alertdialog"[\s\S]*&lt;b&gt;nota&lt;\/b&gt;[\s\S]*data-pz-confirmar="no" data-autofoco[\s\S]*pz-principal pz-peligro" data-pz-confirmar="si" data-sin/,
    "con peligro, el foco empieza en «Cancelar»");
  assert.equal(ui.hayCapa, true);
  ui.manejarClic(clicEn({ "data-pz-confirmar": "si" }));
  assert.equal(await p, true);
  assert.equal(ui.capas(), "");
  const p2 = ui.confirmar({ titulo: "¿Seguro?" });
  ui.manejarClic(clicEn({ "data-pz-cerrar": "" }));
  assert.equal(await p2, false, "cerrar es «no»");
  const a = ui.acercaDe({ version: "1.0", enlaces: { codigo: "https://github.com/ana-app/ana", sitio: "javascript:alert(1)", comunidad: "http://x.cl", aportar: "https://x.cl/\"><img" } });
  assert.match(a, /data-pz-enlace="https:\/\/github.com\/ana-app\/ana">Código/);
  assert.doesNotMatch(a, /javascript|http:\/\/x|<img/);
  assert.match(a, /Ana &lt;b&gt; 1.0 · Gratis y abierto \(AGPL-3.0\)/);
  assert.match(a, /data-pz-comentarios="error">Enviar comentarios/);
  ui.manejarClic(clicEn({ "data-pz-enlace": "https://github.com/ana-app/ana" }));
  ui.manejarClic(clicEn({ "data-pz-enlace": "file:///etc/passwd" }));
  assert.deepEqual(enviados.filter((x) => x[0] === "abrirEnlace"), [["abrirEnlace", { url: "https://github.com/ana-app/ana" }]]);
});

test("componentes: comentarios abren un issue prellenado del repo de la app, sin datos de la persona", () => {
  const { ui, enviados } = componentes({ version: "0.3.0" });
  assert.equal(PiezaComponentes.urlIssue("mal repo", {}), null);
  assert.equal(PiezaComponentes.urlIssue("a/b/../c", {}), null);
  const u = PiezaComponentes.urlIssue("ana-app/ana", { titulo: "💡 Más <b>", cuerpo: "a&b=c", etiqueta: "idea" });
  assert.equal(u, "https://github.com/ana-app/ana/issues/new?title=%F0%9F%92%A1%20M%C3%A1s%20%3Cb%3E&body=a%26b%3Dc&labels=idea");
  assert.doesNotMatch(PiezaComponentes.urlIssue("ana-app/ana", { etiqueta: "x&y" }), /labels/);
  assert.equal(PiezaComponentes.sistemaDe("mac", { userAgent: "Mozilla (Macintosh; Intel Mac OS X 15_2)" }), "macOS 15.2");
  assert.equal(PiezaComponentes.sistemaDe("linux"), "Linux");
  ui.manejarClic(clicEn({ "data-pz-comentarios": "idea" }));
  assert.match(ui.capas(), /aria-labelledby="pz-t-coment"[\s\S]*data-pz-coment-tipo="idea" aria-pressed="true"/);
  ui.manejarClic(clicEn({ "data-pz-coment-enviar": "" }));
  assert.match(ui.capas(), /aria-invalid="true"[\s\S]*Escribe un título\./, "sin título no se envía");
  assert.equal(enviados.length, 0);
  const datos = ui.datosComentario({ tipo: "idea", titulo: "Modo oscuro", texto: "Por favor", sistema: true, version: "0.3.0" });
  assert.deepEqual(datos, { titulo: "💡 Modo oscuro", cuerpo: "Por favor\n\n---\nAna <b> 0.3.0 · en · macOS 15.2", etiqueta: "idea" });
  assert.equal(ui.datosComentario({ tipo: "error", titulo: "x", texto: "y", sistema: false }).cuerpo, "y");
});

test("componentes: avisos en cola, uno a la vez, sin repetir y esperando la bienvenida", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const clases = new Set();
  const el = { textContent: "", setAttribute() {}, classList: { add: (c) => clases.add(c), remove: (c) => clases.delete(c), toggle: (c, s) => (s ? clases.add(c) : clases.delete(c)) } };
  const documento = { getElementById: (id) => (id === "toast" ? el : null) };
  const retenidos = [];
  let esperar = true;
  const { ui } = componentes({ documento, duracion: 1000, pausa: 100, retener: (...a) => (esperar ? (retenidos.push(a), true) : false) });
  assert.equal(ui.aviso("Guardar"), false);
  assert.deepEqual(retenidos, [["Guardar", {}]]);
  esperar = false;
  ui.aviso("Guardar");                      // se traduce con Tp
  ui.aviso("Comentarios");
  ui.aviso("Comentarios");                  // repetido: no entra
  ui.aviso("<b>listo</b>", { traducido: true, error: true });
  assert.equal(el.textContent, "Save");
  assert.ok(clases.has("visible") && clases.has("pz-toast"));
  assert.deepEqual(ui.avisos.enCola, ["Comments", "<b>listo</b>"]);
  t.mock.timers.tick(1080);                 // 900 + 45·4 = 1080 ms visible
  assert.equal(clases.has("visible"), false, "se esconde antes del siguiente");
  t.mock.timers.tick(100);                  // y la pausa
  assert.equal(el.textContent, "Comments");
  t.mock.timers.tick(1400); t.mock.timers.tick(100);
  assert.equal(el.textContent, "<b>listo</b>", "texto plano: nunca HTML");
  assert.ok(clases.has("pz-error"));
  t.mock.timers.tick(3000); t.mock.timers.tick(100);
  assert.equal(ui.avisos.actual, null);
  assert.equal(clases.has("visible"), false);
  for (let i = 0; i < 9; i++) ui.aviso(`Aviso ${i}`, { traducido: true });
  assert.deepEqual(ui.avisos.enCola, ["Aviso 5", "Aviso 6", "Aviso 7", "Aviso 8"], "si se juntan muchos quedan los últimos");
  ui.avisos.limpiar();
});

test("componentes 0.2: dialogo con «antes», título propio o sin título; envolver", () => {
  const { ui } = componentes();
  const d = ui.dialogo({ id: "t-bv", antes: '<div class="puntos"></div>', tituloHTML: '<span lang="es">Elige</span> · <span lang="en">Choose</span>', cuerpo: "<p>c</p>", clave: "paso-1" });
  assert.match(d, /data-pz-clave="paso-1">\s*<div class="puntos"><\/div><div class="pz-cabeza"><h2 id="t-bv" tabindex="-1" data-sin-traducir><span lang="es">Elige<\/span>/, "lo de antes va antes del título; el título propio va tal cual");
  const sin = ui.dialogo({ id: "t-x", cuerpo: '<h2 id="t-x">Mío</h2>', cerrable: false });
  assert.doesNotMatch(sin, /pz-cabeza/, "sin título ni ✕, no hay cabecera");
  assert.match(sin, /aria-labelledby="t-x"[\s\S]*<h2 id="t-x">Mío<\/h2>/);
  const e = ui.envolver('<h2 id="t-propio">Propio</h2><p>x</p>', { id: "t-propio", clase: "pz-ancho", sinEsc: true });
  assert.match(e, /class="pz-capa" data-pz-capa><div class="pz-dialogo pz-ancho" role="dialog" aria-modal="true" aria-labelledby="t-propio" tabindex="-1" data-pz-sin-esc>/);
  assert.doesNotMatch(e, /data-pz-cerrar/);
  assert.match(ui.envolver("<h2 id='a'>A</h2>", { id: "a", cerrable: true }), /data-pz-cerrar/);
  assert.throws(() => ui.envolver("<p>sin id</p>", {}));
  assert.doesNotMatch(ui.dialogo({ id: "t", titulo: "T", clave: 'x" onclick="y' }), /onclick/, "una clave rara no entra");
});

test("componentes 0.3: confirmar sin peligro enfoca el título (ningún botón con data-autofoco); con sinElegir, Esc y el velo no son «no»", async () => {
  const { ui } = componentes();
  const p = ui.confirmar({ titulo: "¿Seguro?" });
  assert.doesNotMatch(ui.capas(), /data-autofoco/, "sin peligro el foco va al título, como en todo diálogo");
  assert.match(ui.capas(), /<h2 id="pz-t-conf" tabindex="-1"/);
  ui.manejarClic(clicEn({ "data-pz-cerrar": "" }));
  assert.equal(await p, false);
  const q = ui.confirmar({ titulo: "¿Guardar los cambios?", si: "Guardar", no: "No guardar", sinElegir: null });
  ui.manejarClic(clicEn({ "data-pz-cerrar": "" }));
  assert.equal(await q, null, "Esc o el velo: ni sí ni no");
  const r = ui.confirmar({ titulo: "Uno", sinElegir: null });
  const r2 = ui.confirmar({ titulo: "Otro" });
  assert.equal(await r, null, "una confirmación que reemplaza a otra la deja sin elegir");
  ui.manejarClic(clicEn({ "data-pz-confirmar": "no" }));
  assert.equal(await r2, false);
});

test("componentes 0.2: aviso con botón, frases ya armadas (tr) y #toast listo desde el inicio", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const clases = new Set(), hijos = [], atributos = {};
  const el = { textContent: "", setAttribute: (a, v) => { atributos[a] = v; }, appendChild: (h) => hijos.push(h),
    classList: { add: (...c) => c.forEach((x) => clases.add(x)), remove: (...c) => c.forEach((x) => clases.delete(x)), toggle: (c, s) => (s ? clases.add(c) : clases.delete(c)) } };
  let escuchas = {};
  const documento = { getElementById: (id) => (id === "toast" ? el : null),
    createElement: (tag) => ({ tag, type: "", className: "", textContent: "", addEventListener: (e, f) => { escuchas[e] = f; } }) };
  const i18n = i18nEn();
  i18n.usar({ codigo: "en", nombre: "English", textos: { ...EN.textos, "Quedan {n} días": "{n} days left", "Deshacer": "Undo", "Borré «{x}»": "Deleted «{x}»" } });
  const ui = PiezaComponentes.crear({ i18n, app: "Ana", documento, duracion: 1000, pausa: 100 });
  assert.ok(clases.has("pz-toast") && "data-sin-traducir" in atributos, "#toast queda con pz-toast y data-sin-traducir al crear");
  ui.aviso("Quedan 3 días");                // ya armada en español: va por tr
  assert.equal(el.textContent, "3 days left");
  t.mock.timers.tick(5000); t.mock.timers.tick(100);
  let deshecho = 0;
  ui.aviso("Borré «{x}»", { valores: { x: "Nota <b>" }, accion: { texto: "Deshacer", f: () => deshecho++ } });
  assert.equal(el.textContent, "Deleted «Nota <b>»");
  assert.equal(hijos.length, 1);
  assert.equal(hijos[0].tag, "button");
  assert.equal(hijos[0].textContent, "Undo", "el botón se traduce y va como texto");
  assert.ok(clases.has("pz-con-accion"));
  t.mock.timers.tick(4000);
  assert.ok(clases.has("visible"), "con botón dura más (al menos 6 s)");
  escuchas.click({ preventDefault() {} });
  assert.equal(deshecho, 1);
  assert.equal(clases.has("visible"), false, "tocar el botón cierra el aviso");
  t.mock.timers.tick(200);
  assert.equal(ui.avisos.actual, null);
  assert.equal(clases.has("pz-con-accion"), false);
  ui.aviso("Hecho", { traducido: true, accion: { texto: "Ver", f: () => deshecho++ } });
  assert.equal(ui.avisos.accionar(), true, "un atajo de la app puede tocar el botón");
  assert.equal(deshecho, 2);
  assert.equal(ui.avisos.accionar(), false);
  ui.aviso("Sin f", { traducido: true, accion: { texto: "X" } });
  assert.equal(hijos.length, 2, "un botón sin función no se pinta");
  ui.avisos.limpiar();
});

test("componentes 0.2: filasIA con detalle, «Revisar de nuevo» y un solo botón principal", () => {
  const { ui, enviados } = componentes();
  const ias = [{ id: "claude", nombre: "Claude", instalada: true }, { id: "codex", nombre: "Codex", instalada: true },
    { id: "telefono", nombre: "Este teléfono", instalada: false, detalle: "Comentarios" }];
  let h = ui.filasIA({ ias });
  assert.equal((h.match(/pz-principal/g) || []).length, 1, "sin ninguna en uso, solo la primera instalada es principal");
  assert.match(h, /data-sin-traducir>Comments<\/span>/, "el detalle se traduce con tr");
  assert.match(h, /pz-boton pz-plano" data-pz-probar-ia="telefono" >Revisar de nuevo/);
  assert.equal((ui.filasIA({ ias, principal: "todas" }).match(/pz-principal/g) || []).length, 2, "la forma de 0.1.0");
  assert.equal((ui.filasIA({ ias, principal: false }).match(/pz-principal/g) || []).length, 0);
  assert.equal((ui.filasIA({ ias, elegida: "codex" }).match(/pz-principal/g) || []).length, 0, "con una en uso, ninguna grita");
  ui.manejarClic(clicEn({ "data-pz-probar-ia": "telefono" }));
  assert.deepEqual(enviados.at(-1), ["probarIA", { ia: "telefono" }]);
  ui.iaProbada({ ia: "telefono", ok: true });
  h = ui.filasIA({ ias, elegida: "telefono" });
  assert.match(h, /data-pz-probar-ia="telefono" >Probar otra vez/, "probó bien: ahora cuenta como instalada");
  assert.doesNotMatch(h, /Comments/);
});

test("componentes 0.2: versión como función, Acerca de con enlaces extra, actualizaciones con detalle, desarrollo y sin pintar", () => {
  let version = "";
  const { ui, pintadas } = componentes({ version: () => version });
  version = "2.1";
  const a = ui.acercaDe({ enlaces: {}, extra: [{ texto: "Guía de la IA", url: "https://ana-app.github.io/ana/ia.html" }, { texto: "Mal", url: "javascript:x" }, { texto: "", url: "https://x.cl" }] });
  assert.match(a, /Ana &lt;b&gt; 2\.1 · Gratis/, "la versión se lee al pintar");
  assert.match(a, /data-pz-enlace="https:\/\/ana-app.github.io\/ana\/ia.html">Guía de la IA</);
  assert.doesNotMatch(a, /javascript|>Mal<|x\.cl/);
  assert.equal(ui.datosComentario({ tipo: "otro", titulo: "t", texto: "", sistema: true, version: version }).cuerpo.includes("2.1"), true);
  const antes = pintadas();
  ui.actualizacionDisponible({ hay: true, version: "2.2", detalle: "Notas <de antes>", texto: "Versión {v}", valores: { v: "2.2" } }, { pintar: false });
  assert.equal(pintadas(), antes, "{pintar: false} solo lo anota");
  assert.match(ui.filaActualizacion(), /Notas &lt;de antes&gt;/, "detalle sirve como notas");
  ui.actualizacionRevisada({ hay: true, version: "", texto: "", notas: "• arreglo", desarrollo: true }, { pintar: false });
  assert.equal(pintadas(), antes);
  const h = ui.filaActualizacion();
  assert.match(h, /Hay cambios nuevos en el código de Ana &lt;b&gt;/);
  assert.match(h, /• arreglo/);
  ui.actualizacionRevisada({ hay: false });
  assert.equal(pintadas(), antes + 1);
});

test("componentes 0.3: revisable, clases del título y de la capa, «hay» sin versión no es desarrollo", () => {
  const { ui } = componentes();
  const ias = [{ id: "claude", nombre: "Claude", instalada: true }, { id: "telefono", nombre: "Este teléfono", instalada: false, detalle: "Comentarios", revisable: false }];
  const h = ui.filasIA({ ias });
  assert.doesNotMatch(h, /data-pz-probar-ia="telefono"/, "una IA que todavía no existe no ofrece «Revisar de nuevo»");
  assert.match(h, /<b data-sin-traducir>Este teléfono<\/b><small><span data-sin-traducir>Comments<\/span><\/small><\/span><\/div>/);
  assert.match(h, /data-pz-probar-ia="claude"/);
  const d = ui.dialogo({ id: "t-x", tituloHTML: "Hola", claseTitulo: "grande mal\"x", claseCapa: "velo-oscuro" });
  assert.match(d, /<div class="pz-capa velo-oscuro" data-pz-capa>/);
  assert.match(d, /<h2 id="t-x" class="grande" tabindex="-1"/, "solo clases con forma de clase");
  assert.match(ui.dialogo({ id: "t-y", titulo: "T" }), /<h2 id="t-y" tabindex="-1"/, "sin claseTitulo, sin class");
  assert.match(ui.envolver('<h2 id="t-z">Z</h2>', { id: "t-z", claseCapa: "completa" }), /<div class="pz-capa completa" data-pz-capa><div class="pz-dialogo"/);
  ui.actualizacionRevisada({ hay: true, notas: "• algo" }, { pintar: false });
  assert.match(ui.filaActualizacion(), /There&#39;s a new version of Ana/, "sin versión ni texto sigue siendo un Release");
  assert.doesNotMatch(ui.filaActualizacion(), /cambios nuevos en el código/);
  ui.actualizacionRevisada({ hay: true, notas: "• commit", desarrollo: true }, { pintar: false });
  assert.match(ui.filaActualizacion(), /Hay cambios nuevos en el código de Ana/, "solo con desarrollo: true");
});

test("i18n 0.3.1: con noTraducirAtributos, [data-sin-traducir] siempre cuenta (también para sus atributos)", () => {
  const con = PiezaI18n.crear({ noTraducir: "[data-nota]", noTraducirAtributos: "[data-propio]" });
  con.usar(EN);
  const suyo = el("span", { "data-sin-traducir": "", title: "Guardar" }, [el("i", { title: "Guardar" })]);
  const zona = el("div", { "data-nota": "" }, [el("button", { title: "Guardar" }, ["Guardar"]), suyo]);
  const fuera = el("b", { "data-sin-traducir": "", "aria-label": "Guardar" });
  con.traducirDOM(el("section", {}, [zona, fuera]));
  assert.equal(zona.childNodes[0].attrs.title, "Save", "un botón de la app dentro de la zona, sí");
  assert.equal(suyo.attrs.title, "Guardar", "data-sin-traducir dentro de la zona: no");
  assert.equal(suyo.childNodes[0].attrs.title, "Guardar", "ni lo que tiene adentro");
  assert.equal(fuera.attrs["aria-label"], "Guardar", "ni fuera de la zona");
  con.traducirDOM(suyo);
  assert.equal(suyo.attrs.title, "Guardar", "tampoco si es la raíz");
});

test("host-ui 0.2: responder acepta objetos; reasignar window.<App> avisa y suma al mismo objeto", () => {
  const avisos = [];
  const v = ventanaFalsa({ console: { warn: (m) => avisos.push(m) } });
  const host = PiezaHost.crearHost({ nombre: "ana", global: "Ana", ventana: v });
  const respuestas = v.Ana;
  host.responder({ estado() {}, _pruebas: { sumar: (a, b) => a + b }, numero: 3 });
  assert.equal(v.Ana._pruebas.sumar(1, 2), 3);
  assert.equal("numero" in v.Ana, false);
  assert.match(avisos.at(-1), /numero no es una función/);
  assert.equal(host.llamar("_pruebas", {}), undefined, "un objeto nunca es una respuesta");
  v.Ana = { tarde() { return "ok"; } };
  assert.equal(v.Ana, respuestas, "el objeto es el mismo");
  assert.equal(typeof v.Ana.estado, "function", "lo de antes sigue");
  assert.equal(v.Ana.tarde(), "ok", "lo nuevo se sumó");
  assert.match(avisos.at(-1), /no reasignes window\.Ana/);
});

test("i18n 0.3: placeholder de un textarea y atributos en zonas sin traducir (noTraducirAtributos)", () => {
  const i = i18nEn();
  const area = el("textarea", { placeholder: "Comentarios", title: "Guardar" }, ["Guardar"]);
  const nuevaZona = () => el("div", { "data-nota": "" }, ["Guardar", el("button", { title: "Guardar" }, ["Guardar"]), el("i", { "data-propio": "", title: "Guardar" })]);
  let zona = nuevaZona();
  const raiz = el("div", {}, [area, zona]);
  i.traducirDOM(raiz);
  assert.equal(area.attrs.placeholder, "Comments", "el placeholder es de la app");
  assert.equal(area.attrs.title, "Save");
  assert.equal(area.childNodes[0].nodeValue, "Guardar", "lo escrito en el textarea es de la persona");
  const sin = PiezaI18n.crear({ noTraducir: "[data-nota]" });
  sin.usar(EN);
  zona = nuevaZona();
  sin.traducirDOM(el("section", {}, [zona]));
  assert.equal(zona.childNodes[1].attrs.title, "Guardar", "sin la opción, una zona sin traducir tampoco traduce atributos (como antes)");
  const con = PiezaI18n.crear({ noTraducir: "[data-nota]", noTraducirAtributos: "[data-propio]" });
  con.usar(EN);
  zona = nuevaZona();
  con.traducirDOM(el("section", {}, [zona]));
  assert.equal(zona.childNodes[0].nodeValue, "Guardar", "el texto de la zona no se traduce");
  assert.equal(zona.childNodes[1].attrs.title, "Save", "el title de un botón de la app, sí");
  assert.equal(zona.childNodes[2].attrs.title, "Guardar", "lo que diga noTraducirAtributos, no");
});

test("componentes, tema y host-ui: sin eval, sin innerHTML, sin estilos ni manejadores en línea, nada de una app adentro", () => {
  for (const f of ["piezas/host-ui/ui/host.js", "piezas/tema/ui/tema.js", "piezas/componentes/ui/componentes.js"]) {
    const t = fs.readFileSync(path.join(BASE, f), "utf8");
    assert.doesNotMatch(t, /\beval\(|new Function|innerHTML\s*=|style="|\.style\.cssText|setAttribute\("style"|\son[a-z]+=/, f);
    assert.doesNotMatch(t, /esquema|minuta|graba|corta|repasa|alcanc/i, f);
  }
  for (const f of ["piezas/tema/ui/tema.css", "piezas/componentes/ui/componentes.css"]) {
    const t = fs.readFileSync(path.join(BASE, f), "utf8");
    assert.doesNotMatch(t, /@import|url\(|esquema|minuta|graba|corta|repasa|alcanc/i, f);
  }
});

// ───────────── cifrado ─────────────
const PiezaCifrado = require(path.join(BASE, "piezas/cifrado/ui/cifrado.js"));
const FRASE = "caballo batería grapa correcta";

test("cifrado: armar y abrir con la frase o con la llave guardada; nombres opacos estables", async () => {
  const c = PiezaCifrado.crear({ app: "Prueba", contexto: "prueba:copia", tipo: "copia" });
  const { cabecera, llaves } = await c.nuevaCabecera(FRASE.normalize("NFD"));
  const texto = await c.armar({ hola: "Ana Pérez" }, cabecera, llaves);
  assert.ok(!texto.includes("Ana"));
  const a = await c.abrir(texto, { frase: FRASE });
  assert.deepEqual(a.contenido, { hola: "Ana Pérez" }, "la frase se normaliza (NFC)");
  const b = await c.abrir(texto, { raw: llaves.raw });
  assert.deepEqual(b.contenido, a.contenido);
  const n1 = await c.nombreOpaco(llaves, "perfiles/ana.json");
  assert.match(n1, /^[0-9a-f]{32}$/);
  assert.equal(await c.nombreOpaco(a.llaves, "perfiles/ana.json"), n1);
  assert.notEqual(await c.nombreOpaco(llaves, "perfiles/matias.json"), n1);
});

test("cifrado: frase mala, sobre cambiado, AAD de otro lugar, versión más nueva, tamaño y pocas vueltas", async () => {
  const c = PiezaCifrado.crear({ app: "Prueba", contexto: "prueba:copia", maximo: 50000 });
  const { cabecera, llaves } = await c.nuevaCabecera(FRASE);
  const texto = await c.armar({ x: 1 }, cabecera, llaves);
  const codigo = async (p) => { try { await p; return "ok"; } catch (e) { return e.codigo; } };
  assert.equal(await codigo(c.abrir(texto, { frase: "otra frase bastante larga" })), "frase");
  const obj = JSON.parse(texto);
  const dañado = { ...obj, datos: { ...obj.datos, datos: obj.datos.datos.replace(/^./, (x) => (x === "A" ? "B" : "A")) } };
  assert.equal(await codigo(c.abrir(JSON.stringify(dañado), { frase: FRASE })), "danado");
  assert.equal(await codigo(c.abrir(JSON.stringify({ ...obj, version: 2 }), { frase: FRASE })), "version");
  assert.equal(await codigo(c.abrir(JSON.stringify({ ...obj, kdf: { ...obj.kdf, iteraciones: 1000 } }), { frase: FRASE })), "danado");
  assert.equal(await codigo(c.abrir("x".repeat(60000), { frase: FRASE })), "no_es");
  assert.equal(await codigo(c.abrir('{"otra":"cosa"}', { frase: FRASE })), "no_es");
  const sobre = await c.cifrarJSON(llaves, { a: 1 }, "perfiles/ana");
  assert.deepEqual(await c.descifrarJSON(llaves, sobre, "perfiles/ana"), { a: 1 });
  assert.equal(await codigo(c.descifrarJSON(llaves, sobre, "perfiles/matias")), "danado", "el AAD ata el sobre a su lugar");
  assert.equal(await codigo(c.nuevaCabecera("corta")), "corta");
  const e = await c.abrir(texto, { frase: "no" }).catch((x) => x);
  assert.equal(e.plantilla, "La frase no es la correcta.");
  const v = await c.abrir(JSON.stringify({ ...obj, version: 9 }), { frase: FRASE }).catch((x) => x);
  assert.equal(v.message, "Este archivo viene de una versión más nueva de Prueba. Actualiza la app.");
  assert.equal(PiezaCifrado.fuerzaFrase("uno dos tres cuatro cinco seis").nivel, 3);
});

test("cifrado: varios sobres con el formato de Repasa, frases propias, error() con la marca y «corta» directo", async () => {
  const c = PiezaCifrado.crear({ app: "Prueba", contexto: "prueba", marca: "prueba", tipo: "copia", claveVersion: "v",
    mensajes: { no_es: "Eso no es una copia de {app}, revisa el archivo.", inventado: "x" } });
  const { cabecera, llaves } = await c.nuevaCabecera(FRASE);
  const texto = await c.armarVarios([{ ruta: "a.json" }, { ruta: "b.json" }], cabecera, llaves,
    { aad: "prueba:copia:v1", extra: { creada: "2026-10-31", kdf: "no pisa" } });
  const obj = JSON.parse(texto);
  assert.deepEqual(Object.keys(obj), ["prueba", "v", "creada", "kdf", "cifrado", "verificador", "archivos"], "el orden de Repasa");
  assert.equal(obj.archivos.length, 2);
  // Un sobre armado a mano como lo hacía Repasa (cifrarJSON con su AAD fijo) se abre igual.
  const r = await c.abrirVarios(texto, { frase: FRASE }, { aad: "prueba:copia:v1" });
  assert.deepEqual(r.contenidos, [{ ruta: "a.json" }, { ruta: "b.json" }]);
  assert.equal(r.archivo.creada, "2026-10-31");
  const codigo = async (p) => { try { await p; return "ok"; } catch (e) { return e.codigo; } };
  assert.equal(await codigo(c.abrirVarios(texto, { frase: FRASE }, { aad: "otro" })), "danado", "el AAD ata cada sobre");
  assert.equal(await codigo(c.abrirVarios(JSON.stringify({ ...obj, v: 2 }), { frase: FRASE })), "version");
  const e = await c.abrir('{"otra":1}', { frase: FRASE }).catch((x) => x);
  assert.deepEqual([e.codigo, e.plantilla, e.frase, e.valores.app], ["no_es", "Eso no es una copia de {app}, revisa el archivo.",
    "Eso no es una copia de Prueba, revisa el archivo.", "Prueba"], "la frase propia de la app, con {app}");
  assert.deepEqual(JSON.parse(JSON.stringify(e)), { ok: false, codigo: "no_es", plantilla: e.plantilla, valores: { app: "Prueba" }, error: e.frase });
  const propio = c.error("version");
  assert.ok(propio instanceof PiezaCifrado.ErrorCifrado);
  assert.equal(propio.frase, "Este archivo viene de una versión más nueva de Prueba. Actualiza la app.");
  const corta = await c.nuevaCabecera("corta").catch((x) => x);
  assert.deepEqual([corta.codigo, corta.plantilla, corta.message], ["corta", PiezaCifrado.MENSAJES.corta, PiezaCifrado.MENSAJES.corta]);
  assert.equal(c.revisarFrase("corta"), PiezaCifrado.MENSAJES.corta);
});

test("cifrado: abre lo que armaba la copia de Alcancía (llave de 256 bits) con su contexto", async () => {
  const s = crypto.webcrypto.subtle;
  const sal = crypto.randomBytes(16);
  const base = await s.importKey("raw", new TextEncoder().encode(FRASE), "PBKDF2", false, ["deriveBits"]);
  const bits = new Uint8Array(await s.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: sal, iterations: 600000 }, base, 256));
  const aes = await s.importKey("raw", bits, { name: "AES-GCM" }, false, ["encrypt"]);
  const sobre = async (texto, aad) => {
    const iv = crypto.randomBytes(12);
    const d = new Uint8Array(await s.encrypt({ name: "AES-GCM", iv, additionalData: new TextEncoder().encode(aad) }, aes, new TextEncoder().encode(texto)));
    return { iv: Buffer.from(iv).toString("base64"), datos: Buffer.from(d).toString("base64") };
  };
  const archivo = JSON.stringify({
    alcancia: "copia-celular", version: 1, kdf: { alg: "PBKDF2-SHA256", iteraciones: 600000, sal: sal.toString("base64") }, cifrado: "AES-256-GCM",
    verificador: await sobre("alcancia", "alcancia:celular:verificador"), datos: await sobre('{"formato":1,"estado":{}}', "alcancia:celular:1"),
  });
  const c = PiezaCifrado.crear({ app: "Alcancía", contexto: "alcancia:celular", verificador: "alcancia", marca: "alcancia", tipo: "copia-celular" });
  assert.deepEqual((await c.abrir(archivo, { frase: FRASE })).contenido, { formato: 1, estado: {} });
  assert.deepEqual((await c.abrir(archivo, { raw: Buffer.from(bits).toString("base64") })).contenido.formato, 1, "una llave guardada de 32 bytes");
});

// ───────────── catálogo (Electron) contra un servidor falso ─────────────
const Cat = require(path.join(BASE, "piezas/catalogo/escritorio/catalogo.js"));
import http from "node:http";

async function servidorCatalogo(rutas) {
  const vistos = [];
  const srv = http.createServer((req, res) => {
    vistos.push(req.url);
    const r = rutas[req.url];
    if (!r) { res.writeHead(404); return res.end(); }
    if (r.redirige) { res.writeHead(302, { Location: r.redirige }); return res.end(); }
    res.writeHead(200); res.end(r.cuerpo);
  });
  await new Promise((ok) => srv.listen(0, "127.0.0.1", ok));
  const puerto = srv.address().port;
  // El fetch de la app con la URL real cambiada al servidor local (las mismas opciones: redirect "error" de verdad).
  const fetchFalso = (url, opciones) => {
    const u = new URL(url);
    assert.equal(u.host, "raw.githubusercontent.com");
    assert.equal(opciones.redirect, "error");
    // Como net.fetch: la respuesta dice la URL que se pidió (si hubo una redirección, ni siquiera llega: redirect "error").
    return fetch(`http://127.0.0.1:${puerto}${u.pathname}`, opciones).then((r) => ({
      status: r.status, redirected: r.redirected, url: u.toString(), headers: r.headers, body: r.body, arrayBuffer: () => r.arrayBuffer(),
    }));
  };
  return { srv, vistos, fetchFalso, puerto };
}

test("catálogo (Electron): solo del índice validado, con huella, sin redirecciones y con tope", async () => {
  const p = (id) => JSON.stringify({ formato: 1, id, categoria: "basicas", nombre: id });
  const h = (t) => crypto.createHash("sha256").update(t).digest("hex");
  const entrada = (id, cuerpo, extra = {}) => ({ id, categoria: "basicas", ruta: `plantillas/basicas/${id}.json`, sha256: h(cuerpo), tamano: Buffer.byteLength(cuerpo), ...extra });
  const buena = p("buena"), danada = p("danada"), grande = p("grande");
  const base = "/ana-app/ana-catalogo/main/";
  const { srv, vistos, fetchFalso } = await servidorCatalogo({
    [base + "plantillas/index.json"]: { cuerpo: "{}" },
    [base + "plantillas/basicas/buena.json"]: { cuerpo: buena },
    [base + "plantillas/basicas/danada.json"]: { cuerpo: danada.replace("danada\"}", "otra\"}") },
    [base + "plantillas/basicas/grande.json"]: { cuerpo: grande + " ".repeat(5000) },
    [base + "plantillas/basicas/vuelta.json"]: { redirige: "/robar" },
  });
  const llamadas = [];
  const procesador = {
    async conEntrada(script, accion, datos) {
      llamadas.push([script, accion, datos, accion === "instalar" ? fs.readFileSync(datos.archivo, "utf8") : null]);
      if (accion === "indice") return { ok: true, tipo: "plantillas", plantillas: [entrada("buena", buena), entrada("danada", danada), entrada("grande", grande), entrada("vuelta", buena), entrada("rara", buena, { ruta: "../app.json" })] };
      return { ok: true, tipo: "plantillas", id: datos.id };
    },
  };
  const cat = Cat.crear({ fetch: fetchFalso, procesador, appJson: { catalogo: { repo: "ana-app/ana-catalogo", tipos: { plantillas: { validador: "x" } } } } });
  try {
    assert.equal((await cat.descargar("plantillas", "buena")).codigo, "no_esta", "sin índice no baja nada");
    assert.equal(vistos.length, 0);
    const listado = await cat.listar("plantillas");
    assert.equal(listado.ok, true, JSON.stringify(listado));
    assert.equal((await cat.descargar("plantillas", "buena")).ok, true);
    assert.equal(llamadas.at(-1)[3], buena, "Python recibe lo bajado, con la huella del índice");
    assert.equal((await cat.descargar("plantillas", "danada")).codigo, "danado");
    assert.equal((await cat.descargar("plantillas", "grande")).codigo, "danado", "más grande que lo que dice el índice");
    assert.equal((await cat.descargar("plantillas", "vuelta")).codigo, "sin_conexion", "una redirección nunca se sigue");
    assert.ok(!vistos.includes("/robar"));
    assert.equal((await cat.descargar("plantillas", "rara")).codigo, "no_valido");
    assert.equal((await cat.descargar("plantillas", "inventada")).codigo, "no_esta");
    assert.equal((await cat.listar("otro")).codigo, "no_valido");
    assert.equal(llamadas.filter((x) => x[1] === "instalar").length, 1, "solo lo bueno llegó a instalarse");
    assert.equal(fs.readdirSync(os.tmpdir()).filter((x) => x.startsWith("pieza-catalogo-")).length, 0, "sin temporales");
  } finally { srv.close(); }
  assert.throws(() => Cat.leerConfig({ catalogo: { repo: "../x" } }));
  assert.throws(() => Cat.leerConfig({ catalogo: { repo: "a/b", tipos: { plantillas: { indice: "../index.json" } } } }));
});

test("catálogo (Electron): sin conexión, la última lista; plano, otra carpeta y mayúsculas; el error en «frase»", async () => {
  const llamadas = [];
  const procesador = { async conEntrada(s, accion, d) { llamadas.push(accion); return { ok: true, tipo: d.tipo, idiomas: [{ id: "pt-BR" }], fecha: "2026-10-30T10:00:00" }; } };
  const sinRed = async () => { throw new Error("sin red"); };
  const cat = Cat.crear({ fetch: sinRed, procesador, appJson: { catalogo: { repo: "ana-app/ana-catalogo", tipos: {
    idiomas: { validador: "x", carpeta: "traducciones", categoria: false, mayusculas: true }, plantillas: { validador: "x" } } } } });
  const r = await cat.listar("idiomas");
  assert.equal(r.ok, true);
  assert.equal(r.sin_conexion, true);
  assert.equal(r.frase, "No pude conectarme. Revisa tu conexión.");
  assert.deepEqual(llamadas, ["ultima"]);
  assert.equal((await cat.descargar("idiomas", "pt-BR")).codigo, "no_esta", "lo guardado se ve, pero no se descarga sin un índice nuevo");
  const t = cat.config.tipos.idiomas;
  assert.equal(t.indice, "traducciones/index.json");
  assert.ok(t.patron.test("traducciones/pt-BR.json") && !t.patron.test("traducciones/x/pt-BR.json") && !t.patron.test("idiomas/pt-BR.json"));
  assert.ok(!cat.config.tipos.plantillas.patron.test("plantillas/basicas/Mayus.json"));
  const vacio = Cat.crear({ fetch: sinRed, procesador: { async conEntrada() { return { ok: false, codigo: "sin_conexion" }; } },
    appJson: { catalogo: { repo: "a/b", tipos: { plantillas: { validador: "x" } } } } });
  const e = await vacio.listar("plantillas");
  assert.deepEqual([e.ok, e.codigo, e.frase, e.plantilla], [false, "sin_conexion", "No pude conectarme. Revisa tu conexión.", undefined]);
});

// ───────────── trabajos: el lector de progreso (Electron) ─────────────
const { lectorProgreso } = require(path.join(BASE, "piezas/trabajos/escritorio/progreso.js"));

test("trabajos: el lector pasa las líneas nuevas, salta las rotas y las enormes, y borra su archivo", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pieza-progreso-"));
  const recibidos = [];
  const l = lectorProgreso((e) => recibidos.push(...e), { prefijo: "Prueba!", cada: 20, dir });
  assert.match(path.basename(l.ruta), /^prueba-progreso-/);
  assert.equal(fs.statSync(l.ruta).mode & 0o777, 0o600);
  fs.appendFileSync(l.ruta, '{"t":"lee","ruta":"a.py"}\nno es json\n{"t":"est');
  await new Promise((ok) => setTimeout(ok, 80));
  fs.appendFileSync(l.ruta, 'ado"}\n' + "x".repeat(1024 * 1024 + 10) + "\n[1,2]\n" + '{"t":"fin"}\n');
  l.terminar();
  assert.deepEqual(recibidos, [{ t: "lee", ruta: "a.py" }, { t: "estado" }, { t: "fin" }]);
  assert.ok(!fs.existsSync(l.ruta));
  fs.rmSync(dir, { recursive: true });
});
