// Pruebas de la pieza «host-escritorio» en Node, sin pantalla: la lógica del enchufe (validar acciones y datos, config, idioma,
// rutas), el procesador con Python de verdad (límite de tiempo que corta también a los hijos, entorno sin <ID>_*, secreto por la
// entrada estándar, lo de la persona nunca como argumento) y el host con un Electron falso (el puente solo atiende al marco
// principal con el origen propio, las acciones declaradas responden con su eco, la apariencia sigue a config.tema).
// Electron de verdad: pruebas/host_escritorio_electron.mjs (con xvfb-run, si hay Electron instalado aparte).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const BASE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIR = path.join(BASE, "piezas/host-escritorio/escritorio");
const E = require(path.join(DIR, "enchufe.js"));
const { crearProcesador, crearFila } = require(path.join(DIR, "procesador.js"));
const { crearHost, nombreArchivo, servirArchivo } = require(path.join(DIR, "host.js"));
const PYTHON = process.env.PYTHON || "python3";

const SCRIPT = `
import json, os, subprocess, sys, time
args = sys.argv[1:]
salida, accion = args[-1], args[0]
entrada = json.load(open(args[-2], encoding="utf-8")) if len(args) >= 3 and args[-2].endswith(".json") else {}
if accion == "dormir":
    hijo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    open(os.path.join(os.environ["ANA_DATOS"], "hijo.pid"), "w").write(str(hijo.pid))
    time.sleep(60)
if accion == "roto":
    sys.exit(3)
if accion == "latir":
    # Late como la pieza «trabajos» (toca <ID>_LATIDO) más tiempo del que aguantaría sin latir.
    for _ in range(int(entrada.get("vueltas", 12))):
        open(os.environ["ANA_LATIDO"], "a").close(); os.utime(os.environ["ANA_LATIDO"], None); time.sleep(0.2)
if accion == "colgado":
    time.sleep(60)
r = {"ok": True, "accion": accion, "entrada": entrada, "argv": args[:-1], "cwd": os.getcwd(),
     "env": sorted(k for k in os.environ if k.startswith("ANA_")), "ajena": os.environ.get("ANA_AJENA"),
     "stdin": sys.stdin.read() if accion == "secreto" else None}
if accion == "secreto":
    print("CREDENCIAL {}")
if accion == "leer":
    r["texto"] = "del disco"
if accion == "falla":
    r = {"ok": False, "error": "no pude"}
r["latido"] = os.environ.get("ANA_LATIDO") is not None
json.dump(r, open(salida, "w", encoding="utf-8"))
`;

const ACCIONES = {
  formato: 1,
  acciones: {
    probarIA: { script: "eco.py", args: ["probar"], entrada: "archivo", datos: { ia: { tipo: "enum", valores: ["claude", "codex", "gemini"] } }, responde: "iaProbada", eco: ["ia"], limite: 30 },
    guardar: { script: "eco.py", args: ["guardar"], entrada: "archivo", datos: { ruta: { tipo: "rutaRelativa", extensiones: [".md"], requerido: true }, texto: { tipo: "texto", max: 50 } },
      inyectar: { carpeta: "carpetaActual" }, responde: "guardado", eco: ["ruta"], cola: "escritura", limite: 30 },
    nivel: { script: "eco.py", args: ["nivel", "$n"], datos: { n: { tipo: "entero", min: 1, max: 3 } }, responde: "nivelListo", limite: 30 },
    lento: { script: "eco.py", args: ["dormir"], responde: "lentoListo", limite: 1 },
    malo: { script: "eco.py", args: ["$texto"], entrada: "archivo", datos: { texto: { tipo: "texto", max: 10 } }, responde: "x", limite: 30 },
    sinScript: { script: "noexiste.py", responde: "x", limite: 30 },
    proyecto: { script: "eco.py", args: ["$orden"], entrada: "archivo", datos: { orden: { tipo: "enum", valores: ["abrir", "latir", "colgado"] }, n: { tipo: "entero", max: 3 }, vueltas: { tipo: "entero" } },
      responde: "proyectoRespuesta", eco: ["orden", "n"], limite: { segun: "orden", valores: { latir: "trabajo", colgado: "trabajo" }, otro: 1 } },
    leerArchivo: { script: "eco.py", args: ["leer"], entrada: "archivo", datos: { ruta: { tipo: "rutaRelativa", extensiones: [".md"], requerido: true } },
      inyectar: { carpeta: "carpetaActual" }, responde: "archivoAbierto", eco: ["ruta"], vigilar: "lee", limite: 30 },
    escribirArchivo: { script: "eco.py", args: ["$modo"], entrada: "archivo", datos: { modo: { tipo: "enum", valores: ["guardar", "falla"] },
      ruta: { tipo: "rutaRelativa", extensiones: [".md"], requerido: true }, texto: { tipo: "texto", max: 6 * 1024 * 1024 } },
      inyectar: { carpeta: "carpetaActual" }, responde: "archivoGuardado", eco: ["ruta"], vigilar: "escribe", cola: "escritura", maximo: 7 * 1024 * 1024, limite: 30 },
  },
};

function crearApp({ acciones = ACCIONES, config = { idioma_ui: ["es", "en"], tema: ["sistema", "claro", "oscuro"], bienvenida: "bool", carpeta: { tipo: "texto", max: 400, interfaz: false } } } = {}) {
  const raiz = fs.mkdtempSync(path.join(os.tmpdir(), "host-escritorio-"));
  fs.mkdirSync(path.join(raiz, "bin"));
  fs.mkdirSync(path.join(raiz, "ui", "idiomas"), { recursive: true });
  fs.writeFileSync(path.join(raiz, "app.json"), JSON.stringify({ id: "ana", nombre: "Ana", datos: "sistema", config }));
  fs.writeFileSync(path.join(raiz, "bin", "eco.py"), SCRIPT);
  fs.writeFileSync(path.join(raiz, "ui", "index.html"), "<!doctype html><title>Ana</title>");
  fs.writeFileSync(path.join(raiz, "ui", "idiomas", "en.json"), JSON.stringify({ codigo: "en", textos: { "Salir de {app}": "Quit {app}", "Archivo": "File" } }));
  if (acciones) fs.writeFileSync(path.join(raiz, "acciones.json"), JSON.stringify(acciones));
  const datos = path.join(raiz, "datos");
  return { raiz, datos };
}

