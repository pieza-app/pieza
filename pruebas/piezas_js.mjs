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
  assert.equal(s.pedidos[0], `https://api.github.com/repos/${REPO}/releases/latest`);
  // Sin empaquetar (desarrollo): nunca hay y no sale a internet.
  const dev = Act.crear({ app: { ...s.app, isPackaged: false }, net: s.net, repo: REPO, nombre: "Ana" });
  assert.equal((await dev.revisar()).hay, false);
  assert.equal(s.pedidos.length, 1);
  // Sin conexión
  const sin = Act.crear({ app: s.app, net: { fetch: async () => { throw new Error("x"); } }, repo: REPO, nombre: "Ana", plataforma: "linux", entorno: { APPIMAGE: appimage } });
  assert.deepEqual([(await sin.revisar()).hay, (await sin.revisar()).sinConexion], [false, true]);
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
