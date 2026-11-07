// La interfaz de la app de prueba: pide «listo», recibe el estado, corre una acción declarada y carga un medio.
"use strict";
const host = PiezaHost.crearHost({ nombre: "prueba", global: "Prueba" });
const visto = { plataforma: host.plataforma };
function anotar(k, v) { visto[k] = v; host.enviar("anotar", { texto: JSON.stringify(visto) }); }
host.responder({
  estado(e) { document.getElementById("estado").textContent = e.version; anotar("estado", { version: e.version, idioma: e.idioma }); },
  anotado(r) { if (!visto.anotado) { visto.anotado = r.ok; anotar("eco", r.ok); } },
  propia(r) { anotar("propia", r); },
});
const img = document.getElementById("medio");
img.onload = () => anotar("medio", img.naturalWidth);
img.onerror = () => anotar("medio", "error");
img.src = host.medio("imagenes", "punto.png");
host.enviar("listo");
host.enviar("propia", { n: 2 });