// ───────────── Enchufe ─────────────
test("enchufe: una acción con texto de la persona como argumento no se carga", () => {
  const { raiz } = crearApp();
  const { acciones, errores } = E.cargarAcciones(raiz);
  assert.ok(!acciones.malo && errores.some((e) => e.includes("$texto")));
  assert.ok(!acciones.sinScript && errores.some((e) => e.includes("noexiste.py")));
  assert.ok(acciones.probarIA && acciones.guardar && acciones.nivel);
  assert.ok(E.erroresAccion("x", { script: "a.py", limite: 0 }).some((e) => e.includes("limite")));
  assert.ok(E.erroresAccion("x", { script: "../a.py", limite: 3 }).some((e) => e.includes("script")));
  assert.ok(E.erroresAccion("x", { script: "a.py", limite: 3, datos: { t: { tipo: "texto", max: 3 } } }).some((e) => e.includes("entrada")));
  assert.ok(E.erroresAccion("x", { script: "a.py", limite: 3, entrada: "archivo", datos: { carpeta: { tipo: "texto", max: 9 } }, inyectar: { carpeta: "carpetaActual" } }).some((e) => e.includes("lo pone el host")));
  assert.ok(E.erroresAccion("x", { script: "a.py", limite: 3, args: ["a b"] }).some((e) => e.includes("literal")));
  assert.deepEqual(E.erroresAccion("x", { script: "a.py", limite: 3, args: ["$n"], datos: { n: { tipo: "entero" } } }), []);
});

test("enchufe: los datos se validan por tipo y lo no declarado no pasa", () => {
  const def = { args: [], datos: {
    t: { tipo: "texto", max: 5 }, r: { tipo: "texto", max: 3, recortar: true }, e: { tipo: "enum", valores: ["a", "b"] }, b: { tipo: "bool" },
    n: { tipo: "entero", min: 0, max: 9 }, ruta: { tipo: "rutaRelativa", extensiones: [".md"] }, img: { tipo: "base64", maxBytes: 4 },
    l: { tipo: "lista", max: 2, de: { tipo: "enum", valores: ["x", "y"] } } } };
  const ok = E.validarDatos(def, { t: "hola", r: "largo", e: "a", b: true, n: 3, ruta: "a/b.md", img: "AAAA", l: ["x"], otro: 1, __proto__: { x: 1 } });
  assert.ok(ok.ok);
  assert.deepEqual(ok.entrada, { t: "hola", r: "lar", e: "a", b: true, n: 3, ruta: "a/b.md", img: "AAAA", l: ["x"] });
  for (const malo of [{ t: "demasiado" }, { e: "c" }, { b: "si" }, { n: 10 }, { n: 1.5 }, { ruta: "../a.md" }, { ruta: "/a.md" }, { ruta: "a.txt" },
    { ruta: "C:\\a.md" }, { img: "AAAAAAAA" }, { img: "no es base64!" }, { l: ["x", "y", "x"] }, { l: ["z"] }]) {
    assert.equal(E.validarDatos(def, malo).ok, false, JSON.stringify(malo));
  }
  // Un campo de args es obligatorio; «*»: "pasar" deja pasar lo demás (sin lo que inyecta el host).
  assert.equal(E.validarDatos({ args: ["$n"], datos: { n: { tipo: "entero" } } }, {}).codigo, "falta");
  const pasa = E.validarDatos({ args: [], datos: { "*": "pasar" }, inyectar: { carpeta: "carpetaActual" } }, { a: [1], carpeta: "/etc", "con espacio": 1 });
  assert.deepEqual(pasa.entrada, { a: [1] });
  assert.deepEqual(E.armarArgs({ args: ["probar", "$n"] }, { n: 2 }), ["probar", "2"]);
});

test("enchufe: config solo con las claves de app.json, sin cambiar las de la app desde la interfaz", () => {
  const { raiz, datos } = crearApp();
  const a = E.leerApp(raiz);
  const config = E.crearConfig({ ruta: path.join(datos, "config.json"), reglas: a.config, preparar: () => E.prepararCarpeta(datos) });
  config.guardar({ idioma_ui: "en", tema: "morado", bienvenida: true, carpeta: "/etc", otra: 1, __proto__: { x: 1 } });
  assert.deepEqual(config.leer(), { idioma_ui: "en", bienvenida: true });
  config.guardar({ carpeta: "/srv/ana" }, { desdeInterfaz: false });
  assert.equal(config.leer().carpeta, "/srv/ana");
  if (process.platform !== "win32") {
    assert.equal(fs.statSync(path.join(datos, "config.json")).mode & 0o777, 0o600);
    assert.equal(fs.statSync(datos).mode & 0o777, 0o700);
  }
  const idioma = E.crearIdioma({ config, recursos: raiz, sistema: "es-CL" });
  assert.equal(idioma.codigo, "en");
  assert.equal(idioma.f("Salir de {app}", { app: "Ana" }), "Quit Ana");
  assert.ok(idioma.elegido);
  assert.equal(E.valida({ tipo: "texto", patron: "auto|[a-z]{2}" }, "es"), true);
  assert.equal(E.valida({ tipo: "texto", patron: "auto|[a-z]{2}" }, "es; rm"), false);
  assert.throws(() => E.leerApp(os.tmpdir() + "/no-existe"));
});

