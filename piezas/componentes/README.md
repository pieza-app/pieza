# Pieza «componentes» — lo que todas las apps repetían en su interfaz

Diálogo accesible (también uno armado por la app, con `envolver`), confirmar, avisos en cola (también con un botón), las filas de «Tu IA», la fila de actualizaciones «Paso n de 3», «Acerca de» y el
formulario de comentarios que abre un issue en GitHub. `ui/componentes.js` devuelve HTML como texto (todo lo de afuera
escapado) y atiende sus clics y teclas; `ui/componentes.css` lo dibuja con los tokens de la pieza `tema`. Requiere `i18n` y
`tema`. Clases con prefijo `pz-` (no chocan con las de la app); sin estilos ni código en línea.

```html
<link rel="stylesheet" href="tema.css"><link rel="stylesheet" href="componentes.css"><link rel="stylesheet" href="app.css">
<div id="toast" class="pz-toast" role="status" aria-live="polite" data-sin-traducir></div>   <!-- opcional; ver «Avisos» -->
<script src="i18n.js"></script><script src="host.js"></script><script src="componentes.js"></script><script src="app.js"></script>
```
```js
const ui = PiezaComponentes.crear({
  i18n, host, app: "Ana", repo: "ana-app/ana", version: () => E.version,   // una función si la versión llega después
  pintar,                                   // cuando cambia algo de la pieza (una IA probada, el avance de una actualización)
  cerrar: () => { E.ajustes = false; pintar(); },   // Esc, el velo o ✕ sobre un diálogo de la app
  retener: (...a) => bv.retener(...a),      // pieza bienvenida: los avisos esperan a que se elija el idioma
});
function pintar() {
  raiz.innerHTML = app() + (E.ajustes ? ui.dialogo({ id: "t-aj", titulo: "Ajustes", cuerpo: ajustes(),
    pie: `<button class="pz-boton pz-principal" data-pz-cerrar>Listo</button>` }) : "") + ui.capas();
  i18n.traducirDOM(raiz);
  ui.despuesDePintar();                     // foco al título al abrir, donde estaba si repintas, de vuelta al cerrar
}
const ajustes = () => `<h3>Tu IA</h3>${ui.filasIA({ ias: E.ias, elegida: E.config.ia, guia: "https://ana-app.github.io/ana/ia.html" })}
  <h3>Actualizaciones</h3>${ui.filaActualizacion()}<h3>Acerca de</h3>${ui.acercaDe({ version: E.version, enlaces: { codigo: "https://github.com/ana-app/ana" } })}`;
document.addEventListener("click", (ev) => { if (ui.manejarClic(ev)) return; /* … */ });
document.addEventListener("keydown", (ev) => { if (ui.manejarTecla(ev)) return; /* … */ });
host.responder({
  iaProbada: (r) => ui.iaProbada(r),
  actualizacionRevisada: (r) => ui.actualizacionRevisada(r),
  actualizacionProgreso: (a) => ui.actualizacionProgreso(a),
  estado(e) { ui.actualizacionDisponible(e.actualizacion); /* … */ },
});
if (await ui.confirmar({ titulo: "¿Borrar «{x}»?", valores: { x: nota.titulo }, texto: "No se puede deshacer.", si: "Borrar", peligro: true })) borrar();
ui.aviso("Guardado");                       // frase en español · ui.aviso("Quedan 3 días") ya armada · { traducido: true } · { error: true }
ui.aviso("Borré «{x}»", { valores: { x: nota.titulo }, accion: { texto: "Deshacer", f: deshacer } });
const html = ui.envolver(`<h2 id="t-exportar">Exportar</h2>${cuerpo}`, { id: "t-exportar" });   // tu diálogo, con su propio <h2>
```

