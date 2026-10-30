// Página de Pieza: idioma (es/en) y datos (catálogo y proyectos). Todo lo que viene de datos/*.json se pone con textContent.
(function () {
  "use strict";
  const EN = {
    saltar: "Skip to content", n_como: "How it works", n_proy: "Projects", n_cat: "Catalog", n_emp: "Get started",
    ante: "Open framework · AGPL-3.0", h1: "Build open apps from tested pieces.",
    bajada: "Your own AI, languages, safe updates, a community catalog… Pick the pieces, review your app's full spec and plug them in. Every app that gets built leaves pieces for the next one.",
    c_apps: "apps made with Pieza", c_piezas: "pieces in the catalog", c_listas: "ready to use",
    b_emp: "Get started", b_cod: "See the code", h_como: "How it works",
    p1: "Describe your idea", p1p: "One round of questions. Your AI recommends the pieces that fit, and the ones every app needs come along.",
    p2: "Review the spec", p2p: "Before anything is created you see it all: screens, settings, permissions per platform, what it connects to and what only you can do.",
    p3: "Plug in and grow", p3p: "Pieces are copied into your app and they're yours. When one improves you get it without losing your changes; when you improve it, it goes back to every app.",
    h_proy: "Made with Pieza", nota_proy: "Public repos with the “hecho-con-pieza” topic on GitHub. No telemetry: only the ones that choose to show up.",
    h_cat: "Catalog", nota_cat: "Each piece says which screens it adds, which permissions it asks for on each platform and what it connects to. “On the way” = already proven in an app, waiting to be extracted.",
    h_emp: "Get started", e_cc: "Install the plugin: it brings the flow to create apps and the one to review contributions.", e_cc2: "Then: “let's build an app for…”.",
    e_ai: "Download the skills and upload them in your account's capabilities.", e_otra_h: "Another AI",
    e_otra: "Codex, Gemini or whichever you use: clone the repo and ask it to follow AGENTS.md. The flows live in skills/.",
    h_sello: "Built an app with Pieza?", sello_p: "Add the hecho-con-pieza topic to its repo and it shows up here. If you like, add the badge to your README or page:",
    h_pri: "Non-negotiables", pr1: "Data belongs to the person: on their computer or in their git.",
    pr2: "The AI is the person's own, with their account, and it can't touch anything we don't send it.",
    pr3: "What the person types never goes as a process argument.", pr4: "No dependencies: Python's standard library, web without CDNs.",
    pr5: "Language is asked first.", pr6: "Open and free, no accounts or tracking.", pie: "Pieza · AGPL-3.0 · no cookies or tracking",
    secciones: "Sections",
  };
  const TXT = {
    es: { lista: "Lista", camino: "En camino", plataformas: "Plataformas", permisos: "Permisos", red: "Sale a", sinRed: "funciona sin internet",
          ninguno: "ninguno", vacio: "Aún no hay apps públicas con el topic. ¡La tuya puede ser la primera!", familia: "familia",
          actualizado: "Actualizado: {x}", siempre: "va en toda app", sinDatos: "No pude cargar los datos. Recarga la página." },
    en: { lista: "Ready", camino: "On the way", plataformas: "Platforms", permisos: "Permissions", red: "Connects to", sinRed: "works offline",
          ninguno: "none", vacio: "No public apps with the topic yet. Yours could be the first!", familia: "family",
          actualizado: "Updated: {x}", siempre: "in every app", sinDatos: "Couldn't load the data. Reload the page." },
  };
  const CATEGORIAS = {
    base: ["Base", "Base"], interfaz: ["Interfaz", "Interface"], ia: ["IA", "AI"], datos: ["Datos", "Data"], medios: ["Audio y video", "Audio and video"],
    conexiones: ["Conexiones", "Connections"], plataforma: ["Plataforma", "Platform"], repo: ["Repo y página", "Repo and page"],
  };
  const ORDEN = ["base", "ia", "interfaz", "plataforma", "datos", "medios", "conexiones", "repo"];
  const ES = {};
  let idioma = "es", catalogo = null, proyectos = null;

  function guardado() { try { return localStorage.getItem("idioma"); } catch (e) { return null; } }
  function guardar(v) { try { localStorage.setItem("idioma", v); } catch (e) { /* sin almacenamiento: igual funciona */ } }
  function el(etiqueta, clase, texto) { const n = document.createElement(etiqueta); if (clase) n.className = clase; if (texto != null) n.textContent = texto; return n; }
  const t = (k) => TXT[idioma][k];

  function aplicarIdioma(v) {
    idioma = v === "en" ? "en" : "es";
    document.documentElement.lang = idioma;
    document.querySelectorAll("[data-t]").forEach((n) => {
      const k = n.dataset.t;
      if (!(k in ES)) ES[k] = n.textContent;
      n.textContent = idioma === "en" && EN[k] ? EN[k] : ES[k];
    });
    const b = document.getElementById("idioma");
    b.textContent = idioma === "en" ? "ES" : "EN";
    b.lang = idioma === "en" ? "es" : "en";
    b.setAttribute("aria-label", idioma === "en" ? "Leer en español" : "Read in English");
    document.querySelectorAll('img[src^="sello"]').forEach((i) => { i.src = idioma === "en" ? "sello-en.svg" : "sello.svg"; i.alt = idioma === "en" ? "Made with Pieza" : "Hecho con Pieza"; });
    pintar();
  }

  function pintarProyectos() {
    const ul = document.getElementById("lista-proyectos");
    ul.replaceChildren();
    if (!proyectos) return;
    document.getElementById("n-apps").textContent = String(proyectos.total);
    if (!proyectos.proyectos.length) { ul.append(el("li", "vacio", t("vacio"))); }
    for (const p of proyectos.proyectos) {
      const li = el("li");
      const a = el("a", "nombre", p.nombre.split("/")[1]);
      a.href = p.pagina || p.url;
      li.append(a);
      if (p.descripcion) li.append(el("p", "desc", p.descripcion));
      const pie = el("span", "etiqueta", p.nombre.split("/")[0] + (p.familia ? " · " + t("familia") : ""));
      li.append(pie);
      ul.append(li);
    }
    document.getElementById("actualizado").textContent = proyectos.actualizado ? t("actualizado").replace("{x}", proyectos.actualizado) : "";
  }

  function pintarCatalogo() {
    const caja = document.getElementById("lista-catalogo");
    caja.replaceChildren();
    if (!catalogo) return;
    document.getElementById("n-piezas").textContent = String(catalogo.total);
    document.getElementById("n-listas").textContent = String(catalogo.listas);
    const yo = idioma === "en" ? 1 : 0;
    for (const cat of ORDEN) {
      const grupo = catalogo.piezas.filter((p) => p.categoria === cat);
      if (!grupo.length) continue;
      const sec = el("div", "grupo");
      sec.append(el("h3", null, (CATEGORIAS[cat] || [cat, cat])[yo]));
      const ul = el("ul", "piezas");
      grupo.sort((a, b) => (a.estado === "lista" ? 0 : 1) - (b.estado === "lista" ? 0 : 1));
      for (const p of grupo) {
        const li = el("li");
        const cab = el("div", "cabeza");
        cab.append(el("b", null, p.nombre || p.id));
        const lista = (p.estado || "lista") === "lista";
        cab.append(el("span", "etiqueta" + (lista ? " lista" : ""), lista ? t("lista") + " · " + p.version : t("camino")));
        li.append(cab, el("p", null, p.descripcion || ""));
        const datos = el("div", "datos");
        const permisos = Object.entries(p.permisos || {}).flatMap(([plat, l]) => l.map((x) => plat + ": " + x.clave));
        datos.append(el("span", null, t("plataformas") + ": " + (p.plataformas || []).join(", ") + (p.siempre ? " · " + t("siempre") : "")));
        datos.append(el("span", null, t("permisos") + ": " + (permisos.length ? permisos.join("; ") : t("ninguno"))));
        datos.append(el("span", null, t("red") + ": " + ((p.red || []).length ? p.red.join(", ") : (p.red_nota || t("sinRed")))));
        li.append(datos);
        ul.append(li);
      }
      sec.append(ul);
      caja.append(sec);
    }
  }

  function pintar() { pintarProyectos(); pintarCatalogo(); }

  async function cargar(nombre) {
    const r = await fetch("datos/" + nombre, { cache: "no-cache" });
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const pedido = new URLSearchParams(location.search).get("lang");
    const inicial = pedido || guardado() || ((navigator.language || "es").toLowerCase().startsWith("es") ? "es" : "en");
    document.getElementById("idioma").addEventListener("click", () => { const v = idioma === "en" ? "es" : "en"; guardar(v); aplicarIdioma(v); });
    aplicarIdioma(inicial);
    Promise.allSettled([cargar("catalogo.json"), cargar("proyectos.json")]).then(([c, p]) => {
      if (c.status === "fulfilled") catalogo = c.value;
      if (p.status === "fulfilled") proyectos = p.value;
      if (!catalogo || !proyectos) document.getElementById("actualizado").textContent = t("sinDatos");
      pintar();
    });
  });
})();
