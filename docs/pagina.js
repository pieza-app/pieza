// Página de Pieza: idioma (es/en), datos (catálogo y proyectos), estrellas, el relato al bajar, «¿Qué IA usas?» y el manifiesto.
// Todo lo que viene de datos/*.json se pone con textContent. Sin dependencias.
(function () {
  "use strict";
  document.documentElement.classList.add("js");
  const quieto = window.matchMedia("(prefers-reduced-motion: reduce)");

  const EN = {
    saltar: "Skip to content", n_como: "How it works", n_proy: "Projects", n_cat: "Catalog", n_emp: "Get started", n_man: "Manifesto",
    ante: "Open and free framework", h1: "Build open apps from tested pieces.",
    bajada2: "Your own AI, languages, safe updates, a community catalog… You pick the pieces and your AI plugs them in. Every app that gets built leaves pieces for the next one.",
    c_apps: "apps made with Pieza", c_piezas: "pieces in the catalog", c_listas: "ready to use",
    b_emp: "Get started", b_cod: "See the code", h_como: "How it works",
    r0: "AI", r1: "Languages", r2: "Up to date", r3: "Welcome", r4: "Your app", r5: "Settings", r6: "Catalog", r7: "Data", r8: "Security",
    como_bajada: "Four steps. You talk; your AI and the pieces do the rest.",
    globo_idea: "I want an app to organize my recipes.",
    fm_t: "Your app's spec", fm_1: "4 screens", fm_2: "Permissions: none", fm_3: "Internet: only to update itself", al_dia: "Up to date ✓",
    s1: "Tell your AI your idea.", s1p: "In your own words, the way you'd tell someone. For example: “an app to organize my recipes”.",
    s2: "Look at the spec before anything is made.", s2p: "You see which screens it will have, which permissions it asks for and whether it goes online. If you don't like something, change it.",
    s3: "The pieces plug in on their own.", s3p: "Languages, your AI, updates… already proven in other apps. Nothing is written from scratch.",
    s4: "They stay up to date on their own.", s4p: "When a piece improves, your app gets the fix without losing what you changed.",
    por_dentro: "Under the hood, for developers",
    p1: "Describe your idea", p1p: "One round of questions. Your AI recommends the pieces that fit, and the ones every app needs come along.",
    p2: "Review the spec", p2p: "Before anything is created you see it all: screens, settings, permissions per platform, what it connects to and what only you can do.",
    p3: "Plug in and grow", p3p: "Pieces are copied into your app and they're yours. When one improves you get it without losing your changes; when you improve it, it goes back to every app.",
    h_emp: "Get started", q_ia: "Which AI do you use?", otra: "Other", otra_ia: "Another AI: ",
    paso_copia: "Copy and paste this in your terminal", paso_bajar: "Download them and upload them to your account",
    paso_clonar: "Clone it and ask it to follow AGENTS.md", copiar: "Copy", ver_det: "See details",
    d_cc: "If you're already inside Claude Code, type these two commands:",
    z_crear: "Create apps (.zip)", z_revisar: "Review contributions (.zip)",
    paso_pide: "Ask it: “let's build an app for…”", globo_ej: "Let's build an app to organize my recipes.",
    paso_ficha: "Look at the spec and say yes", fe_1: "Screens: 4", fe_2: "Permissions: none", fe_3: "Internet: updates only", fe_ok: "Yes, build it",
    e_cc: "Install the plugin: it brings the flow to create apps and the one to review contributions.",
    e_gm: "Install the extension: the same skills plus the /pieza:crear and /pieza:revisar commands.",
    e_cx: "Install the skills in ~/.agents/skills (it updates them without erasing your local settings).",
    e_ai: "Download the skills and upload them in your account's capabilities.",
    e_otra: "Another AI? Clone the repo and ask it to follow AGENTS.md. Equivalences between tools:",
    h_cat: "Catalog", nota_cat: "Each piece says which screens it adds, which permissions it asks for on each platform and what it connects to. “On the way” = already proven in an app, waiting to be extracted.",
    nota_com: "Community pieces live in their maker's repo. We review them before marking them as reviewed.",
    filtrar: "Filter pieces", f_todas: "All", f_rev: "Reviewed", f_sin: "Not reviewed",
    h_proy: "Made with Pieza", nota_proy: "Public repos with the “hecho-con-pieza” topic on GitHub. No telemetry: only the ones that choose to show up.",
    h_sello: "Built an app with Pieza?", sello_p: "Give its repo the hecho-con-pieza topic and it shows up here.",
    sello_como: "How to do it", sello_p2: "If you like, add the badge to your README or page:",
    prompt: "pieza@your-computer:~$ cat MANIFESTO.md",
    lema: "We build in the open. We share what works. Nobody owns your computer but you.",
    man_intro: "Pieza was born from a simple idea: if someone already solved something well, nobody else should have to solve it again. Every app in this family left pieces for the next one. Now those pieces belong to everyone.",
    man_creemos: "What we believe",
    m1: "Your computer is yours.", m1p: "Apps live there, with your data there. No servers watching you, no accounts tying you down, no telemetry.",
    m2: "Your AI is yours.", m2p: "We use the one you already have, with your account. Never ours. Never between you and your data.",
    m3: "Code is shared.", m3p: "Everything is open (AGPL-3.0): read it, change it, use it. If you improve it and publish it, your improvement belongs to everyone too.",
    m4: "Non-profit.", m4p: "No ads, no paid plans, no “pro version”. This exists because it's useful, not to sell you something.",
    m5: "Learn from whoever does it better.", m5p: "Every contribution is reviewed looking for what the other person did better. What we learn is written down and reaches every app.",
    m6: "Credit, always.", m6p: "Whoever contributes is named in what they made.",
    m7: "Safe before fast.", m7p: "What comes from outside gets validated. What installs as safe, someone read in full.",
    m8: "For anyone.", m8p: "If it needs a manual, it's badly made. Language is asked first.",
    h_sumate: "Join in", sumate_p: "You don't need permission to start. A piece of yours can save someone on the other side of the world weeks of work.",
    su1: "Publish a piece", su1p: "In your own repo, with the pieza-comunidad topic.",
    su2: "Build an app", su2p: "Tell your AI “let's build an app for…” and give it the hecho-con-pieza topic.",
    su3: "Talk", su3p: "Ideas, questions and what you learned, in Discussions.",
    su4: "Contribute", su4p: "Translate, test, report a bug or improve a piece.",
    man_completo: "Read the full manifesto", man_firma: "Made in Chile, for anywhere. By people who share what they know.",
    h_pri: "Non-negotiables", pr1: "Data belongs to the person: on their computer or in their git.",
    pr2: "The AI is the person's own, with their account, and it can't touch anything we don't send it.",
    pr3: "What the person types never goes as a process argument.", pr4: "No dependencies: Python's standard library, web without CDNs.",
    pr5: "Language is asked first.", pr6: "Open and free, no accounts or tracking.", pie: "Pieza · AGPL-3.0 · no cookies or tracking",
    secciones: "Sections",
    h_faq: "Frequently asked questions",
    q1: "Is Pieza a framework?", a1: "Yes, with one difference: pieces are copied into your app and they're yours. You don't depend on a package that can break from the outside, and when a piece improves you get it without losing your changes.",
    q2: "Do I need Claude Code?", a2: "No. The flows work the same in Claude Code, Gemini CLI and Codex, and with any other AI by following AGENTS.md. The pieza.py tool works on its own, with Python.",
    q3: "Does Pieza send data to any server?", a3: "No. There are no servers and no telemetry. The app counter only counts public repos that added the hecho-con-pieza topic on GitHub.",
    q4: "How do I hear about new versions of a piece?", a4: "Every app built with Pieza ships the “Pieza al día” workflow: once a week it opens a PR with the fixes and improvements that can be applied on their own, and an issue with the steps for what has to be done by hand.",
    q5: "What's the license?", a5: "AGPL-3.0, like the apps in the family. It's free and open.",
    comunidad: "Community", aportar: "How to contribute",
  };
  const TXT = {
    es: { lista: "Lista", camino: "En camino", plataformas: "Plataformas", permisos: "Permisos", red: "Sale a", sinRed: "funciona sin internet",
          ninguno: "ninguno", vacio: "Todavía no hay apps aquí. La tuya puede ser la primera.", familia: "familia",
          actualizado: "Actualizado: {x}", siempre: "va en toda app", sinDatos: "No pude cargar los datos. Recarga la página.",
          oficial: "Oficial", revisada: "Comunidad · Revisada ✓", sinRevisar: "Comunidad · Sin revisar",
          aviso: "Aún no la revisamos: instálala bajo tu responsabilidad.", deRepo: "En {x}",
          nadaFiltro: "No hay piezas con ese filtro.", aprobadas: "{n} aprobadas por la comunidad",
          aprobada: "Aprobada por la comunidad ✓", sinRevisarApp: "Sin revisar", repo: "Código", pagina: "Página", copiado: "Copiado ✓", seleccionado: "Seleccionado: copia con Ctrl+C o ⌘C" },
    en: { lista: "Ready", camino: "On the way", plataformas: "Platforms", permisos: "Permissions", red: "Connects to", sinRed: "works offline",
          ninguno: "none", vacio: "No apps here yet. Yours could be the first.", familia: "family",
          actualizado: "Updated: {x}", siempre: "in every app", sinDatos: "Couldn't load the data. Reload the page.",
          oficial: "Official", revisada: "Community · Reviewed ✓", sinRevisar: "Community · Not reviewed",
          aviso: "We haven't reviewed it yet: install it at your own risk.", deRepo: "In {x}",
          nadaFiltro: "No pieces match that filter.", aprobadas: "{n} approved by the community",
          aprobada: "Approved by the community ✓", sinRevisarApp: "Not reviewed yet", repo: "Code", pagina: "Website", copiado: "Copied ✓", seleccionado: "Selected: copy with Ctrl+C or ⌘C" },
  };
  const CATEGORIAS = {
    base: ["Base", "Base"], interfaz: ["Interfaz", "Interface"], ia: ["IA", "AI"], datos: ["Datos", "Data"], medios: ["Audio y video", "Audio and video"],
    conexiones: ["Conexiones", "Connections"], plataforma: ["Plataforma", "Platform"], repo: ["Repo y página", "Repo and page"],
  };
  const ORDEN = ["base", "ia", "interfaz", "plataforma", "datos", "medios", "conexiones", "repo"];
  const IAS = ["claude", "gemini", "codex", "claudeai", "otra"];
  const ES = {}, ES_ARIA = {};
  let idioma = "es", catalogo = null, proyectos = null, filtro = "todas";

  function leer(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento: igual funciona */ } }
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
    document.querySelectorAll("[data-t-aria]").forEach((n) => {
      const k = n.dataset.tAria;
      if (!(k in ES_ARIA)) ES_ARIA[k] = n.getAttribute("aria-label");
      n.setAttribute("aria-label", idioma === "en" && EN[k] ? EN[k] : ES_ARIA[k]);
    });
    const b = document.getElementById("idioma");
    b.textContent = idioma === "en" ? "ES" : "EN";
    b.lang = idioma === "en" ? "es" : "en";
    b.setAttribute("aria-label", idioma === "en" ? "Leer en español" : "Read in English");
    document.querySelectorAll('img[src^="sello"]').forEach((i) => { i.src = idioma === "en" ? "sello-en.svg" : "sello.svg"; i.alt = idioma === "en" ? "Made with Pieza" : "Hecho con Pieza"; });
    pintar();
  }

  /* ---------- Datos ---------- */
  // Solo rutas de íconos que arma pagina.py: "iconos/…/<nombre>.svg", sin subir de carpeta.
  const ICONO = /^iconos\/(piezas|proyectos)\/[A-Za-z0-9._-]+\.svg$/;
  const iconoValido = (r) => typeof r === "string" && ICONO.test(r) && !r.includes("..");
  function iconoMascara(ruta) {
    const s = el("span", "icono");
    s.setAttribute("aria-hidden", "true");
    if (iconoValido(ruta)) s.style.setProperty("--icono", 'url("' + ruta + '")');
    else s.classList.add("generico");
    return s;
  }
  function enlaceSeguro(u) { return typeof u === "string" && /^https:\/\//.test(u) ? u : ""; }

  function pintarProyectos() {
    const ul = document.getElementById("lista-proyectos");
    ul.replaceChildren();
    if (!proyectos) return;
    const lista = Array.isArray(proyectos.proyectos) ? proyectos.proyectos : [];
    document.getElementById("n-apps").textContent = String(proyectos.total || 0);
    const ap = document.getElementById("n-aprobadas");
    ap.textContent = lista.length ? t("aprobadas").replace("{n}", String(proyectos.aprobados || 0)) : "";
    if (!lista.length) {
      const li = el("li", "vacio");
      const s = el("span", "icono generico"); s.setAttribute("aria-hidden", "true");
      li.append(s, el("p", null, t("vacio")));
      ul.append(li);
    }
    for (const p of lista) {
      const li = el("li");
      const cab = el("div", "cabeza");
      const img = el("img", "icono-app");
      img.alt = ""; img.width = 40; img.height = 40;
      img.src = iconoValido(p.icono) ? p.icono : "favicon.svg";
      // «nombre» es solo el nombre; dueño/repo viene en «repo».
      const nombre = String(p.nombre || p.repo || "").split("/").pop();
      const repo = typeof p.repo === "string" && REPO.test(p.repo) ? "https://github.com/" + p.repo : "";
      const titulo = el("b", "nombre", nombre);
      cab.append(img, titulo);
      li.append(cab);
      if (p.descripcion) li.append(el("p", "desc", String(p.descripcion)));
      const rev = p.revision && p.revision.estado === "revisado";
      const pie = el("div", "pie-tarjeta");
      pie.append(el("span", "etiqueta " + (rev ? "revisada" : "sin-revisar"), rev ? t("aprobada") : t("sinRevisarApp")));
      if (p.familia) pie.append(el("span", "etiqueta", t("familia")));
      li.append(pie);
      const enl = el("p", "enlaces-app");
      if (repo) { const a = el("a", null, t("repo")); a.href = repo; enl.append(a); }
      // Su sitio web solo se enlaza cuando la app está revisada; si no, solo su repo.
      const pag = rev ? enlaceSeguro(p.pagina) : "";
      if (pag) { const a = el("a", null, t("pagina")); a.href = pag; enl.append(a); }
      if (enl.children.length) li.append(enl);
      ul.append(li);
    }
    const f = String(proyectos.actualizado || "").slice(0, 10);
    document.getElementById("actualizado").textContent = f ? t("actualizado").replace("{x}", f) : "";
  }

  // Revisión de una pieza: "oficial" (o sin campo), "revisada", "sin-revisar" o "rechazada" (no se muestra).
  function revision(p) {
    if (p.fuente !== "comunidad") return "oficial";
    const e = p.revision && p.revision.estado;
    return e === "revisada" || e === "rechazada" ? e : "sin-revisar";
  }
  const REPO = /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}$/;

  function pintarCatalogo() {
    const caja = document.getElementById("lista-catalogo");
    caja.replaceChildren();
    if (!catalogo) return;
    document.getElementById("n-piezas").textContent = String(catalogo.total);
    document.getElementById("n-listas").textContent = String(catalogo.listas);
    const yo = idioma === "en" ? 1 : 0;
    const visibles = (catalogo.piezas || []).filter((p) => {
      const r = revision(p);
      if (r === "rechazada") return false;
      if (filtro === "revisadas") return r !== "sin-revisar";
      if (filtro === "sin-revisar") return r === "sin-revisar";
      return true;
    });
    const cats = ORDEN.concat([...new Set(visibles.map((p) => p.categoria))].filter((c) => !ORDEN.includes(c)));
    for (const cat of cats) {
      const grupo = visibles.filter((p) => p.categoria === cat);
      if (!grupo.length) continue;
      const sec = el("div", "grupo");
      sec.append(el("h3", null, (CATEGORIAS[cat] || [cat, cat])[yo]));
      const ul = el("ul", "piezas");
      grupo.sort((a, b) => (a.estado === "lista" ? 0 : 1) - (b.estado === "lista" ? 0 : 1));
      for (const p of grupo) {
        const r = revision(p);
        const li = el("li");
        const cab = el("div", "cabeza");
        cab.append(iconoMascara(p.icono), el("b", null, p.nombre || p.id));
        const lista = (p.estado || "lista") === "lista";
        cab.append(el("span", "etiqueta" + (lista ? " lista" : ""), lista ? t("lista") + " · " + p.version : t("camino")));
        cab.append(el("span", "etiqueta " + r, r === "oficial" ? t("oficial") : r === "revisada" ? t("revisada") : t("sinRevisar")));
        li.append(cab, el("p", null, p.descripcion || ""));
        if (r !== "oficial" && typeof p.repo === "string" && REPO.test(p.repo)) {
          const a = el("a", "repo", t("deRepo").replace("{x}", p.repo));
          a.href = "https://github.com/" + p.repo;
          const pr = el("p"); pr.append(a); li.append(pr);
        }
        const datos = el("div", "datos");
        const permisos = Object.entries(p.permisos || {}).flatMap(([plat, l]) => (l || []).map((x) => plat + ": " + x.clave));
        datos.append(el("span", null, t("plataformas") + ": " + (p.plataformas || []).join(", ") + (p.siempre ? " · " + t("siempre") : "")));
        datos.append(el("span", null, t("permisos") + ": " + (permisos.length ? permisos.join("; ") : t("ninguno"))));
        datos.append(el("span", null, t("red") + ": " + ((p.red || []).length ? p.red.join(", ") : (p.red_nota || t("sinRed")))));
        li.append(datos);
        if (r === "sin-revisar") li.append(el("p", "aviso", t("aviso")));
        ul.append(li);
      }
      sec.append(ul);
      caja.append(sec);
    }
    if (!caja.children.length) caja.append(el("p", "vacio-filtro", t("nadaFiltro")));
  }

  function pintar() { pintarProyectos(); pintarCatalogo(); }

  async function cargar(nombre) {
    const r = await fetch("datos/" + nombre, { cache: "no-cache" });
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  }

  function iniciarFiltro() {
    const caja = document.getElementById("filtro-catalogo");
    caja.addEventListener("click", (ev) => {
      const b = ev.target.closest("button[data-filtro]");
      if (!b) return;
      filtro = b.dataset.filtro;
      caja.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      pintarCatalogo();
    });
  }

  /* ---------- Estrellas de la portada (canvas, se pausa fuera de pantalla y con la pestaña oculta) ---------- */
  function iniciarEstrellas() {
    const lienzo = document.getElementById("estrellas");
    const portada = document.getElementById("arriba");
    const ctx = lienzo.getContext("2d");
    if (!ctx) return;
    let ancho = 0, alto = 0, estrellas = [], visible = true, cuadro = 0, mx = 0, my = 0, px = 0, py = 0;
    const capas = [0.15, 0.35, 0.7];

    function medir() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      ancho = portada.clientWidth; alto = portada.clientHeight;
      lienzo.width = Math.round(ancho * dpr); lienzo.height = Math.round(alto * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.min(320, Math.round((ancho * alto) / 4200));
      estrellas = [];
      for (let i = 0; i < n; i++) {
        const capa = i % 3;
        estrellas.push({ x: Math.random() * ancho, y: Math.random() * alto, r: 0.5 + capa * 0.45 + Math.random() * 0.4,
          capa, fase: Math.random() * 6.28, vel: 0.4 + Math.random() * 1.2, ambar: Math.random() < 0.06 });
      }
      dibujar(performance.now());
    }

    function dibujar(ahora) {
      ctx.clearRect(0, 0, ancho, alto);
      const sy = Math.min(window.scrollY, alto);
      px += (mx - px) * 0.05; py += (my - py) * 0.05;
      for (const s of estrellas) {
        const k = capas[s.capa];
        let x = s.x - px * 18 * k + (quieto.matches ? 0 : ahora * 0.004 * k);
        let y = s.y - sy * k * 0.5 - py * 12 * k;
        x = ((x % ancho) + ancho) % ancho; y = ((y % alto) + alto) % alto;
        const brillo = quieto.matches ? 0.8 : 0.55 + 0.45 * Math.sin(ahora * 0.001 * s.vel + s.fase);
        ctx.globalAlpha = brillo * (0.45 + k * 0.6);
        ctx.fillStyle = s.ambar ? "#ffc65a" : "#ece8ff";
        ctx.fillRect(x, y, s.r, s.r);
      }
      ctx.globalAlpha = 1;
    }

    function bucle(ahora) {
      cuadro = 0;
      if (!visible || document.hidden || quieto.matches) return;
      dibujar(ahora);
      cuadro = requestAnimationFrame(bucle);
    }
    function seguir() { if (!cuadro && visible && !document.hidden && !quieto.matches) cuadro = requestAnimationFrame(bucle); }

    new IntersectionObserver((e) => {
      visible = e[0].isIntersecting;
      portada.classList.toggle("quieto", !visible);
      seguir();
    }).observe(portada);
    document.addEventListener("visibilitychange", seguir);
    window.addEventListener("pointermove", (e) => { mx = e.clientX / window.innerWidth - 0.5; my = e.clientY / window.innerHeight - 0.5; }, { passive: true });
    let espera = 0;
    window.addEventListener("resize", () => { clearTimeout(espera); espera = setTimeout(medir, 150); });
    quieto.addEventListener("change", () => { medir(); seguir(); });
    medir();
    seguir();
  }

  /* ---------- «Cómo funciona»: cada paso arma el rompecabezas al bajar ---------- */
  function iniciarRelato() {
    const tablero = document.getElementById("tablero");
    const relato = document.querySelector(".relato");
    const pasos = [...document.querySelectorAll(".pasos-relato li")];
    if (quieto.matches || !("IntersectionObserver" in window)) { relato.classList.add("sin-relato"); return; }
    relato.classList.add("relato-vivo");
    tablero.dataset.paso = "1";
    pasos[0].classList.add("activo");
    const obs = new IntersectionObserver((entradas) => {
      for (const e of entradas) {
        if (!e.isIntersecting) continue;
        pasos.forEach((p) => p.classList.toggle("activo", p === e.target));
        tablero.dataset.paso = e.target.dataset.paso;
      }
    }, { rootMargin: "-45% 0px -45% 0px" });
    pasos.forEach((p) => obs.observe(p));
  }

  /* ---------- Empezar: «¿Qué IA usas?» ---------- */
  function iniciarSelector() {
    const lista = document.getElementById("selector-ia");
    const botones = [...lista.querySelectorAll('[role="tab"]')];
    function elegir(ia, foco) {
      if (!IAS.includes(ia)) ia = "claude";
      for (const b of botones) {
        const si = b.dataset.ia === ia;
        b.setAttribute("aria-selected", String(si));
        b.tabIndex = si ? 0 : -1;
        document.getElementById(b.getAttribute("aria-controls")).hidden = !si;
        if (si && foco) b.focus();
      }
      guardar("ia", ia);
    }
    lista.addEventListener("click", (e) => { const b = e.target.closest('[role="tab"]'); if (b) elegir(b.dataset.ia); });
    lista.addEventListener("keydown", (e) => {
      const i = botones.indexOf(document.activeElement);
      if (i < 0) return;
      let j = null;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") j = (i + 1) % botones.length;
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") j = (i - 1 + botones.length) % botones.length;
      else if (e.key === "Home") j = 0;
      else if (e.key === "End") j = botones.length - 1;
      if (j == null) return;
      e.preventDefault();
      elegir(botones[j].dataset.ia, true);
    });
    const pedida = (new URLSearchParams(location.search).get("ia") || "").toLowerCase().replace(/[^a-z]/g, "");
    const alias = { claudecode: "claude", geminicli: "gemini", claudeia: "claudeai" };
    elegir(alias[pedida] || pedida || leer("ia") || "claude");

    document.querySelectorAll("[data-copiar]").forEach((b) => {
      b.addEventListener("click", async () => {
        const code = document.getElementById(b.dataset.copiar);
        const texto = code.textContent;
        let ok = false;
        try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(texto); ok = true; } } catch (e) { ok = false; }
        if (!ok) {
          const sel = window.getSelection(), r = document.createRange();
          r.selectNodeContents(code); sel.removeAllRanges(); sel.addRange(r);
        }
        const antes = b.dataset.t;
        b.removeAttribute("data-t");
        b.textContent = ok ? t("copiado") : t("seleccionado");
        b.classList.toggle("listo", ok);
        b.closest(".tres").classList.add("copiado");
        clearTimeout(b._espera);
        b._espera = setTimeout(() => { b.dataset.t = antes; b.classList.remove("listo"); b.textContent = idioma === "en" ? EN.copiar : ES.copiar || "Copiar"; }, 2400);
      });
    });
  }

  /* ---------- Manifiesto: las ideas se escriben al aparecer ---------- */
  function iniciarManifiesto() {
    const ideas = document.getElementById("ideas");
    if (quieto.matches || !("IntersectionObserver" in window)) return;
    ideas.classList.add("por-escribir");
    const obs = new IntersectionObserver((e) => {
      if (!e[0].isIntersecting) return;
      ideas.classList.add("escribiendo");
      ideas.classList.remove("por-escribir");
      obs.disconnect();
    }, { rootMargin: "0px 0px -20% 0px" });
    obs.observe(ideas);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const pedido = new URLSearchParams(location.search).get("lang");
    const inicial = pedido || leer("idioma") || ((navigator.language || "es").toLowerCase().startsWith("es") ? "es" : "en");
    document.getElementById("idioma").addEventListener("click", () => { const v = idioma === "en" ? "es" : "en"; guardar("idioma", v); aplicarIdioma(v); });
    aplicarIdioma(inicial);
    iniciarFiltro();
    iniciarSelector();
    iniciarRelato();
    iniciarManifiesto();
    iniciarEstrellas();
    Promise.allSettled([cargar("catalogo.json"), cargar("proyectos.json")]).then(([c, p]) => {
      if (c.status === "fulfilled") catalogo = c.value;
      if (p.status === "fulfilled") proyectos = p.value;
      if (!catalogo || !proyectos) document.getElementById("actualizado").textContent = t("sinDatos");
      pintar();
    });
  });
})();