| API | |
|---|---|
| `crear({i18n, host?, app, repo?, version?, pintar?, cerrar?, retener?, elegirIA?, mantenerCampos?, documento?, duracion?, pausa?})` | `elegirIA(id)`: qué hacer cuando una IA prueba bien (por defecto `host.enviar("config", {ia})`). `mantenerCampos: true`: si la app vuelve a pintar mientras se escribe en un campo **fuera** de un diálogo (un buscador), el foco y el cursor vuelven a ese campo (necesita `id` o un `data-*` para reconocerlo). |
| `dialogo({id, titulo?, tituloHTML?, valores?, antes?, cuerpo, pie?, clase?, claseCapa?, claseTitulo?, cerrable?, sinEsc?, clave?})` | `role="dialog"`, `aria-modal`, `aria-labelledby`; `titulo` es una frase en español con `{marcadores}` (va por `T`); `tituloHTML`, un título que armaste tú con `esc()` (bilingüe, sin traducir); sin ninguno, no hay cabecera y el título lo pones en `cuerpo` con ese `id`. `antes`: HTML antes del título (los puntos de una bienvenida). `cuerpo` y `pie` los armas tú con `esc()`. `clase: "pz-ancho"` para uno ancho (va en la caja); `claseCapa`, en el velo; `claseTitulo`, en el `<h2>` (con `titulo` o `tituloHTML`); `cerrable: false` sin ✕; `sinEsc: true` para uno que no se cierra solo; `clave` distingue pasos con el mismo título (el foco va al título al cambiar de paso). |
| `envolver(html, {id, clase?, claseCapa?, sinEsc?, clave?, cerrable?})` | Tu diálogo entero (con su `<h2 id>`) dentro de la capa y la caja accesible: foco, Tab, Esc y velo de la pieza. `clase` va en la caja y `claseCapa` en el velo. Sin ✕ salvo `cerrable: true`. |
| `confirmar({titulo, texto?, valores?, si?, no?, peligro?, sinElegir?})` | Promesa: `true` (sí) o `false` (no). **Esc y el velo cuentan como «no»**; si necesitas distinguirlos («Guardar / No guardar / Cancelar»), `sinElegir: null` hace que devuelvan `null`. Sin `peligro` el foco empieza en el título, como en todo diálogo (el lector anuncia la pregunta; un Enter apurado no elige nada); con `peligro`, en «Cancelar». Se pinta con `capas()`. |
| `capas()` | Lo que la pieza pinta arriba de todo (confirmar, comentarios): al final de cada pintada. |
| `despuesDePintar()`, `manejarClic(ev)`, `manejarTecla(ev)` | Foco, Tab que no se escapa del diálogo de más arriba, Esc. Devuelven `true` si era de la pieza. |
| `aviso(frase, {valores?, traducido?, error?, duracion?, accion?})` | Cola: uno a la vez, sin repetir el que está o espera, máximo 4 esperando; dura según el largo (los errores, más). `frase` en español: con `valores` va por `Tp`; sin ellos, por `tr` (así sirve una frase ya armada, «Quedan 3 días»); `traducido: true` si ya viene en el idioma de la persona. `accion: {texto, f}` suma un botón (Deshacer, Revisar…): dura al menos 6 s, tocarlo corre `f` y cierra; `ui.avisos.accionar()` lo toca desde un atajo de la app. |
| `filasIA({ias, elegida, guia?, principal?})`, `probarIA(id)`, `iaProbada(r)` | `ias: [{id, nombre, instalada, detalle?, revisable?}]`; `detalle` (frase en español) dice por qué no está lista. Una no instalada trae «Revisar de nuevo» (se instaló después, o el teléfono ya bajó su modelo), salvo con `revisable: false` (una que todavía no existe: «Muy pronto» en `detalle`). `principal`: `"una"` (por defecto: solo la primera instalada, y ninguna si hay una en uso: un solo color de acción por pantalla), `"todas"` o `false`. `[data-pz-probar-ia]` manda `probarIA {ia}`; `iaProbada` acepta `{ia, ok, plantilla, valores, ayuda}` (y `{id}` de antes) y muestra el error traducido (sin la `ayuda` de la app: la fila ya está en «Tu IA»). |
| `filaActualizacion()`, `actualizacionRevisada(r, {pintar?})`, `actualizacionDisponible(r, {pintar?})`, `actualizacionProgreso(a)` | La forma de la pieza `actualizaciones` (`texto` + `valores`, `notas` —o `detalle`, de antes—, `paso`, `total`, `pct`), con barra de avance. Solo `desarrollo: true`: «Hay cambios nuevos en el código de {app}» con los commits (un `hay` sin versión sigue siendo «Hay una versión nueva»). `{pintar: false}` solo lo anota (p. ej. mientras está la pantalla del idioma). |
| `acercaDe({version?, licencia?, enlaces: {sitio, codigo, comunidad, aportar}, extra?: [{texto, url}]})` | Solo enlaces https (`[data-pz-enlace]` → `abrirEnlace {url}`); `extra` suma los de la app (texto en español, se traduce con el resto); con `repo`, el botón «Enviar comentarios». `version` por defecto, la de `crear`. |
| `abrirComentarios({tipo})`, `datosComentario()`; `urlIssue(repo, {titulo, cuerpo, etiqueta})`, `sistemaDe(plataforma, navigator)` | Formulario (algo falla, una idea, otro) que abre `github.com/<repo>/issues/new` prellenado en el navegador. Con la casilla marcada suma versión, idioma y sistema; nunca nada de la persona. |
| `crearAvisos(...)`, `esc(v)` | Por si los necesitas sueltos. |

