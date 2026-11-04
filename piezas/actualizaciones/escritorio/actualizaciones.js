// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.
// Pieza «actualizaciones» (Windows y Linux, Electron). Versiones nuevas dentro de la app (nunca una alerta del sistema):
// se revisa al abrir y cada 6 horas. Equivale a app/Sources/PiezaActualizaciones/Actualizaciones.swift.
// Windows: el instalador del Release (<Base>-Windows.exe, en silencio: cierra la app y la vuelve a abrir).
// Linux: el AppImage se reemplaza a sí mismo; la instalación de instalar.sh (~/.local/share/<Base>) se cambia entera con el tar.gz.
// Solo desde https://github.com/<repo>/releases/download/… y siempre verificado con su .sha256. Los datos de la persona viven
// fuera de la app: actualizar no borra nada.
//
// Nada de la app adentro: repo, nombre y archivos llegan como parámetros. Electron también (app, net), así la lógica se
// prueba en Node sin Electron.
//
// Firma (opcional, desde 0.4): con llaves públicas Ed25519 (`crear({llaves})` o app.json → actualizaciones.llaves con
// `usarApp(host.app)`), cada archivo vale solo si el Release trae su `.sig`: la firma de `<id>-actualizacion|<versión>|<sha256>`
// con la llave privada que vive en el Mac de quien mantiene la app (nunca en GitHub). Así alguien que tome la cuenta de GitHub no
// puede publicar una versión falsa ni volver a una vieja. Sin llaves, todo igual que antes.
//
//   const { crear } = require("./actualizaciones");
//   const act = crear({ app, net, repo: "ana-app/ana", nombre: "Ana" });
//   act.usarApp(host.app);                  // las llaves de app.json → actualizaciones.llaves (si las hay)
//   const r = await act.revisar();          // {hay, version, notas, sinConexion, texto, valores, desarrollo}
//   await act.instalar((avance) => ventana.llamar("actualizacionProgreso", avance));
"use strict";
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const child = require("child_process");

/** Los textos van en español y con marcadores: la interfaz los traduce entera con T(texto, valores). Nunca van a un guion. */
const TEXTOS = {
  version: "Versión {v}",
  bajando: "Descargando la versión nueva…",
  preparando: "Preparando la versión nueva…",
  instalando: "Instalando: {app} se cerrará y volverá a abrirse sola",
  errorBajar: "No pude descargar la versión nueva. Revisa tu conexión e intenta de nuevo.",
  errorArmar: "No pude preparar la versión nueva. {app} sigue igual que antes; intenta de nuevo más tarde.",
  sinDescarga: "No encontré la descarga de la versión nueva.",
  firma: "No pude comprobar que la versión nueva sea de {app}: le falta la firma o no es válida. {app} sigue igual que antes.",
};
const REPO = /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}$/;
const BASE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$/;
const VERSION = /^\d{1,6}(\.\d{1,6}){0,3}$/;
const MAX_HUELLA = 4096;
const ID = /^[a-z0-9][a-z0-9._-]{0,60}$/;
const MAX_LLAVES = 2;
/** Lo que va antes de los 32 bytes de una llave pública Ed25519 en formato SPKI (DER). */
const SPKI_ED25519 = Buffer.from("302a300506032b6570032100", "hex");