test("enchufe: dentro() es la misma guarda que nucleo.ruta_en (también con enlaces)", () => {
  const { raiz } = crearApp();
  const base = path.join(raiz, "carpeta");
  fs.mkdirSync(path.join(base, "sub"), { recursive: true });
  fs.writeFileSync(path.join(base, "sub", "a.md"), "x");
  assert.equal(E.dentro(base, "sub/a.md"), fs.realpathSync(path.join(base, "sub", "a.md")));
  assert.ok(E.dentro(base, "nuevo.md", { extensiones: [".md"] }));
  for (const r of ["../app.json", "/etc/passwd", "sub/../../x.md", "", "a\0.md", "C:/x.md", "sub//a.md"]) assert.equal(E.dentro(base, r), null, r);
  assert.equal(E.dentro(base, "sub/a.txt", { extensiones: [".md"] }), null);
  if (process.platform !== "win32") {
    fs.symlinkSync(raiz, path.join(base, "fuera"));
    assert.equal(E.dentro(base, "fuera/app.json"), null);
  }
  assert.equal(nombreArchivo("../../x", "svg"), "archivo..-..-x.svg");
  assert.equal(nombreArchivo(".oculto", "md"), "archivo.oculto.md");
});

// ───────────── Procesador ─────────────
function procesadorDe(raiz, datos, extra = {}) {
  fs.mkdirSync(datos, { recursive: true });
  return crearProcesador({ python: PYTHON, recursos: raiz, id: "ana", datos, registro: () => {}, ...extra });
}

test("procesador: lo de la persona va en un archivo, nunca como argumento; sin variables ANA_* de afuera", async () => {
  const { raiz, datos } = crearApp();
  process.env.ANA_AJENA = "de otro programa";
  try {
    const p = procesadorDe(raiz, datos);
    const r = await p.conEntrada("eco.py", "guardar", { texto: "--borrar-todo; rm -rf ~" });
    assert.equal(r.ok, true);
    assert.equal(r.entrada.texto, "--borrar-todo; rm -rf ~");
    assert.ok(!r.argv.some((x) => x.includes("borrar")));
    assert.equal(r.ajena, null);
    assert.deepEqual(r.env, ["ANA_DATOS", "ANA_RECURSOS"]);
    // La entrada y la salida vivían en una carpeta temporal propia que ya no existe.
    assert.ok(!fs.existsSync(r.cwd));
    assert.equal(p.enCurso, 0);
  } finally { delete process.env.ANA_AJENA; }
});

test("procesador: el secreto llega por la entrada estándar y la salida estándar vuelve", async () => {
  const { raiz, datos } = crearApp();
  const p = procesadorDe(raiz, datos);
  const r = await p.correr("eco.py", ["secreto"], { secreto: "llave-123" });
  assert.equal(r.respuesta.stdin, "llave-123");
  assert.ok(!r.respuesta.argv.includes("llave-123"));
  assert.match(r.salidaEstandar, /^CREDENCIAL \{\}/);
});

test("procesador: el límite de tiempo corta el script y lo que lanzó", { skip: process.platform === "win32" }, async () => {
  const { raiz, datos } = crearApp();
  const p = procesadorDe(raiz, datos, { gracia: 1 });
  const antes = Date.now();
  const r = await p.correrJSON("eco.py", ["dormir"], { limite: 1 });
  assert.equal(r.ok, false);
  assert.equal(r.codigo, "limite");
  assert.deepEqual(r.valores, { s: 1 });
  assert.ok(Date.now() - antes < 6000);
  const pid = Number(fs.readFileSync(path.join(datos, "hijo.pid"), "utf8"));
  await new Promise((ok) => setTimeout(ok, 300));
  // Muerto (o zombi esperando a que lo recojan): nunca durmiendo.
  const vivo = () => { try { return !/^\d+ \(.*\) Z/.test(fs.readFileSync(`/proc/${pid}/stat`, "utf8")); } catch { try { process.kill(pid, 0); return !fs.existsSync("/proc"); } catch { return false; } } };
  assert.equal(vivo(), false, "el hijo del script siguió vivo");
});

test("procesador: un script que falla o que no existe responde ok: false", async () => {
  const { raiz, datos } = crearApp();
  const p = procesadorDe(raiz, datos);
  assert.equal((await p.correrJSON("eco.py", ["roto"])).codigo, "fallo");
  assert.equal((await p.correrJSON("../eco.py", [])).ok, false);
  assert.equal((await p.correrJSON("otro.py", [])).ok, false);
  assert.equal((await p.correrJSON("eco.py", ["a\0b"])).ok, false);
});

test("procesador: la fila corre de a una y en orden", async () => {
  const fila = crearFila();
  const orden = [];
  const tarea = (n, ms) => () => new Promise((ok) => setTimeout(() => { orden.push(n); ok(n); }, ms));
  await Promise.all([fila.agregar(tarea(1, 40)), fila.agregar(tarea(2, 1)), fila.agregar(() => { throw new Error("x"); }).catch(() => {}), fila.agregar(tarea(3, 1))]);
  assert.deepEqual(orden, [1, 2, 3]);
  assert.equal(fila.pendientes, 0);
});

// ───────────── Host con un Electron falso ─────────────
function electronFalso() {
  const llamadas = [];
  const ipc = {};
  const ev = (o) => { o._on = {}; o.on = (n, f) => { o._on[n] = f; return o; }; o.once = o.on; return o; };
  class BrowserWindow {
    constructor(opciones) {
      this.opciones = opciones; ev(this);
      this.webContents = ev({ mainFrame: { url: "ana://ui/index.html" }, setWindowOpenHandler: (f) => { this.webContents.abrir = f; },
        executeJavaScript: (js) => { llamadas.push(js); return Promise.resolve(); }, getURL: () => "ana://ui/index.html" });
      this.webContents.mainFrame.url = "ana://ui/index.html";
      e.ventanas.push(this);
    }
    loadURL(u) { this.url = u; }
    isDestroyed() { return false; } isMinimized() { return false; }
    show() {} focus() {} hide() { this.escondida = true; } restore() {}
    setBackgroundColor(c) { this.fondo = c; } getNormalBounds() { return { x: 1, y: 2, width: 800, height: 600 }; }
  }
  const e = {
    ventanas: [], llamadas, abiertos: [], menus: [], protocolos: {},
    app: ev({ isPackaged: false, getVersion: () => "1.2.3", getLocale: () => "es-CL", requestSingleInstanceLock: () => true, setName() {}, setPath() {},
      whenReady: () => Promise.resolve(), exit() { e.salio = true; }, quit() {}, getPath: () => os.tmpdir(), setAppUserModelId() {} }),
    BrowserWindow,
    Menu: { buildFromTemplate: (p) => p, setApplicationMenu: (m) => e.menus.push(m) },
    clipboard: { writeText: (t) => { e.copiado = t; } },
    dialog: {},
    ipcMain: { on: (canal, f) => { ipc[canal] = f; } },
    ipc,
    nativeTheme: { themeSource: "system", get shouldUseDarkColors() { return this.themeSource === "dark"; } },
    net: { fetch: (u) => Promise.resolve(new Response("archivo " + u)) },
    protocol: { registerSchemesAsPrivileged: (l) => { e.esquemas = l; }, handle: (n, f) => { e.protocolos[n] = f; } },
    session: { defaultSession: { setPermissionRequestHandler: (f) => { e.pedirPermiso = f; }, setPermissionCheckHandler: (f) => { e.revisarPermiso = f; } } },
    shell: { openExternal: (u) => e.abiertos.push(u), trashItem: async () => {} },
  };
  return e;
}

