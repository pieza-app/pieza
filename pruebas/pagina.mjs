// La pieza «pagina» en un navegador de verdad: arma la página de una app ficticia («Ana») con pieza.py y la revisa en español e
// inglés, a 1280 y 390 px, en claro y oscuro: sin errores de JavaScript ni de CSP, sin desborde, sin textos sin traducir, con el
// JSON-LD igual a lo que se ve y contraste AA. Necesita Playwright (PLAYWRIGHT=/ruta/a/playwright); lo llama pruebas/correr.sh.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { servir, revisarPagina } from "../piezas/pagina/herramientas/pagina_capturas.mjs";

const BASE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT || "playwright");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pagina-"));
const problemas = [];

// Dos apps: una con todo (Mac, Windows, Linux, IA, catálogo, voz y una comparación) y otra mínima (solo Mac, sin nada más).
const casos = [
  ["completa", "mac,windows,linux", ["pagina", "actualizaciones", "ia", "catalogo", "transcribir"], {
    acento: { claro: "#8a3ffc", oscuro: "#c4a5ff" },
    usa: { notificaciones: true, llavero: false, microfono: true },
    funciones: [{ titulo: { es: "Notas de Ana Pérez", en: "Ana Pérez's notes" }, texto: { es: "Escribe y ordena.", en: "Write and sort." } },
      { titulo: { es: "Sin cuenta", en: "No account" }, texto: { es: "Nada sale de tu computador.", en: "Nothing leaves your computer." } }],
    pasos: [{ titulo: { es: "Abre", en: "Open" }, texto: { es: "Elige tu carpeta.", en: "Pick your folder." } }],
    comparacion: { con: ["Otra app", "Una más"], filas: [{ que: { es: "Precio", en: "Price" }, valores: [{ es: "Gratis", en: "Free" }, { es: "De pago", en: "Paid" }, { es: "Suscripción", en: "Subscription" }] }] },
    preguntas: [{ pregunta: { es: "¿Funciona sin internet?", en: "Does it work offline?" }, respuesta: { es: "Sí. Matías Soto la usa en el avión.", en: "Yes. Matías Soto uses it on the plane." } }],
    red: [{ dominio: "api.ejemplo.com", por: { es: "Solo si conectas Banco Ejemplo.", en: "Only if you connect Banco Ejemplo." } }],
    permisos: [{ sistema: "Windows", nombre: { es: "Cámara", en: "Camera" }, por: { es: "Para la foto de perfil.", en: "For the profile photo." } }],
    estado: { es: "Versión de prueba.", en: "Preview version." },
  }],
  ["minima", "mac", ["pagina"], { demo: false, descargas: false }],
];

const navegador = await chromium.launch();
for (const [nombre, plataformas, piezas, cambios] of casos) {
  const app = path.join(tmp, nombre);
  fs.mkdirSync(path.join(app, "ui"), { recursive: true });
  fs.writeFileSync(path.join(app, "ui", "index.html"), "<!doctype html><title>Ana</title>\n");
  execFileSync("python3", [path.join(BASE, "herramientas", "pieza.py"), "iniciar", app, "ana", "Ana", `--plataformas=${plataformas}`], { stdio: "ignore" });
  for (const p of piezas) execFileSync("python3", [path.join(BASE, "herramientas", "pieza.py"), "agregar", p, app], { stdio: "ignore" });
  const ruta = path.join(app, "docs", "pagina.json");
  fs.writeFileSync(ruta, JSON.stringify({ ...JSON.parse(fs.readFileSync(ruta, "utf8")), ...cambios }));
  execFileSync("python3", [path.join(BASE, "herramientas", "pieza.py"), "generar", app], { stdio: "ignore" });
  const s = await servir(0, app);
  const url = `http://127.0.0.1:${s.address().port}/`;
  for (const l of ["es", "en"]) for (const ancho of [1280, 390]) for (const oscuro of [false, true]) {
    const etiqueta = `${nombre}, ${l}, ${ancho} px, ${oscuro ? "oscuro" : "claro"}`;
    const p = await navegador.newPage({ viewport: { width: ancho, height: 800 }, colorScheme: oscuro ? "dark" : "light", locale: l === "en" ? "en-US" : "es-CL" });
    p.on("pageerror", (e) => problemas.push(`${etiqueta}: JS ${e.message}`));
    p.on("console", (m) => { if (m.type() === "error" || /Content Security Policy/i.test(m.text())) problemas.push(`${etiqueta}: consola ${m.text().slice(0, 160)}`); });
    await p.goto(url + (l === "en" ? "?lang=en" : ""));
    await p.evaluate(() => document.querySelectorAll("details").forEach((d) => { d.open = true; }));
    problemas.push(...await revisarPagina(p, l, etiqueta));
    const titulo = await p.evaluate((l) => document.documentElement.dataset[l === "es" ? "tituloEs" : "tituloEn"], l);
    if (await p.title() !== titulo) problemas.push(`${etiqueta}: el título no está en su idioma`);
    // Lo que se ve calza con lo que la app tiene.
    const hay = await p.evaluate(() => ({ demo: !!document.querySelector('a[href="demo/"]'), so: [...document.querySelectorAll(".so")].map((a) => a.dataset.so),
      huggingface: document.body.textContent.includes("huggingface.co"), avisos: !!document.querySelector("#permisos li") }));
    if (nombre === "minima" && (hay.demo || hay.so.length || hay.huggingface || hay.avisos)) problemas.push(`${etiqueta}: muestra algo que la app no tiene ${JSON.stringify(hay)}`);
    if (nombre === "completa" && (!hay.demo || hay.so.join() !== "mac,windows,linux" || !hay.huggingface || !hay.avisos)) problemas.push(`${etiqueta}: le falta algo ${JSON.stringify(hay)}`);
    await p.close();
  }
  s.close();
}
await navegador.close();
fs.rmSync(tmp, { recursive: true, force: true });
if (problemas.length) { console.log("✗ " + problemas.join("\n✗ ")); process.exit(1); }
console.log("✓ Página: dos apps ficticias en es/en, 1280 y 390 px, claro y oscuro");
