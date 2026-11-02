// Una app recién creada con «pieza.py crear» abre de verdad en Linux (Electron + Xvfb), con su host y su interfaz tal cual: el
// idioma primero, la bienvenida traducida, y el ejemplo de punta a punta (la interfaz → el host → bin/ejemplo.py con Python de
// verdad → la interfaz). Lo llama pruebas/test_crear.py si hay Electron (ELECTRON=…/electron/dist/electron) y Playwright:
//   ELECTRON=… PLAYWRIGHT=… xvfb-run -a node pruebas/crear_electron.mjs <app>
import { createRequire } from "node:module";
import assert from "node:assert/strict";
import path from "node:path";

const require = createRequire(import.meta.url);
const { _electron } = require(process.env.PLAYWRIGHT || "playwright");
const app = path.resolve(process.argv[2]);
const electron = await _electron.launch({ executablePath: process.env.ELECTRON, args: ["--no-sandbox", "--disable-gpu", path.join(app, "escritorio", "src", "main.js")] });
const errores = [];
try {
  const w = await electron.firstWindow();
  w.on("pageerror", (e) => errores.push(e.message));
  await w.waitForSelector(".opciones-idioma", { timeout: 30000 });
  assert.match(w.url(), /^[a-z]+:\/\/ui\/index\.html/, "la interfaz se sirve por el protocolo propio");
  assert.equal(await w.evaluate(() => document.documentElement.dataset.host), "linux");
  assert.equal(await w.evaluate(() => typeof require === "undefined" && typeof process === "undefined"), true, "la página no ve Node");
  await w.click('[data-bv-idioma="en"]');
  await w.waitForSelector(".pieza-bv:not(.pieza-bv-idioma)");
  for (let i = 0; i < 10 && await w.locator(".pieza-bv [data-bv-ir].pz-principal:not([disabled])").count(); i++) {
    await w.click(".pieza-bv [data-bv-ir].pz-principal");
  }
  if (await w.locator(".pieza-bv [data-bv-fin]:not([data-bv-fin=despues])").count()) await w.click(".pieza-bv [data-bv-fin]:not([data-bv-fin=despues])");
  else await w.click(".pieza-bv [data-bv-fin=despues]");   // con «ia», sin una IA instalada aquí: «Lo hago después»
  await w.fill("#texto", "Hola, soy Ana Pérez");
  await w.click("#contar");
  await w.waitForSelector("#resultado", { timeout: 30000 });
  assert.match(await w.textContent("#resultado"), /4 words and 15 letters/);
} finally {
  await electron.close();
}
assert.deepEqual(errores, []);
console.log("Electron: todo bien");