/** Texto entre comillas simples para bash: nada de lo que va adentro (rutas, URL) se interpreta como código. */
const comillas = (x) => "'" + String(x).replace(/'/g, "'\\''") + "'";

/** Solo se descarga desde los Releases de ESTE repo en github.com. GitHub después redirige a su almacenamiento
 *  (objects.githubusercontent.com / release-assets.githubusercontent.com): se sigue esa redirección solo por https y lo que
 *  llega se acepta únicamente si su SHA-256 es el del .sha256 publicado junto al archivo. */
function esDescargaNuestra(u, repo) {
  if (!REPO.test(String(repo || ""))) return false;
  try {
    const x = new URL(u);
    return x.protocol === "https:" && x.hostname === "github.com" && !x.port && !x.username && !x.password && !x.search && !x.hash
      && x.pathname.startsWith(`/${repo}/releases/download/`) && !x.pathname.includes("..") && !x.pathname.includes("%2");
  } catch { return false; }
}

/** «v1.10.0» → «1.10.0»; null si no es una versión de números. */
function limpiarVersion(v) {
  const s = String(v || "").trim().replace(/^v/, "");
  return VERSION.test(s) ? s : null;
}
/** ¿a es más nueva que b? («0.10.0» > «0.9.3»). Lo que no es versión nunca es más nuevo. */
function esMayor(a, b) {
  a = limpiarVersion(a); b = limpiarVersion(b) || "0";
  if (!a) return false;
  const x = a.split(".").map(Number), y = b.split(".").map(Number);
  for (let i = 0; i < Math.max(x.length, y.length); i++) { const d = (x[i] || 0) - (y[i] || 0); if (d) return d > 0; }
  return false;
}
/** El primer campo de un .sha256 («<64 hex>  archivo»), en minúsculas; null si no es una huella. */
function leerHuella(texto) {
  const h = String(texto || "").trim().split(/\s+/)[0].toLowerCase();
  return /^[0-9a-f]{64}$/.test(h) ? h : null;
}
/** Una llave pública Ed25519 (32 bytes en base64) como KeyObject; null si no es una. */
function llavePublica(b64) {
  const s = String(b64 || "").trim();
  if (!/^[A-Za-z0-9+/]{43}=$/.test(s)) return null;
  const raw = Buffer.from(s, "base64");
  if (raw.length !== 32) return null;
  try { return crypto.createPublicKey({ key: Buffer.concat([SPKI_ED25519, raw]), format: "der", type: "spki" }); } catch { return null; }
}
/** Lo que se firma: `<id>-actualizacion|<versión sin v>|<sha256 en minúsculas>` (lo mismo que herramientas/firmar de Pieza). */
const mensajeFirmado = (id, version, sha256) => `${id}-actualizacion|${version}|${String(sha256).toLowerCase()}`;
/** ¿La firma (base64, 64 bytes) es de alguna de las llaves? */
function firmaValida(firma, mensaje, llaves) {
  const s = String(firma || "").trim();
  if (!/^[A-Za-z0-9+/]{86}==$/.test(s)) return false;
  const f = Buffer.from(s, "base64");
  return (llaves || []).some((k) => {
    const pub = llavePublica(k);
    try { return !!pub && crypto.verify(null, Buffer.from(mensaje, "utf8"), pub, f); } catch { return false; }
  });
}
/** Revisa una descarga con firma. null si todo calza; si no, el código del error (una clave de TEXTOS): la huella publicada
 *  tiene que ser la del archivo, la versión firmada la del Release y más nueva que la instalada, y la firma de una de las llaves. */
function revisarDescarga({ huellaArchivo, textoHuella, firma, version, instalada, id, llaves }) {
  const esperada = leerHuella(textoHuella);
  if (!esperada || esperada !== String(huellaArchivo).toLowerCase()) return "errorBajar";
  if (!llaves || !llaves.length || !esMayor(version, instalada) || !firmaValida(firma, mensajeFirmado(id, limpiarVersion(version), esperada), llaves)) return "firma";
  return null;
}
/** Las llaves de una lista (hasta 2, todas válidas) o null si alguna no sirve. */
function llavesValidas(l) {
  return Array.isArray(l) && l.length <= MAX_LLAVES && l.every((k) => typeof k === "string" && llavePublica(k)) ? l.slice() : null;
}

/** Nombres fijos de los archivos de cada Release (los mismos que usan publicar.yml, instalar.sh e instalar.ps1). */
function archivosDe(base) {
  return { windows: `${base}-Windows.exe`, appimage: `${base}-Linux.AppImage`, tar: `${base}-Linux.tar.gz`, mac: `${base}-macOS.zip` };
}
/** Sin tildes ni espacios: «Matías Café» → «MatiasCafe». */
const baseDe = (nombre) => String(nombre).normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9._-]/g, "");