**Textos:** las frases fijas salen en español y las traduce `traducirDOM` con el resto de la app (así sus pruebas de «ningún texto
sin traducir» las cuentan); las que llevan valores salen ya traducidas dentro de `data-sin-traducir`. Todas tienen su inglés en
`textos` del `pieza.json` (`pieza.py agregar` las suma al `en.json` de la app).

**Accesible:** al abrir, el foco va al **título** del diálogo (el lector de pantalla lo anuncia y nada se desplaza; con
`[data-autofoco]` en un campo, a ese campo, con el cursor al final). Si la app vuelve a pintar con el diálogo abierto, el foco vuelve al
control donde estaba (en un campo, con el cursor donde estaba, o al final); si cambia de paso (`clave`), al título nuevo. Fuera de
un diálogo, lo mismo con `crear({mantenerCampos: true})`, solo si la pintada se llevó el campo (si la persona salió de él, no se
vuelve). El título enfocado no lleva anillo en ninguna ventana `aria-modal`, sea de la pieza o de la app. Tab y Mayús+Tab dan la vuelta adentro, Esc y el velo cierran lo de más
arriba y el foco vuelve al botón que lo abrió (se recuerda por su `id` o su primer `data-*`, porque la app vuelve a pintar todo).
Sin animaciones con `prefers-reduced-motion`.

**Lo que se toca:** `--pz-boton-alto` (36 px), `--pz-chip-alto` (32 px, chips y selector) y `--pz-tactil` (44 px). En pantallas
táctiles y a 760 px o menos los dos primeros pasan a `--pz-tactil` **dentro de los componentes de la pieza** (diálogos, filas de
Ajustes `.pz-filas`, avisos y los chips de «Acerca de»); en el resto de tu app quedan como los dejes (un editor compacto no crece
solo). Para que todo crezca en táctil: `@media (pointer: coarse), (max-width: 760px) { :root { --pz-boton-alto: var(--pz-tactil);
--pz-chip-alto: var(--pz-tactil); } }` en tu `app.css`. La ✕ de un diálogo nunca baja de 36 px (`--pz-cerrar-ancho` la fija), aunque
pongas `--pz-boton-alto: 0` para medir tus botones a mano. Para botones de 44 px también en escritorio: `:root { --pz-boton-alto: 44px; }` en tu `app.css` (nunca `min-height` sobre `.pz-boton`, que pisaría
lo de los diálogos); para unos más grandes en táctil (niños): `:root { --pz-tactil: 48px; }`. Las reglas sobre elementos (`p`,
`h2` de un diálogo) van con `:where()`: cualquier clase tuya les gana. Un botón con texto largo se parte en dos líneas; el
selector `.pz-seg` no se parte (se parte el texto de cada opción) y su riel se ve sobre `--panel` y sobre `--panel-2`.

