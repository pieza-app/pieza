// La pieza «host-escritorio» con Electron de verdad (sin pantalla, con Xvfb): arma una app ficticia («Ana») con la pieza tal
// cual, la abre y revisa desde su interfaz que el puente funcione de punta a punta, que la página no vea Node y que una acción
// declarada corra su script. Electron se instala aparte (no se versiona):
//   ELECTRON=/ruta/a/node_modules/electron/dist/electron node pruebas/host_escritorio_electron.mjs
// Sin ELECTRON o sin xvfb-run se avisa y se sale bien (como Playwright en correr.sh).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const BASE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ELECTRON = process.env.ELECTRON;
const xvfb = spawnSync("sh", ["-c", "command -v xvfb-run"]).status === 0;
if (!ELECTRON || !fs.existsSync(ELECTRON) || !xvfb) {
  console.log("host-escritorio con Electron: sin ELECTRON o sin xvfb-run, no lo pruebo aquí");
  process.exit(0);
}

const raiz = fs.mkdtempSync(path.join(os.tmpdir(), "host-electron-"));
const casa = path.join(raiz, "casa");
const src = path.join(raiz, "escritorio", "src");
fs.mkdirSync(src, { recursive: true });
for (const f of ["host.js", "enchufe.js", "procesador.js", "preload.js", "vigilante.js"]) fs.copyFileSync(path.join(BASE, "piezas/host-escritorio/escritorio", f), path.join(src, f));
fs.mkdirSync(path.join(raiz, "bin"));
fs.mkdirSync(path.join(raiz, "ui"));
fs.mkdirSync(casa);
fs.writeFileSync(path.join(raiz, "app.json"), JSON.stringify({ id: "ana", nombre: "Ana", config: { idioma_ui: ["es", "en"], tema: ["sistema", "claro", "oscuro"], carpeta: { tipo: "texto", max: 4000, interfaz: false } } }));
const docs = path.join(raiz, "docs");
fs.mkdirSync(docs);
fs.writeFileSync(path.join(docs, "a.md"), "viejo");
fs.writeFileSync(path.join(raiz, "acciones.json"), JSON.stringify({ formato: 1, acciones: {
  probarIA: { script: "eco.py", args: ["probar"], entrada: "archivo", datos: { ia: { tipo: "enum", valores: ["claude", "codex"] } }, responde: "iaProbada", eco: ["ia"], limite: 30 },
} }));
fs.writeFileSync(path.join(raiz, "bin", "eco.py"),
  "import json, sys\nentrada = json.load(open(sys.argv[2]))\njson.dump({'ok': True, 'recibi': entrada}, open(sys.argv[-1], 'w'))\n");
fs.writeFileSync(path.join(raiz, "ui", "index.html"),
  `<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'">
<title>Ana</title><script src="app.js"></script>`);
fs.writeFileSync(path.join(raiz, "ui", "app.js"), `
const vistos = {};
const enviar = (accion, datos) => window.anaEscritorio.enviar({ accion, datos });
window.Ana = {
  estado(e) { vistos.estado = e; enviar("config", { tema: "oscuro" }); enviar("probarIA", { ia: "claude" }); },
  iaProbada(r) { vistos.iaProbada = r; enviar("cambiarAfuera", {}); },
  archivoCambiado(r) {
    vistos.archivoCambiado = r;
    enviar("resultado", { vistos, host: window.ANA_HOST, sinNode: typeof require === "undefined" && typeof process === "undefined",
      oscuro: matchMedia("(prefers-color-scheme: dark)").matches });
  },
};
enviar("listo", {});
`);
fs.writeFileSync(path.join(src, "main.js"), `
const electron = require("electron");
const { crearHost } = require("./host");
const host = crearHost({ electron, carpeta: { clave: "carpeta" }, vigilar: { extensiones: [".md"] } });
// La carpeta con su vigilante (fs.watch de verdad): a.md es conocido; cambia afuera y la interfaz recibe archivoCambiado.
host.acciones.registrar("cambiarAfuera", () => {
  host.carpeta.usar(${JSON.stringify(docs)});
  host.vigilante.conocer("a.md", "viejo");
  setTimeout(() => require("fs").writeFileSync(${JSON.stringify(path.join(docs, "a.md"))}, "de otro editor"), 400);
});
host.acciones.registrar("resultado", (d) => {
  d.secretos = typeof host.secretos("prueba").disponible === "boolean"; process.stdout.write("RESULTADO " + JSON.stringify(d) + "\\n"); electron.app.exit(0); });
setTimeout(() => { process.stdout.write("RESULTADO {}\\n"); electron.app.exit(1); }, 30000);
host.iniciar();
`);

const r = spawnSync("xvfb-run", ["-a", ELECTRON, "--no-sandbox", "--disable-gpu", path.join(src, "main.js")], {
  env: { ...process.env, HOME: casa, XDG_CONFIG_HOME: path.join(casa, ".config"), ELECTRON_ENABLE_LOGGING: "0" }, encoding: "utf8", timeout: 60000,
});
const linea = (r.stdout || "").split("\n").find((l) => l.startsWith("RESULTADO "));
const d = linea ? JSON.parse(linea.slice(10)) : {};
const fallas = [];
const revisar = (ok, que) => { if (!ok) fallas.push(que); };
revisar(d.host === "linux" || d.host === "windows", "window.ANA_HOST");
revisar(d.sinNode === true, "la página no ve Node");
revisar(d.vistos && d.vistos.estado && d.vistos.estado.config && "version" in d.vistos.estado, "estado");
revisar(d.vistos && d.vistos.iaProbada && d.vistos.iaProbada.ok === true && d.vistos.iaProbada.ia === "claude"
  && JSON.stringify(d.vistos.iaProbada.recibi) === '{"ia":"claude"}', "acción declarada con su eco");
revisar(d.vistos && d.vistos.archivoCambiado && d.vistos.archivoCambiado.texto === "de otro editor", "el vigilante avisa un cambio de afuera");
revisar(d.secretos === true, "secretos con safeStorage");
revisar(d.oscuro === true, "config.tema = oscuro cambia la apariencia (nativeTheme)");
const conf = JSON.parse(fs.readFileSync(path.join(casa, ".config", "ana", "config.json"), "utf8"));
revisar(conf.tema === "oscuro", "config.json guardado");
fs.rmSync(raiz, { recursive: true, force: true });
if (fallas.length) {
  console.error("host-escritorio con Electron falló:", fallas.join("; "), "\n", (r.stdout || "").slice(-1500), (r.stderr || "").slice(-1500));
  process.exit(1);
}
console.log("host-escritorio con Electron: todo bien");