/** Cómo está instalada esta copia y qué archivo del Release la actualiza (null: desarrollo o puesta a mano, no se toca). */
function instalacion({ empaquetada, plataforma, appimage, execPath, home, base, ejecutable }) {
  if (!empaquetada) return null;
  const a = archivosDe(base);
  if (plataforma === "win32") return { tipo: "windows", archivo: a.windows };
  if (plataforma !== "linux") return null;
  if (appimage) return { tipo: "appimage", archivo: a.appimage, destino: appimage };
  const dir = path.dirname(execPath);
  if (dir === path.join(home, ".local", "share", base) && path.basename(execPath) === ejecutable) return { tipo: "tar", archivo: a.tar, destino: dir };
  return null;
}

/** El guion que cambia la carpeta de Linux cuando la app ya se cerró (deja la anterior si algo falla) y la vuelve a abrir.
 *  Todo lo variable va con comillas(); el pid es un número. */
function guionTar({ pid, destino, nueva, tmp, lanzador, ejecutable }) {
  const q = comillas, ant = destino + ".anterior";
  return `#!/bin/bash
while kill -0 ${Number(pid)} 2>/dev/null; do sleep 0.5; done
rm -rf ${q(ant)}; mv ${q(destino)} ${q(ant)} && mv ${q(nueva)} ${q(destino)} && rm -rf ${q(ant)} || { rm -rf ${q(destino)}; mv ${q(ant)} ${q(destino)}; }
rm -rf ${q(tmp)}
if [ -x ${q(lanzador)} ]; then exec ${q(lanzador)}; else exec ${q(path.join(destino, ejecutable))}; fi
`;
}

/** Baja `url` a `destino` calculando su SHA-256 al vuelo. La última dirección (después de las redirecciones de GitHub)
 *  tiene que seguir siendo https. */
async function descargar(net, url, destino, progreso = () => {}) {
  const r = await net.fetch(url);
  if (!r.ok || !r.body || (r.url && !String(r.url).startsWith("https://"))) throw new Error(`HTTP ${r.status}`);
  const total = Number(r.headers.get("content-length")) || 0;
  const salida = fs.createWriteStream(destino, { mode: 0o600 }), hash = crypto.createHash("sha256"), lector = r.body.getReader();
  let bytes = 0;
  try {
    for (;;) {
      const { done, value } = await lector.read();
      if (done) break;
      hash.update(value);
      bytes += value.length;
      if (!salida.write(value)) await new Promise((ok) => salida.once("drain", ok));
      if (total) progreso(bytes / total);
    }
  } finally { await new Promise((ok) => salida.end(ok)); }
  return hash.digest("hex");
}

/**
 * opciones: {app, net, repo, nombre, base?, ejecutable?, llaves?, id?} y, para probar, {home, plataforma, entorno, execPath, pid, spawn,
 * tmpdir, espera}. `base` = nombre de los archivos (sin tildes); `ejecutable` = el binario de Linux (por defecto base en minúsculas).
 */