**Avisos:** si tienes `#toast` en `index.html`, ponle `class="pz-toast"` y `data-sin-traducir` desde el inicio (la pieza igual se
los pone al crearse): sin la clase se ve una caja vacía hasta el primer aviso, y sin `data-sin-traducir` `traducirDOM` lo vuelve a
traducir. Sin `#toast`, la pieza crea `#pz-toast`. Usan `--texto`/`--sobre-texto` y `--rojo`/`--sobre-rojo`: se leen aunque tu
`--fondo` o `--panel` sean transparentes.

## El marco y las superficies (0.4.0)

El estilo de Pieza para cualquier app: una barra lateral oscura y el contenido al lado. Necesita `tema` 0.4.0.

```html
<div class="pz-marco">
  <nav class="pz-lateral" aria-label="Principal">
    <button class="pz-marca"><img src="logo.svg" alt="">Mi app</button>
    <button class="pz-boton pz-principal">+ Nueva</button>
    <p class="pz-lateral-titulo">Tus cosas</p>
    <button class="pz-lateral-enlace pz-solo-ancho" aria-current="page">Inicio <small>3</small></button>
    <div class="pz-lateral-pie"><button class="pz-lateral-enlace">Ajustes</button></div>
  </nav>
  <main class="pz-contenido"><h1>Título</h1>…</main>
</div>
```

| Clase | Qué es |
|---|---|
| `.pz-marco`, `.pz-lateral`, `.pz-contenido` | El marco. A 760 px o menos la barra queda arriba en una fila; lo marcado `.pz-solo-ancho` y los `.pz-lateral-titulo` se ocultan. `--pz-lateral-ancho` (240 px) la ensancha. |
| `.pz-marca`, `.pz-lateral-titulo`, `.pz-lateral-enlace`, `.pz-lateral-pie` | Logo y nombre, títulos de grupo, enlaces (la sección actual con `aria-current`, con su número en `<small>`) y lo de abajo (Tu IA, Ajustes). |
| `.pz-tarjeta`, `.pz-tarjetas` | Una superficie con borde y su grilla (`ul`). |
| `.pz-cifras`, `.pz-cifra` | Cifras grandes con su etiqueta: `<p class="pz-cifra"><b>12</b><small>pasos</small></p>`. |
| `.pz-oscuro` | Un panel oscuro para lo que pasa en vivo o lo que destaca (su `<b>` va en el acento). |
| `.pz-zona-oscura` | Para la barra propia de una app: oscura en los dos modos. Con `color-scheme: dark`, los tokens de adentro se resuelven en oscuro y `--fondo`/`--panel` pasan a los de la barra lateral: lo de adentro se ve bien sin reglas propias. |
| `.pz-etapas` | Los pasos de un proceso: `li.pz-hecha`, `li.pz-actual` (con `aria-current="step"`), cada uno con su número en un `<span>`. |
| `.pz-dos-columnas`, `.pz-columna-lado` | Lo principal y un panel al lado; abajo cuando no cabe. |

## Pasar una app a esta pieza

En todas: `pieza.py agregar componentes <app>` (trae `i18n` y `tema`), los `<link>`/`<script>` de arriba, y cambiar:

| Hoy (en cada app) | Con la pieza |
|---|---|
| `function toast(t)` + `#toast` en `index.html` | `const toast = (t, o) => ui.aviso(t, o)`; deja `#toast` (la pieza lo usa) y borra su CSS (`#toast`, `#toast.visible`) |
| `<div class="capa"><div class="dialogo" role="dialog" …>` armado a mano | `ui.dialogo({id, titulo, cuerpo, pie})` |
| `.pie-dialogo`, `.boton`, `.boton.principal`, `.boton.plano`, `.boton.peligro` | `.pz-pie`, `.pz-boton`, `.pz-boton.pz-principal`, `.pz-plano`, `.pz-peligro` |
| `.fila` / `.txt` de Ajustes, `.seg`, `.chip(s)`, `.giro`, `.ok`, `.mal-txt`/`.error-txt` | `.pz-fila` / `.pz-txt`, `.pz-seg`, `.pz-chip(s)`, `.pz-giro`, `.pz-ok`, `.pz-error-texto` |
| `filasIA()`, `E.probando`, `E.resultadoIA`, `data-probar(-ia)` | `ui.filasIA({ias: E.ias, elegida: E.config.ia})`; `iaProbada: (r) => ui.iaProbada(r)` |
| `filaActualizacion()`, `E.revisando`/`E.buscando`/`E.act`, `data-accion="buscar-actualizacion"`/`"actualizar"` | `ui.filaActualizacion()` + las tres respuestas de arriba |
| `E.confirmar` + su diálogo | `await ui.confirmar({…})` |
| Esc que cierra a mano el diálogo abierto | `ui.manejarTecla(ev)` + `cerrar` en `crear` |

| App | Además (lo que no es mecánico) |
|---|---|
| Esquema | Sus ~30 diálogos con su propio `<h2>` pasan a `ui.envolver(html, {id})`. Es la base: su `.capa-idioma` es de la bienvenida y se queda. `confirmar-si/no` y `E.confirmar` pasan a `await ui.confirmar`. `filasIA` elegía la IA al tocar «Usar y probar»; con la pieza se elige recién cuando la prueba sale bien. `actualizacionRevisada` usaba `detalle`: ahora `notas` (como manda la pieza `actualizaciones`). |
| Graba | Sus diálogos llevan `html.vidrio` (fondo translúcido): agrega `html.vidrio .pz-dialogo { … }` en su `app.css`. |
| Corta | Su aviso de error de actualización (`toast(r.texto)`) ya lo hace la pieza: bórralo. |
| Repasa | `mantener()` es su `pintar` (conserva el scroll): pásalo como `pintar`. Sus botones más grandes (para niños) quedan en su `app.css` sobre `.pz-boton`. Sus teclas 1–5 del repaso van después de `ui.manejarTecla`. |
| Alcancía | `--pz-toast-abajo: calc(var(--barra-alto) + 16px)` en celular. En `LECTURA` (celular) no pintes `filasIA` ni `filaActualizacion`. Su `aviso-regla` es propio y se queda. |
| Minuta | No usa `.capa`/`.dialogo`: sus ventanas son `.galeria`/`.galeria-caja` con `role="dialog"` **sin** `aria-modal`. Para que el foco y Esc funcionen, agrega `aria-modal="true"` (o pásalas a `ui.dialogo`). `.boton` en Minuta es un botón de ícono de 34 px: no lo renombres a `.pz-boton` sin revisar cada uno. Su formulario de comentarios publica también con la cuenta de GitHub del respaldo (`comentarios` con `directo`): eso queda en Minuta hasta la pieza `comentarios`; la parte «Abrir en GitHub» pasa a `ui.abrirComentarios`. |

## Si venías de 0.2.0