async function hostListo(extra = {}) {
  const { raiz, datos } = crearApp();
  const electron = electronFalso();
  const host = crearHost({ electron, recursos: raiz, datos, python: PYTHON, estadoScript: null, ...extra });
  host.iniciar();
  await new Promise((ok) => setImmediate(ok));
  const v = electron.ventanas[0];
  const enviar = (accion, datosMsg, cambio = {}) => electron.ipc.ana({ sender: v.webContents, senderFrame: v.webContents.mainFrame, ...cambio }, { accion, datos: datosMsg });
  await enviar("listo", {});
  electron.llamadas.length = 0;
  return { host, electron, v, enviar, raiz, datos };
}
const llamadasA = (electron, f) => electron.llamadas.filter((js) => js.includes(`window.Ana.${f}(`)).map((js) => JSON.parse(js.slice(js.indexOf(`.${f}(`) + f.length + 2, -1)));

test("host: la ventana va con sandbox, sin Node, y solo navega dentro de ana://ui/", async () => {
  const { electron, v } = await hostListo();
  const w = v.opciones.webPreferences;
  assert.equal(w.sandbox, true); assert.equal(w.contextIsolation, true); assert.equal(w.nodeIntegration, false); assert.equal(w.webviewTag, false);
  assert.deepEqual(w.additionalArguments, ["--pieza-host=ana"]);
  assert.equal(v.url, "ana://ui/index.html");
  assert.equal(electron.esquemas[0].scheme, "ana");
  let cancelada = false;
  v.webContents._on["will-navigate"]({ preventDefault: () => { cancelada = true; } }, "https://ejemplo.org/");
  assert.ok(cancelada && electron.abiertos.includes("https://ejemplo.org/"));
  cancelada = false;
  v.webContents._on["will-navigate"]({ preventDefault: () => { cancelada = true; } }, "file:///etc/passwd");
  assert.ok(cancelada && !electron.abiertos.includes("file:///etc/passwd"));
  assert.deepEqual(v.webContents.abrir({ url: "http://ejemplo.org" }), { action: "deny" });
  assert.ok(!electron.abiertos.includes("http://ejemplo.org"));
  // Permisos: todo negado salvo lo que la app permita.
  let r; electron.pedirPermiso(v.webContents, "media", (x) => { r = x; }, {});
  assert.equal(r, false);
});

test("host: el puente ignora otra ventana, un iframe u otro origen", async () => {
  const { electron, v, enviar } = await hostListo();
  const ajena = { url: "https://malo.example/" };
  await enviar("copiar", { texto: "hola" }, { senderFrame: { url: "ana://ui/index.html" } });          // un iframe (otro marco)
  await enviar("copiar", { texto: "hola" }, { sender: { mainFrame: ajena }, senderFrame: ajena });   // otra ventana
  v.webContents.mainFrame.url = "https://malo.example/";                                              // navegó afuera
  await enviar("copiar", { texto: "hola" });
  v.webContents.mainFrame.url = "ana://ui/index.html";
  assert.equal(electron.copiado, undefined);
  await enviar("copiar", { texto: "hola" });
  assert.equal(electron.copiado, "hola");
  assert.deepEqual(llamadasA(electron, "copiado"), [{ ok: true }]);
  await enviar("__proto__", {}); await enviar("constructor", {});
});

test("host: una acción declarada valida, corre el script y responde con su eco", async () => {
  const { electron, enviar } = await hostListo();
  await enviar("probarIA", { ia: "claude", extra: "no pasa" });
  const [r] = llamadasA(electron, "iaProbada");
  assert.equal(r.ok, true); assert.equal(r.ia, "claude"); assert.deepEqual(r.entrada, { ia: "claude" }); assert.deepEqual(r.argv.slice(0, 1), ["probar"]);
  await enviar("probarIA", { ia: "otra" });
  const [, malo] = llamadasA(electron, "iaProbada");
  assert.equal(malo.ok, false); assert.equal(malo.codigo, "datos"); assert.equal(malo.campo, "ia");
  await enviar("nivel", { n: 2 });
  assert.deepEqual(llamadasA(electron, "nivelListo")[0].argv, ["nivel", "2"]);
  await enviar("nivel", { n: "2; rm" });
  assert.equal(llamadasA(electron, "nivelListo")[1].codigo, "datos");
  await enviar("malo", { texto: "x" });                      // no se cargó: no responde nada
  assert.equal(llamadasA(electron, "x").length, 0);
});

test("host: lo que inyecta el host nunca lo pone la interfaz; sin valor, no corre", async () => {
  let carpeta = null;
  const { electron, enviar } = await hostListo({ inyectar: { carpetaActual: () => carpeta } });
  await enviar("guardar", { ruta: "a.md", texto: "hola", carpeta: "/etc" });
  assert.equal(llamadasA(electron, "guardado")[0].codigo, "falta");
  carpeta = "/srv/ana/docs";
  await enviar("guardar", { ruta: "a.md", texto: "hola", carpeta: "/etc" });
  const r = llamadasA(electron, "guardado")[1];
  assert.equal(r.entrada.carpeta, "/srv/ana/docs"); assert.equal(r.ruta, "a.md");
  await enviar("guardar", { ruta: "../a.md", texto: "hola" });
  assert.equal(llamadasA(electron, "guardado")[2].codigo, "datos");
});