function crear(opciones) {
  const o = opciones || {};
  const base = o.base || baseDe(o.nombre || "");
  if (!o.app || !o.net || !REPO.test(o.repo || "") || !o.nombre || !BASE.test(base)) {
    throw new Error("actualizaciones: faltan app, net, repo («dueño/repo»), nombre o una base válida.");
  }
  const ejecutable = o.ejecutable || base.toLowerCase();
  if (!BASE.test(ejecutable)) throw new Error("actualizaciones: «ejecutable» no es un nombre de archivo simple.");
  // La firma: llaves públicas (hasta 2) y el id del mensaje firmado (el de app.json, o la base en minúsculas).
  let llaves = o.llaves === undefined ? [] : llavesValidas(o.llaves);
  if (!llaves) throw new Error("actualizaciones: «llaves» es una lista de hasta 2 llaves públicas Ed25519 (32 bytes en base64).");
  let id = o.id || base.toLowerCase();
  if (!ID.test(id)) throw new Error("actualizaciones: «id» no es un id simple.");
  let mala = false; // app.json traía llaves que no sirven: sin actualizaciones (mejor que sin revisar la firma)
  const home = o.home || os.homedir(), plataforma = o.plataforma || process.platform, entorno = o.entorno || process.env;
  const spawn = o.spawn || child.spawn, espera = o.espera ?? 1500, pid = o.pid ?? process.pid;
  const valores = { app: o.nombre };
  const aviso = (paso, codigo, extra = {}) => ({ paso, codigo, texto: TEXTOS[codigo], valores, total: 3, ...extra });
  const inst = () => instalacion({ empaquetada: o.app.isPackaged, plataforma, appimage: entorno.APPIMAGE, execPath: o.execPath || process.execPath, home, base, ejecutable });

  const act = {
    disponible: { hay: false },
    _urls: null,
    get version() { return o.app.getVersion(); },
    get firmadas() { return llaves.length > 0; },
    instalacion: inst,

    /** Toma `id` y `actualizaciones.llaves` de app.json (el objeto, p. ej. `host.app`), salvo lo que se dio en `crear`. Si
     *  `actualizaciones` está mal escrita, ya no hay actualizaciones (y lo dice en la consola). */
    usarApp(a) {
      if (!a || typeof a !== "object") return act;
      if (!o.id && typeof a.id === "string" && ID.test(a.id)) id = a.id;
      if (o.llaves === undefined && a.actualizaciones !== undefined) {
        const sec = a.actualizaciones;
        const l = sec && typeof sec === "object" && !Array.isArray(sec) ? (sec.llaves === undefined ? [] : llavesValidas(sec.llaves)) : null;
        if (l) llaves = l;
        else { mala = true; console.error("actualizaciones: app.json → actualizaciones.llaves no son llaves Ed25519 válidas; no busco versiones nuevas."); }
      }
      return act;
    },

    /** {hay, version, notas, sinConexion, texto, valores}. Sin empaquetar (desarrollo) o puesta a mano, nunca hay. */
    async revisar() {
      const i = inst();
      if (!i || mala) return act._fin(false);
      let r;
      try {
        r = await o.net.fetch(`https://api.github.com/repos/${o.repo}/releases/latest`, {
          headers: { Accept: "application/vnd.github+json", "User-Agent": `${base}/${act.version}` } });
      } catch { return act._fin(false, true); }
      if (r.status === 404) return act._fin(false); // aún no hay versiones
      if (r.status !== 200) return act._fin(false, true);
      const d = await r.json().catch(() => ({}));
      const tag = limpiarVersion(d && d.tag_name);
      const assets = Array.isArray(d && d.assets) ? d.assets : [];
      const url = (n) => assets.find((a) => a && a.name === n)?.browser_download_url;
      const archivo = url(i.archivo), huella = url(i.archivo + ".sha256"), firma = url(i.archivo + ".sig");
      if (!tag || !esMayor(tag, act.version) || !esDescargaNuestra(archivo, o.repo) || !esDescargaNuestra(huella, o.repo)) return act._fin(false);
      act._urls = { archivo, huella, firma: esDescargaNuestra(firma, o.repo) ? firma : null, version: tag };
      const notas = String(d.body || "").split("\n").slice(0, 4).join("\n").slice(0, 1000);
      return act._fin(true, false, tag, notas);
    },
    _fin(hay, sinConexion = false, version = "", notas = "") {
      // `disponible` (lo que la app manda en su estado) tiene la misma forma que la respuesta: la interfaz usa una sola función.
      act.disponible = { hay, version: hay ? version : "", notas: hay ? notas : "", texto: hay && version ? TEXTOS.version : "", valores: { v: hay ? version : "" }, desarrollo: false };
      return { ...act.disponible, sinConexion };
    },
    /** Un aviso de avance con la forma estándar ({paso, codigo, texto, valores, total}). `codigo` es una clave de TEXTOS. */
    aviso: (paso, codigo) => aviso(paso, TEXTOS[codigo] ? codigo : "errorArmar"),

    /** Descarga, verifica e instala. avisar({paso: "1"|"2"|"3"|"error", codigo, texto, valores, total, pct?}). Al final la
     *  app se cierra y se vuelve a abrir. Quien llama se asegura antes de que no haya nada guardándose. */
    async instalar(avisar) {
      const i = inst();
      if (!i || mala || !act._urls || !esDescargaNuestra(act._urls.archivo, o.repo) || !esDescargaNuestra(act._urls.huella, o.repo)) {
        return avisar(aviso("error", "sinDescarga"));
      }
      // Con firma: sin .sig en el Release, ni se baja.
      if (llaves.length && !act._urls.firma) return avisar(aviso("error", "firma"));
      const tmp = fs.mkdtempSync(path.join(o.tmpdir || os.tmpdir(), `${ejecutable}-actualizacion-`));
      const archivo = path.join(tmp, i.archivo);
      const borrar = () => fs.rmSync(tmp, { recursive: true, force: true });
      avisar(aviso("1", "bajando"));
      let huella, textoHuella, firma = null;
      const bajarTexto = async (u) => {
        const r = await o.net.fetch(u);
        if (!r.ok || (r.url && !String(r.url).startsWith("https://"))) throw new Error("texto");
        return (await r.text()).slice(0, MAX_HUELLA);
      };
      try {
        let ultimo = 0;
        huella = await descargar(o.net, act._urls.archivo, archivo, (p) => {
          if (Date.now() - ultimo > 500) { ultimo = Date.now(); avisar(aviso("1", "bajando", { pct: Math.round(p * 100) })); }
        });
        textoHuella = await bajarTexto(act._urls.huella);
        if (llaves.length) firma = await bajarTexto(act._urls.firma);
      } catch { borrar(); return avisar(aviso("error", "errorBajar")); }
      const esperada = leerHuella(textoHuella);
      if (!esperada || huella !== esperada) { borrar(); return avisar(aviso("error", "errorBajar")); }
      if (llaves.length) {
        const codigo = revisarDescarga({ huellaArchivo: huella, textoHuella, firma, version: act._urls.version, instalada: act.version, id, llaves });
        if (codigo) { borrar(); return avisar(aviso("error", codigo)); }
      }
      avisar(aviso("2", "preparando"));
      const listo = () => avisar(aviso("3", "instalando"));
      try {
        if (i.tipo === "windows") {
          listo();
          // El instalador (por usuario, /S) cierra la app, reemplaza sus archivos y la vuelve a abrir.
          spawn(archivo, ["/S"], { detached: true, stdio: "ignore", windowsHide: true }).unref();
          setTimeout(() => o.app.exit(0), espera);
        } else if (i.tipo === "appimage") {
          const nuevo = i.destino + ".nueva";
          fs.copyFileSync(archivo, nuevo);
          fs.chmodSync(nuevo, 0o755);
          fs.renameSync(nuevo, i.destino); // en Linux se puede reemplazar el archivo aunque esté abierto
          borrar();
          listo();
          setTimeout(() => { o.app.relaunch({ execPath: i.destino, args: process.argv.slice(1) }); o.app.exit(0); }, espera);
        } else {
          const nueva = path.join(tmp, "nueva");
          fs.mkdirSync(nueva);
          const tar = spawn("tar", ["-xzf", archivo, "-C", nueva, "--strip-components=1", "--no-same-owner"], { stdio: "ignore" });
          const ok = await new Promise((r) => { tar.on("error", () => r(false)); tar.on("close", (c) => r(c === 0)); });
          if (!ok || !fs.existsSync(path.join(nueva, ejecutable))) throw new Error("tar");
          const guion = path.join(tmp, "actualizar.sh");
          fs.writeFileSync(guion, guionTar({ pid, destino: i.destino, nueva, tmp, lanzador: path.join(home, ".local", "bin", ejecutable), ejecutable }), { mode: 0o700 });
          spawn("/bin/bash", [guion], { detached: true, stdio: "ignore" }).unref();
          listo();
          setTimeout(() => o.app.exit(0), espera);
        }
      } catch {
        borrar();
        avisar(aviso("error", "errorArmar"));
      }
    },

    /** Al abrir y cada 6 horas; `avisar` solo se llama si hay algo nuevo (no interrumpe la bienvenida ni un diálogo). */
    revisarCadaRato(avisar, cada = 6 * 3600 * 1000) {
      const una = () => act.revisar().then((r) => { if (r.hay) avisar(r); }).catch(() => {});
      una();
      const t = setInterval(una, cada);
      t.unref?.();
      return t;
    },
  };
  return act;
}

module.exports = { crear, TEXTOS, comillas, esDescargaNuestra, esMayor, limpiarVersion, leerHuella, archivosDe, baseDe, instalacion, guionTar,
  llavePublica, mensajeFirmado, firmaValida, revisarDescarga };