| Qué cambió | Qué hacer en la app |
|---|---|
| En táctil / ≤760 px, `--pz-tactil` sube solo los componentes de la pieza (diálogos, `.pz-filas`, avisos), no `:root` | Si contrarrestabas el `:root` de la pieza para un editor compacto (Corta), bórralo. Si querías que todos tus `.pz-boton` crecieran, pon la regla `:root` de «Lo que se toca» en tu `app.css`. |
| `confirmar` sin `peligro` enfoca el título (antes «sí») | Si tus pruebas esperaban el foco en `[data-pz-confirmar="si"]`, ajústalas: Enter ya no confirma, Tab llega a los botones. |
| `filaActualizacion`: solo `desarrollo: true` es una instalación de desarrollo | Si tu app manda los commits nuevos de un checkout, agrega `desarrollo: true` a lo que pasas a `actualizacionRevisada`/`actualizacionDisponible`. |
| El error de `iaProbada` no muestra la `ayuda` | Nada (borra lo que la quitara a mano). |
| El título de tus ventanas `aria-modal` sin anillo; `.pz-cerrar` con ancho mínimo propio | Borra lo que lo arreglaba en tu `app.css`. |
| Cursor donde estaba al repintar; `mantenerCampos` | Si guardabas y devolvías el cursor de un campo a mano, bórralo (fuera de un diálogo, `crear({mantenerCampos: true})`). |
| `revisable: false`, `claseTitulo`, `claseCapa` | Si armabas la fila de una IA «muy pronto» o un diálogo a mano solo para poner una clase al título o al velo, pasa a estas opciones. |

## Si venías de 0.1.0

| Qué cambió | Qué hacer en la app |
|---|---|
| `confirmar({peligro})` enfoca «Cancelar» | Nada (si tus pruebas esperaban el foco en «sí» con `peligro`, ajústalas). Esc sigue siendo «no»; `sinElegir: null` si necesitas distinguirlo. |
| Al abrir, el foco va al título (antes: `[data-autofoco]` o el primer control) | Quita `data-autofoco` de los botones del pie que lo tenían solo para que el foco entrara; déjalo en un campo donde se escribe. |
| `filasIA`: un solo botón principal | Si querías la forma de antes, `principal: "todas"`. Una no instalada ahora tiene «Revisar de nuevo»; si armabas tus filas para mostrar `detalle` o reintentar (Repasa en el celular), usa `ui.filasIA`. |
| Alto de lo que se toca con variables | Cambia tus `min-height: 44px` sobre `.pz-boton`, `.pz-chip` o `.pz-seg button` por `--pz-boton-alto` / `--pz-tactil` en `:root`. Borra lo que ponías para que `.pz-boton` partiera el texto o `.pz-seg` no se partiera (`.barra .pz-seg { flex-wrap: nowrap }`). |
| `.pz-dialogo p` → solo los `p` directos y con `:where()` | Borra lo que corregía el margen o el gris de tus `<p>` dentro de un diálogo y el color de `.pz-error-texto`. |
| Aviso y botón de peligro con `--sobre-texto` / `--sobre-rojo` | Requiere `tema` 0.2.0. Borra lo que arreglaba su texto con fondos transparentes (`html.vidrio .pz-toast`). |
| `envolver`, `dialogo({antes, tituloHTML})`, sin título | Si armabas la capa a mano para tener tu `<h2>`, los puntos antes del título o un título bilingüe, pásalos a estas formas. |
| `ui.aviso` sin `valores` va por `tr` | Si tenías tu `toast(t)` que llamaba `tr` antes de `ui.aviso(…, {traducido: true})` (Minuta), basta `ui.aviso(t)`. |
| `actualizacionRevisada`/`Disponible` con `detalle` y `{pintar: false}` | Borra tu `conNotas` (Repasa, Esquema) y lo que hacías para no pintar detrás de la pantalla del idioma (Corta). |
| `crear({version: () => …})`, `acercaDe({extra})` | Si recreabas `ui` al llegar la versión o armabas tus propios enlaces en «Acerca de», ya no hace falta. |

Lo que pidió Minuta para publicar comentarios directo con la cuenta de GitHub del respaldo queda para la pieza `comentarios`.
