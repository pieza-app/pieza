// {{nombre}} para Windows y Linux: la app nativa genérica de Pieza (pieza «host-escritorio»: host.js, enchufe.js, procesador.js,
// preload.js y vigilante.js, que no se editan aquí) con la misma interfaz de ui/ y los mismos scripts de bin/.
// Empezó con «pieza.py crear»: desde ahí es de la app. Lo que solo corre un script NO va aquí: se declara en app.json → acciones.
// Aquí va lo nativo propio (host.acciones.registrar), los menús y lo que se suma al estado (README de «host-escritorio»).
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const electron = require("electron");
const { crearHost } = require("./host");
{{#si piezas.actualizaciones}}
const { crear: crearActualizaciones } = require("./actualizaciones");
{{/si}}

const icono = path.join(__dirname, "..", "iconos", "{{id}}-256.png");
const host = crearHost({
  electron,
  global: "{{nombre_ascii}}",
  ventana: { ancho: 1280, alto: 800, ...(fs.existsSync(icono) ? { icono } : {}) },
  sitio: "{{web|https}}",
  codigo: "https://github.com/{{repo}}",
{{#si piezas.actualizaciones}}
  // Pieza «actualizaciones»: solo los Releases de {{repo}}, verificados con su .sha256; sin empaquetar no busca.
  actualizaciones: crearActualizaciones({ app: electron.app, net: electron.net, repo: "{{repo}}", nombre: {{nombre|json}} }),
{{/si}}
});
// La app: lo nativo propio, p. ej. host.acciones.registrar("exportar", async (d) => { … }) (el mismo que p.registrar en Mac).
host.iniciar();