test("host: el límite de una acción declarada responde codigo «limite»", { skip: process.platform === "win32" }, async () => {
  const { electron, enviar } = await hostListo();
  await enviar("lento", {});
  assert.equal(llamadasA(electron, "lentoListo")[0].codigo, "limite");
});

test("host: la app registra sus acciones y puede reemplazar una de a poco", async () => {
  const { host, electron, enviar } = await hostListo();
  const vistos = [];
  host.acciones.registrar("grabar", (d, h) => { vistos.push(d); h.llamar("grabando", { ok: true }); });
  host.acciones.registrar("probarIA", (d, h) => h.llamar("iaProbada", { propia: true }));
  await enviar("grabar", { modo: "pantalla" });
  await enviar("probarIA", { ia: "claude" });
  assert.deepEqual(vistos, [{ modo: "pantalla" }]);
  assert.deepEqual(llamadasA(electron, "iaProbada"), [{ propia: true }]);
  assert.throws(() => host.acciones.registrar("no vale", () => {}));
  assert.ok(host.acciones.todas().includes("grabar") && host.acciones.todas().includes("listo"));
  assert.equal(host.llamar("alert('x');//", {}), false);
});

test("host: config cambia la apariencia nativa y rearma el menú en el idioma nuevo", async () => {
  const { electron, enviar, v, host } = await hostListo({ ventana: { fondo: { claro: "#fff", oscuro: "#000" } }, sitio: "https://ana.example/" });
  let tareas = 0;
  await enviar("config", { tema: "oscuro" });
  assert.equal(electron.nativeTheme.themeSource, "dark"); assert.equal(v.fondo, "#000");
  await enviar("config", { tema: "claro" });
  assert.equal(electron.nativeTheme.themeSource, "light");
  await enviar("config", { tema: "sistema", idioma_ui: "en" });
  assert.equal(electron.nativeTheme.themeSource, "system");
  const menu = electron.menus.at(-1);
  assert.equal(menu[0].label, "File");
  assert.ok(menu[0].submenu.some((x) => x.label === "Quit Ana"));
  assert.equal(host.config.leer().idioma_ui, "en");
  assert.equal(tareas, 0);
});

test("host: el estado trae versión, idioma y config; abrirEnlace solo https", async () => {
  const { electron, enviar } = await hostListo({ estado: (b) => ({ ...b, propio: 1 }) });
  await enviar("listo", {});
  const [e] = llamadasA(electron, "estado");
  assert.equal(e.version, "1.2.3"); assert.equal(e.propio, 1); assert.deepEqual(e.config, {});
  for (const u of ["http://a.example", "file:///etc", "javascript:alert(1)", "https://usuario:clave@a.example"]) await enviar("abrirEnlace", { url: u });
  await enviar("abrirEnlace", { url: "https://a.example/x" });
  assert.deepEqual(electron.abiertos, ["https://a.example/x"]);
});

test("host: el protocolo sirve solo ui/ y los medios que la app aprueba, con rangos", async () => {
  const { host, electron, raiz } = await hostListo();
  const pedir = (u, h = {}) => electron.protocolos.ana({ url: u, headers: new Headers(h) });
  assert.equal((await pedir("ana://ui/index.html")).status, 200);
  for (const u of ["ana://ui/../app.json", "ana://ui/%2e%2e/app.json", "ana://otro/x", "ana://video/x.mp4", "ana://ui/index.html?x=1"]) {
    assert.equal((await pedir(u)).status, 404, u);
  }
  const video = path.join(raiz, "v.mp4");
  fs.writeFileSync(video, Buffer.alloc(100, 7));
  host.medios.registrar("video", (ruta) => (ruta === "v.mp4" ? video : null));
  const r = await pedir("ana://video/v.mp4", { range: "bytes=10-19" });
  assert.equal(r.status, 206); assert.equal(r.headers.get("content-range"), "bytes 10-19/100");
  assert.equal((await r.arrayBuffer()).byteLength, 10);
  assert.equal((await pedir("ana://video/otro.mp4")).status, 404);
  assert.equal((await servirArchivo({ headers: new Headers({ range: "bytes=200-" }) }, video)).status, 416);
  assert.throws(() => host.medios.registrar("ui", () => null));
});

// ───────────── 0.2: límites, vigilar, carpeta, secretos, avisos ─────────────
test("enchufe: «limite» trabajo o por orden, «maximo» y «vigilar» con las mismas reglas que pieza.py", () => {
  const enumOrden = { orden: { tipo: "enum", valores: ["a", "b"] } };
  const ok = (a) => E.erroresAccion("x", { script: "a.py", entrada: "archivo", ...a }).length === 0;
  assert.ok(ok({ limite: "trabajo" }));
  assert.ok(ok({ limite: { segun: "orden", valores: { a: "trabajo", b: 60 }, otro: 120 }, datos: enumOrden }));
  assert.ok(!ok({ limite: { segun: "orden", valores: { c: 60 }, otro: 120 }, datos: enumOrden }), "valor que el enum no tiene");
  assert.ok(!ok({ limite: { segun: "orden", valores: {}, otro: 0 }, datos: enumOrden }), "otro fuera de rango");
  assert.ok(!ok({ limite: { segun: "orden", valores: {} }, datos: enumOrden }), "sin otro");
  assert.ok(!ok({ limite: { segun: "t", valores: {}, otro: 5 }, datos: { t: { tipo: "texto", max: 9 } } }), "segun un texto");
  assert.ok(!ok({ limite: "siempre" }));
  assert.ok(!ok({ limite: 5, datos: { t: { tipo: "texto", max: 6 * 1024 * 1024 } } }), "texto más grande que la entrada");
  assert.ok(ok({ limite: 5, maximo: 7 * 1024 * 1024, datos: { t: { tipo: "texto", max: 6 * 1024 * 1024 } } }));
  assert.ok(!ok({ limite: 5, maximo: 51 * 1024 * 1024 }));
  assert.ok(ok({ limite: 5, vigilar: "lee", datos: { ruta: { tipo: "rutaRelativa" } } }));
  assert.ok(!ok({ limite: 5, vigilar: "escribe", datos: { ruta: { tipo: "rutaRelativa" } } }), "escribe sin texto");
  assert.ok(!ok({ limite: 5, vigilar: "lee", datos: { ruta: { tipo: "texto", max: 9 } } }), "ruta que no es rutaRelativa");
  const def = { limite: { segun: "orden", valores: { a: "trabajo" }, otro: 9 } };
  assert.equal(E.limiteDe(def, { orden: "a" }), "trabajo");
  assert.equal(E.limiteDe(def, { orden: "b" }), 9);
  assert.equal(E.limiteDe(def, {}), 9);
  assert.equal(E.limiteDe({ limite: 4 }, {}), 4);
  assert.deepEqual(E.ecoValido({ eco: ["orden", "n"], datos: { orden: enumOrden.orden, n: { tipo: "entero", max: 3 } } }, { orden: "a", n: 9 }), { orden: "a" });
});

