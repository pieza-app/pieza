// {{nombre}}: la interfaz. La misma en Mac, Windows y Linux (host-tauri, con el WebView del sistema) y en el navegador (vista previa con demo.json).
// La app manda el estado con window.{{nombre_ascii}}.estado(json); la interfaz pide cosas con host.enviar(accion, datos).
// Empezó con «pieza.py crear» (pieza «esqueleto» de Pieza): desde ahí es de la app. Lo marcado «La app:» es lo que falta escribir.
// Las piezas de interfaz (host.js, i18n.js, tema.*, componentes.*, bienvenida.*) no se editan aquí: ver AGENTS.md → «Piezas».
(() => {
  "use strict";
  // ── Puente con la app: pieza «host-ui». host.plataforma es "mac" | "windows" | "linux" | "web" (vista previa: simular()). ──
  const host = PiezaHost.crearHost({ nombre: {{id|json}}, global: {{nombre_ascii|json}}, simular: (accion, d, c) => simular(accion, d, c) });
  const NOMBRE = {{nombre|json}};
  const REPO = {{repo|json}};
  const ENLACES = { sitio: {{web|json}}, codigo: `https://github.com/${REPO}`, comunidad: `https://github.com/${REPO}/discussions`,
    aportar: `https://github.com/${REPO}/blob/main/CONTRIBUTING.md` };
  const E = { config: {}, version: "", ias: [], ajustes: false, texto: "", resultado: null, trabajando: false, iniciada: false };
  const raiz = document.getElementById("app");
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");

  // ── Idiomas: pieza «i18n». Las claves son la frase en español; el inglés, en idiomas/en.json (todo texto nuevo va ahí). ──
  const faltantes = new Set();   // pruebas/interfaz.mjs revisa que no quede nada sin traducir
  const i18n = PiezaI18n.crear({ faltantes });
  const { Tp } = i18n;
  let idiomaElegido = null;
  async function cargarIdioma(elegido) {
    // Lo recién elegido > ?idioma= (vista previa y pruebas) > lo guardado > el del sistema.
    if (elegido) idiomaElegido = elegido;
    await i18n.cargar(i18n.elegir({ elegido: idiomaElegido, config: E.config.idioma_ui }));
    document.documentElement.lang = i18n.idioma;
  }

  // ── Tema (sistema, claro u oscuro) y componentes (diálogos, avisos, Tu IA, actualizaciones, Acerca de) ──
  const tema = PiezaTema.crear({ guardar: (v) => { E.config.tema = v; host.enviar("config", { tema: v }); } });
  const ui = PiezaComponentes.crear({
    i18n, host, app: NOMBRE, repo: REPO, version: () => E.version, pintar, mantenerCampos: true,
    cerrar: () => { E.ajustes = false; pintar(); },   // Esc, el velo o ✕ sobre un diálogo de la app
    retener: (...a) => bv.retener(...a),               // mientras se elige el idioma, los avisos esperan
    elegirIA: (id) => { E.config.ia = id; host.enviar("config", { ia: id }); },
  });
  const toast = (frase, o) => ui.aviso(frase, o);

  // ── Bienvenida: pieza «bienvenida». El idioma siempre primero y solo en la pantalla; después, los pasos de la app. ──
  const bv = PiezaBienvenida.crear({
    i18n, pintar, mostrarAviso: (...a) => toast(...a),
    guardarIdioma: (c) => { E.config.idioma_ui = c; host.enviar("config", { idioma_ui: c }); },
    cargarIdioma: (c) => cargarIdioma(c),
    terminar: () => { E.config.bienvenida = true; host.enviar("config", { bienvenida: true }); },
  });
  // La app: cambia el saludo (y su inglés en idiomas/en.json) y suma los pasos que necesite (permisos, una carpeta…).
  bv.sumarPaso({ id: "hola", orden: 10, titulo: "Te damos la bienvenida", saltable: false,
    cuerpo: () => `<p><b data-sin-traducir>${esc(NOMBRE)}</b></p><p>La app: en una o dos frases, qué hace y para quién.</p>` });
{{#si piezas.ia}}
  bv.sumarPaso({ id: "ia", orden: 20, titulo: "Elige tu IA", puede: () => !!E.config.ia,
    cuerpo: () => `<p>Usa la IA que ya tienes, con tu cuenta. La probamos con una pregunta corta.</p>${ui.filasIA({ ias: E.ias, elegida: E.config.ia })}` });
{{/si}}

  // ── Lo que se ve ──
  // La app: aquí va la pantalla principal. Este ejemplo va de punta a punta: manda el texto a bin/ejemplo.py por la acción
  // declarada «ejemplo» (app.json → acciones: el texto va por archivo, nunca como argumento) y muestra lo que responde.
  function principal() {
    return `<header class="barra"><h1 data-sin-traducir>${esc(NOMBRE)}</h1>
      <button type="button" class="pz-boton" id="abrir-ajustes">Ajustes</button></header>
      <main class="contenido">
        <h2>Prueba el ejemplo</h2>
        <p class="suave">La app: aquí va la pantalla principal.</p>
        <label class="pz-campo"><span>Escribe algo</span><textarea id="texto" rows="4">${esc(E.texto)}</textarea></label>
        <div class="pz-pie"><button type="button" class="pz-boton pz-principal" id="contar"${E.trabajando ? " disabled" : ""}>${E.trabajando ? "Contando…" : "Contar palabras"}</button></div>
        ${E.resultado ? `<p id="resultado" class="resultado" data-sin-traducir>${esc(Tp("{n} palabras y {l} letras", { n: E.resultado.palabras, l: E.resultado.letras }))}</p>` : ""}
      </main>`;
  }
  function ajustes() {
    const idiomas = [["es", "Español"], ["en", "English"]].map(([c, n]) =>
      `<button type="button" data-idioma="${c}" aria-pressed="${i18n.idioma === c}" lang="${c}" data-sin-traducir>${n}</button>`).join("");
    return `<h3>Idioma</h3><div class="pz-seg" role="group" aria-label="Idioma">${idiomas}</div>
      <h3>Apariencia</h3>${tema.selectorHTML()}
{{#si piezas.ia}}
      <h3>Tu IA</h3>${ui.filasIA({ ias: E.ias, elegida: E.config.ia })}
{{/si}}
{{#si piezas.actualizaciones}}
      <h3>Actualizaciones</h3>${ui.filaActualizacion()}
{{/si}}
      <h3>Acerca de</h3>${ui.acercaDe({ version: E.version, enlaces: ENLACES })}`;
  }
  function pintar() {
    if (bv.soloIdioma) {   // primer uso: el idioma, solo (sin la app detrás ni avisos)
      raiz.innerHTML = `<div class="pantalla-idioma">${bv.html()}</div>`;
      bv.enfocar();
      return;
    }
    raiz.innerHTML = principal()
      + (bv.activa ? ui.envolver(bv.html(), { id: "t-bv", sinEsc: true }) : "")
      + (E.ajustes ? ui.dialogo({ id: "t-ajustes", titulo: "Ajustes", cuerpo: ajustes(),
        pie: '<button type="button" class="pz-boton pz-principal" data-pz-cerrar>Listo</button>' }) : "")
      + ui.capas();
    i18n.traducirDOM(raiz);
    ui.despuesDePintar();
  }

  // ── Lo que hace la persona ──
  document.addEventListener("click", async (ev) => {
    if (bv.manejarClic(ev) || ui.manejarClic(ev)) return;
    if (tema.manejarClic(ev)) return pintar();
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.id === "abrir-ajustes") { E.ajustes = true; pintar(); }
    else if (b.dataset.idioma) {
      E.config.idioma_ui = b.dataset.idioma;
      host.enviar("config", { idioma_ui: b.dataset.idioma });
      await cargarIdioma(b.dataset.idioma);
      pintar();
    } else if (b.id === "contar") {
      E.trabajando = true;
      pintar();
      host.enviar("ejemplo", { texto: E.texto });
    }
  });
  document.addEventListener("keydown", (ev) => { if (ui.manejarTecla(ev)) return; bv.manejarTecla(ev); });
  document.addEventListener("input", (ev) => { if (ev.target.id === "texto") E.texto = ev.target.value; });

  // ── Lo que manda la app ──
  host.responder({
    async estado(e) {
      Object.assign(E, { config: e.config || {}, version: e.version || "" });
      await cargarIdioma();
      tema.aplicar(tema.elegir({ config: E.config.tema }));
{{#si piezas.actualizaciones}}
      ui.actualizacionDisponible(e.actualizacion && e.actualizacion.hay ? e.actualizacion : null, { pintar: false });
{{/si}}
      if (!E.iniciada) {
        E.iniciada = true;
        bv.abrir({ config: E.config, forzar: new URLSearchParams(location.search).has("bienvenida") });
{{#si piezas.ia}}
        host.enviar("listaIA");
{{/si}}
      }
      pintar();
    },
    ejemploListo(r) {
      E.trabajando = false;
      if (r && r.ok) E.resultado = r;
      else toast((r && r.error) || "No se pudo.", { error: true });
      pintar();
    },
{{#si piezas.ia}}
    iaLista(r) { E.ias = (r && r.ias) || []; pintar(); },
    iaProbada: (r) => ui.iaProbada(r),
{{/si}}
{{#si piezas.actualizaciones}}
    actualizacionRevisada: (r) => ui.actualizacionRevisada(r, { pintar: !bv.soloIdioma }),
    actualizacionProgreso: (a) => ui.actualizacionProgreso(a),
{{/si}}
    // Los menús de la app (host-mac / host-escritorio): «Ajustes…» abre Ajustes (nunca en medio de la bienvenida); «guardar»
    // (al cerrar o salir) no tiene nada pendiente aquí.
    menu(m) { if (m && m.accion === "ajustes" && !bv.activa) { E.ajustes = true; pintar(); } },
    _probar(f) { f(E); pintar(); },
    _pruebas: { ui, bv, i18n, faltantes, E },
  });

  // ── Vista previa en el navegador (datos ficticios de demo.json): c.responder("x", json) hace lo que la app ──
  let DEMO = null;
  const COMUNES = PiezaHost.simulacionesComunes();
  function simular(accion, d, c) {
    if (!DEMO) return;
    switch (accion) {
      case "listo": return c.responder("estado", DEMO);
      case "config": Object.assign(DEMO.config, d); return;
      case "ejemplo": {
        const texto = String(d.texto || "");
        return c.luego(300, () => c.responder("ejemploListo", { ok: true, palabras: texto.split(/\s+/).filter(Boolean).length,
          letras: [...texto].filter((x) => /\p{L}/u.test(x)).length }));
      }
{{#si piezas.ia}}
      case "listaIA": return c.responder("iaLista", { ias: DEMO.ias, elegida: DEMO.config.ia });
{{/si}}
      default: return COMUNES[accion] ? COMUNES[accion](d, c) : undefined;
    }
  }

  async function iniciar() {
    if (host.plataforma === "web") {
      try { DEMO = await (await fetch("demo.json")).json(); } catch { DEMO = { config: {} }; }
      // ?bienvenida: el primer uso, desde el idioma.
      if (new URLSearchParams(location.search).has("bienvenida")) DEMO.config.idioma_ui = "";
    }
    host.enviar("listo");
  }
  iniciar();
})();