test("procesador: un trabajo que late no tiene tope; uno que deja de latir se corta", { skip: process.platform === "win32" }, async () => {
  const { raiz, datos } = crearApp();
  const p = procesadorDe(raiz, datos, { gracia: 1, latido: { muerto: 0.6, primero: 0.6, revisar: 0.1 } });
  const vivo = await p.conEntrada("eco.py", "latir", { vueltas: 10 }, { latido: true });   // ~2 s, más que el tope sin latido
  assert.equal(vivo.ok, true); assert.equal(vivo.latido, true);
  const antes = Date.now();
  const colgado = await p.correrJSON("eco.py", ["colgado"], { latido: true });
  assert.equal(colgado.codigo, "limite"); assert.equal(colgado.texto, "Dejó de avanzar y lo detuve. Intenta de nuevo.");
  assert.ok(Date.now() - antes < 5000);
  assert.equal((await p.correrJSON("eco.py", ["abrir"])).latido, false, "sin trabajo, sin ANA_LATIDO");
});

test("procesador: al salir se corta lo que sigue corriendo", { skip: process.platform === "win32" }, async () => {
  const { raiz, datos } = crearApp();
  const p = procesadorDe(raiz, datos, { gracia: 1 });
  const corriendo = p.correrJSON("eco.py", ["colgado"], { limite: 60 });
  await new Promise((ok) => setTimeout(ok, 300));
  assert.equal(p.enCurso, 1);
  const antes = Date.now();
  p.cortarTodo();
  const r = await corriendo;
  assert.equal(r.ok, false); assert.ok(Date.now() - antes < 4000); assert.equal(p.enCurso, 0);
});

test("host: límite por orden, eco en el error de datos y el texto propio de un inyector", { skip: process.platform === "win32" }, async () => {
  const { host, electron, enviar } = await hostListo({ latido: { muerto: 0.6, primero: 0.6, revisar: 0.1 } });
  await enviar("proyecto", { orden: "latir", vueltas: 8 });          // «trabajo»: dura más que el «otro» (1 s) y no se corta
  assert.equal(llamadasA(electron, "proyectoRespuesta")[0].ok, true);
  await enviar("proyecto", { orden: "abrir", n: 99 });               // n no pasa: el error trae la orden (válida), no n
  const malo = llamadasA(electron, "proyectoRespuesta")[1];
  assert.equal(malo.codigo, "datos"); assert.equal(malo.orden, "abrir"); assert.equal(malo.n, undefined);
  await enviar("proyecto", { orden: "rm -rf" });
  assert.equal(llamadasA(electron, "proyectoRespuesta")[2].orden, undefined, "un eco que no calza nunca vuelve");
  host.inyectores.carpetaActual = () => host.falta("Elige una carpeta primero.", { x: 1 });
  await enviar("leerArchivo", { ruta: "a.md" });
  const f = llamadasA(electron, "archivoAbierto")[0];
  assert.equal(f.codigo, "falta"); assert.equal(f.texto, "Elige una carpeta primero."); assert.deepEqual(f.valores, { x: 1 });
});

test("host: la carpeta elegida, el vigilante y «vigilar» (lo que escribe la app no se avisa)", async () => {
  const { host, electron, enviar, raiz } = await hostListo({ carpeta: { clave: "carpeta" }, vigilar: { extensiones: [".md"] } });
  await enviar("leerArchivo", { ruta: "a.md" });
  assert.equal(llamadasA(electron, "archivoAbierto")[0].texto, "Elige una carpeta primero.", "sin carpeta: el texto del host");
  const docs = path.join(raiz, "docs");
  fs.mkdirSync(docs);
  assert.equal(host.carpeta.usar(docs), fs.realpathSync(docs));
  assert.equal(host.config.leer().carpeta, fs.realpathSync(docs));
  assert.equal(host.vigilante.base, fs.realpathSync(docs));
  await enviar("leerArchivo", { ruta: "a.md" });
  const r = llamadasA(electron, "archivoAbierto")[1];
  assert.equal(r.entrada.carpeta, fs.realpathSync(docs)); assert.equal(host.vigilante.conocidos.get("a.md"), "del disco");
  await enviar("escribirArchivo", { modo: "guardar", ruta: "b.md", texto: "mío" });
  assert.equal(host.vigilante.conocidos.get("b.md"), "mío");
  await enviar("escribirArchivo", { modo: "falla", ruta: "b.md", texto: "otro" });
  assert.equal(host.vigilante.conocidos.get("b.md"), "mío", "si no se pudo escribir, vuelve el de antes");
  // Un documento grande pasa porque la acción dice «maximo».
  await enviar("escribirArchivo", { modo: "guardar", ruta: "c.md", texto: "x".repeat(5.5 * 1024 * 1024) });
  assert.equal(llamadasA(electron, "archivoGuardado")[2].ok, true);
  // Afuera cambia a.md: se avisa; b.md quedó igual a lo que escribió la app: no.
  fs.writeFileSync(path.join(docs, "a.md"), "de otro editor");
  fs.writeFileSync(path.join(docs, "b.md"), "mío");
  electron.llamadas.length = 0;
  await host.vigilante.revisar();
  assert.deepEqual(llamadasA(electron, "archivoCambiado"), [{ ruta: "a.md", texto: "de otro editor" }]);
  assert.ok(!host.vigilante.importa("node_modules/x.md") && !host.vigilante.importa("a.txt") && host.vigilante.importa("sub"));
  host.vigilante.detener();
});

test("host: secretos con safeStorage (nunca en texto plano) y avisos del sistema", async () => {
  const electron = electronFalso();
  let backend = "gnome_libsecret";
  electron.safeStorage = { isEncryptionAvailable: () => true, getSelectedStorageBackend: () => backend,
    encryptString: (t) => Buffer.from("cifrado:" + t), decryptString: (b) => b.toString().replace(/^cifrado:/, "") };
  const vistos = [];
  class Notification { static isSupported() { return true; } constructor(o) { this.o = o; this._on = {}; } on(n, f) { this._on[n] = f; } show() { vistos.push(this); } close() { this.cerrada = true; } }
  electron.Notification = Notification;
  const { raiz, datos } = crearApp();
  const tocados = [];
  const host = crearHost({ electron, recursos: raiz, datos, python: PYTHON, estadoScript: null, alTocarAviso: (id) => tocados.push(id) });
  const s = host.secretos("conexiones");
  assert.ok(s.guardar("banco", "llave-123"));
  assert.equal(s.leer("banco"), "llave-123");
  const archivo = fs.readFileSync(path.join(datos, ".conexiones.json"), "utf8");
  assert.ok(!archivo.includes("llave-123") || archivo.includes(Buffer.from("cifrado:llave-123").toString("base64")));
  assert.ok(!s.guardar("../x", "y") && s.leer("../x") === null);
  if (process.platform !== "win32") assert.equal(fs.statSync(path.join(datos, ".conexiones.json")).mode & 0o777, 0o600);
  backend = "basic_text";
  if (process.platform === "linux") { assert.equal(s.disponible, false); assert.equal(s.leer("banco"), null); assert.equal(s.guardar("otro", "x"), false); }
  s.borrar("banco");
  backend = "gnome_libsecret";
  assert.equal(s.leer("banco"), null);
  assert.throws(() => host.secretos("../x"));
  // Avisos: nada antes de elegir el idioma.
  assert.equal(host.notificaciones.mostrar({ id: "pago", titulo: "Hola" }), false);
  host.config.guardar({ idioma_ui: "es" });
  assert.equal(host.notificaciones.mostrar({ id: "pago", titulo: "Tienes un pago por vencer" }), true);
  assert.equal(host.notificaciones.mostrar({ id: "pago mal", titulo: "x" }), false);
  vistos[0]._on.click();
  assert.deepEqual(tocados, ["pago"]);
  host.notificaciones.quitar("pago");
  assert.ok(vistos[0].cerrada);
});

test("host: menú Ayuda opcional; esperarLibre espera también a los scripts", async () => {
  const { host, electron, enviar } = await hostListo({ sitio: "https://ana.example/", ayuda: false });
  assert.ok(!electron.menus.at(-1).some((m) => m.label === "Ayuda"));
  const corriendo = enviar("lento", {});
  await new Promise((ok) => setTimeout(ok, 100));
  assert.equal(await host.esperarLibre(400), false, "un script corriendo no es estar libre");
  await corriendo;
  assert.equal(await host.esperarLibre(400), true);
});

test("procesador: las variables de la app llegan a todos los scripts, sin pisar las del host", async () => {
  const { raiz, datos } = crearApp();
  const p = procesadorDe(raiz, datos, { entornoApp: { ANA_PROGRAMAS: "/app/MacOS", ANA_DATOS: "/otra", ANA_LATIDO: "/x", "mal nombre": "x" } });
  const r = await p.correrJSON("eco.py", ["abrir"]);
  assert.deepEqual(r.env, ["ANA_DATOS", "ANA_PROGRAMAS", "ANA_RECURSOS"]);
  assert.equal(r.latido, false, "ANA_LATIDO solo lo pone el host");
  const otra = await p.correr("eco.py", ["abrir"], { entorno: { ANA_PROGRAMAS: "/de/la/llamada", ANA_RECURSOS: "/no" } });
  assert.deepEqual(otra.respuesta.env, ["ANA_DATOS", "ANA_PROGRAMAS", "ANA_RECURSOS"]);
  p.entornoApp = () => ({ ANA_HERRAMIENTAS: "/h" });
  assert.ok((await p.correrJSON("eco.py", ["abrir"])).env.includes("ANA_HERRAMIENTAS"), "una función se lee en cada script");
});

test("enchufe: «datos»: «visible» deja ~/<Nombre> recién creada solo para la persona", { skip: process.platform === "win32" }, () => {
  const casa = fs.mkdtempSync(path.join(os.tmpdir(), "casa-"));
  const ruta = E.carpetaDatos({ id: "ana", nombre: "Ana", datos: "visible" }, { casa });
  E.prepararCarpeta(ruta, { visible: true });
  assert.equal(fs.statSync(path.join(casa, "Ana")).mode & 0o777, 0o700);
  assert.equal(fs.statSync(ruta).mode & 0o777, 0o700);
  const ya = path.join(casa, "Otra");
  fs.mkdirSync(ya, { mode: 0o755 }); fs.chmodSync(ya, 0o755);
  E.prepararCarpeta(path.join(ya, ".otra"), { visible: true });
  assert.equal(fs.statSync(ya).mode & 0o777, 0o755, "una que ya existía no se toca");
});

test("host: un enlace tocado pasa por el abrirEnlace de la app; otras ventanas hablan con el puente", async () => {
  const { host, electron, v, enviar } = await hostListo({ entorno: { ANA_PROGRAMAS: "/p" } });
  const pedidos = [];
  host.acciones.registrar("abrirEnlace", (d) => pedidos.push(d.url));
  v.webContents._on["will-navigate"]({ preventDefault() {} }, "https://otro.example/");
  v.webContents.abrir({ url: "https://otro.example/ventana" });
  await new Promise((ok) => setImmediate(ok));
  assert.deepEqual(pedidos, ["https://otro.example/", "https://otro.example/ventana"]);
  assert.deepEqual(electron.abiertos, [], "la app decidió: no se abrió nada");
  // Una declarada corre con las variables de la app.
  await enviar("nivel", { n: 1 });
  assert.ok(llamadasA(electron, "nivelListo")[0].env.includes("ANA_PROGRAMAS"));
  // Otra ventana (el panel): con las mismas guardas, y la respuesta va a ella.
  const panel = new electron.BrowserWindow({ webPreferences: host.ventanas.preferencias() });
  assert.equal(panel.opciones.webPreferences.sandbox, true);
  const enviarPanel = (accion, d, cambio = {}) => electron.ipc.ana({ sender: panel.webContents, senderFrame: panel.webContents.mainFrame, ...cambio }, { accion, datos: d });
  const enPanel = () => electron.llamadas.length;
  const antes = enPanel();
  await enviarPanel("copiar", { texto: "x" });
  assert.equal(enPanel(), antes, "una ventana que no se agregó no habla con el puente");
  host.ventanas.agregar(panel);
  const vistos = [];
  panel.webContents.executeJavaScript = (js) => { vistos.push(js); return Promise.resolve(); };
  electron.llamadas.length = 0;
  await enviarPanel("probarIA", { ia: "codex" });
  await enviarPanel("listo", {});
  assert.equal(llamadasA(electron, "iaProbada").length, 0, "la principal no recibe la respuesta del panel");
  assert.ok(vistos.some((js) => js.includes("window.Ana.iaProbada(") && js.includes('"ia":"codex"')));
  assert.ok(vistos.some((js) => js.includes("window.Ana.estado(")));
  await enviarPanel("copiar", { texto: "x" }, { senderFrame: { url: "ana://ui/index.html" } });   // un iframe del panel
  assert.equal(vistos.filter((js) => js.includes("copiado")).length, 0);
  assert.equal(host.ventanas.todas().length, 2);
});

test("host: ventana sin marco, escondida al arrancar, userData de siempre y app.quit() que guarda", async () => {
  const { raiz, datos } = crearApp();
  const electron = electronFalso();
  const rutas = [];
  electron.app.setPath = (k, v) => rutas.push([k, v]);
  const host = crearHost({ electron, recursos: raiz, datos, python: PYTHON, estadoScript: null, userData: "sistema", abrirAlArrancar: () => false,
    ventana: { frame: false, alCerrar: "esconder" }, tituloAjustes: "Para adultos…", menuApp: ({ item }) => [item("Abrir la carpeta", "carpeta")] });
  host.iniciar();
  await new Promise((ok) => setImmediate(ok));
  const v = electron.ventanas[0];
  assert.equal(v.opciones.frame, false);
  assert.equal(v._on["ready-to-show"], undefined, "no se muestra al crearla");
  assert.deepEqual(rutas, [], "userData queda donde estaba");
  const archivo = electron.menus.at(-1)[0].submenu.map((x) => x.label);
  assert.deepEqual(archivo.slice(0, 2), ["Para adultos…", "Abrir la carpeta"]);
  let frenado = false;
  electron.app._on["before-quit"]({ preventDefault() { frenado = true; } });
  assert.ok(frenado);
  await new Promise((ok) => setTimeout(ok, 500));
  assert.ok(electron.salio, "salió por host.salir (guardando)");
  const otro = crearApp();
  const e2 = electronFalso();
  crearHost({ electron: e2, recursos: otro.raiz, datos: otro.datos, python: PYTHON, estadoScript: null, tituloAjustes: false }).iniciar();
  await new Promise((ok) => setImmediate(ok));
  assert.ok(e2.ventanas[0]._on["ready-to-show"], "sin --oculta ni abrirAlArrancar, se muestra");
  assert.ok(!e2.menus.at(-1)[0].submenu.some((x) => x.label === "Ajustes…"));
});

test("host: guardar como dice si se canceló o falló, privado con app.json", { skip: process.platform === "win32" }, async () => {
  const { host, electron, raiz } = await hostListo();
  let respuesta = { canceled: true };
  electron.dialog.showSaveDialog = async () => respuesta;
  assert.deepEqual(await host.dialogos.guardarArchivo({ extension: "md", contenido: "hola" }), { ok: false, codigo: "cancelado" });
  assert.deepEqual(await host.dialogos.guardarArchivo({ extension: "md", contenido: "" }), { ok: false, codigo: "vacio" });
  assert.deepEqual(await host.dialogos.guardarArchivo({ extension: "md", contenido: "hola", maximo: 2 }), { ok: false, codigo: "tamano" });
  respuesta = { canceled: false, filePath: path.join(raiz, "copia") };
  const r = await host.dialogos.guardarArchivo({ extension: "copia", contenido: "cifrado", privado: true });
  assert.deepEqual(r, { ok: true, ruta: path.join(raiz, "copia.copia") });
  assert.equal(fs.statSync(r.ruta).mode & 0o777, 0o600);
  respuesta = { canceled: false, filePath: path.join("/proc", "no-se-puede.md") };
  assert.equal((await host.dialogos.guardarArchivo({ extension: "md", contenido: "x" })).codigo, "escribir");
  assert.equal(await host.dialogos.guardarComo({ extension: "md", contenido: "x" }), null);
});

test("host: la pieza no trae nada de una app", () => {
  const todo = fs.readdirSync(DIR).map((f) => fs.readFileSync(path.join(DIR, f), "utf8")).join("\n");
  for (const app of ["Esquema", "Graba", "Minuta", "Corta", "Repasa", "Alcancia", "Alcancía"]) {
    const id = app.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    assert.ok(!new RegExp(`(^|[^\\p{L}])${app}(?![\\p{L}])`, "u").test(todo), app);
    for (const marca of [`${id}-app`, `${id}://`, `"${id}"`, `${id.toUpperCase()}_`]) assert.ok(!todo.includes(marca), marca);
  }
});
