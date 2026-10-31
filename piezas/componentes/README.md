# Pieza «componentes» — lo que todas las apps repetían en su interfaz

Diálogo accesible, confirmar, avisos en cola, las filas de «Tu IA», la fila de actualizaciones «Paso n de 3», «Acerca de» y el
formulario de comentarios que abre un issue en GitHub. `ui/componentes.js` devuelve HTML como texto (todo lo de afuera
escapado) y atiende sus clics y teclas; `ui/componentes.css` lo dibuja con los tokens de la pieza `tema`. Requiere `i18n` y
`tema`. Clases con prefijo `pz-` (no chocan con las de la app); sin estilos ni código en línea.

```html
<link rel="stylesheet" href="tema.css"><link rel="stylesheet" href="componentes.css"><link rel="stylesheet" href="app.css">
<script src="i18n.js"></script><script src="host.js"></script><script src="componentes.js"></script><script src="app.js"></script>
```
```js
const ui = PiezaComponentes.crear({
  i18n, host, app: "Ana", repo: "ana-app/ana", version: E.version,
  pintar,                                   // cuando cambia algo de la pieza (una IA probada, el avance de una actualización)
  cerrar: () => { E.ajustes = false; pintar(); },   // Esc, el velo o ✕ sobre un diálogo de la app
  retener: (...a) => bv.retener(...a),      // pieza bienvenida: los avisos esperan a que se elija el idioma
});
function pintar() {
  raiz.innerHTML = app() + (E.ajustes ? ui.dialogo({ id: "t-aj", titulo: "Ajustes", cuerpo: ajustes(),
    pie: `<button class="pz-boton pz-principal" data-pz-cerrar data-autofoco>Listo</button>` }) : "") + ui.capas();
  i18n.traducirDOM(raiz);
  ui.despuesDePintar();                     // foco al abrir, adentro mientras está abierto, de vuelta al cerrar
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
ui.aviso("Guardado");                       // frase en español (Tp la traduce) · ui.aviso(texto, { traducido: true }) · { error: true }
```

| API | |
|---|---|
| `crear({i18n, host?, app, repo?, version?, pintar?, cerrar?, retener?, elegirIA?, documento?, duracion?, pausa?})` | `elegirIA(id)`: qué hacer cuando una IA prueba bien (por defecto `host.enviar("config", {ia})`). |
| `dialogo({id, titulo, valores?, cuerpo, pie?, clase?, cerrable?, sinEsc?})` | `role="dialog"`, `aria-modal`, `aria-labelledby`; `titulo` es una frase en español con `{marcadores}` (va por `T`); `cuerpo` y `pie` los armas tú con `esc()`. `clase: "pz-ancho"` para uno ancho; `cerrable: false` sin ✕; `sinEsc: true` para uno que no se cierra solo. |
| `confirmar({titulo, texto?, valores?, si?, no?, peligro?})` | Promesa: `true` (sí) o `false` (no, Esc, el velo). Se pinta con `capas()`. |
| `capas()` | Lo que la pieza pinta arriba de todo (confirmar, comentarios): al final de cada pintada. |
| `despuesDePintar()`, `manejarClic(ev)`, `manejarTecla(ev)` | Foco, Tab que no se escapa del diálogo de más arriba, Esc. Devuelven `true` si era de la pieza. |
| `aviso(frase, {valores?, traducido?, error?, duracion?})` | Cola: uno a la vez, sin repetir el que está o espera, máximo 4 esperando; dura según el largo (los errores, más). Usa `#toast` si existe o crea `#pz-toast` (`role="status"`, `aria-live`). |
| `filasIA({ias, elegida, guia?})`, `probarIA(id)`, `iaProbada(r)` | `[data-pz-probar-ia]` manda `probarIA {ia}`; `iaProbada` acepta `{ia, ok, plantilla, valores, ayuda}` (y `{id}` de antes) y muestra el error traducido. |
| `filaActualizacion()`, `actualizacionRevisada(r)`, `actualizacionDisponible(r)`, `actualizacionProgreso(a)` | La forma de la pieza `actualizaciones` (`texto` + `valores`, `paso`, `total`, `pct`), con barra de avance. |
| `acercaDe({version, licencia?, enlaces: {sitio, codigo, comunidad, aportar}})` | Solo enlaces https (`[data-pz-enlace]` → `abrirEnlace {url}`); con `repo`, el botón «Enviar comentarios». |
| `abrirComentarios({tipo})`, `datosComentario()`; `urlIssue(repo, {titulo, cuerpo, etiqueta})`, `sistemaDe(plataforma, navigator)` | Formulario (algo falla, una idea, otro) que abre `github.com/<repo>/issues/new` prellenado en el navegador. Con la casilla marcada suma versión, idioma y sistema; nunca nada de la persona. |
| `crearAvisos(...)`, `esc(v)` | Por si los necesitas sueltos. |

**Textos:** las frases fijas salen en español y las traduce `traducirDOM` con el resto de la app (así sus pruebas de «ningún texto
sin traducir» las cuentan); las que llevan valores salen ya traducidas dentro de `data-sin-traducir`. Todas tienen su inglés en
`textos` del `pieza.json` (`pieza.py agregar` las suma al `en.json` de la app).

**Accesible:** el foco entra al diálogo (`[data-autofoco]`, si no el primer control, si no el título), Tab y Mayús+Tab dan la vuelta
adentro, Esc y el velo cierran lo de más arriba y el foco vuelve al botón que lo abrió (se recuerda por su `id` o su primer
`data-*`, porque la app vuelve a pintar todo). Botones de 44 px en pantallas táctiles y a 760 px o menos (ahí los diálogos salen
desde abajo); sin animaciones con `prefers-reduced-motion`.

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
| Esquema | Es la base: su `.capa-idioma` es de la bienvenida y se queda. `confirmar-si/no` y `E.confirmar` pasan a `await ui.confirmar`. `filasIA` elegía la IA al tocar «Usar y probar»; con la pieza se elige recién cuando la prueba sale bien. `actualizacionRevisada` usaba `detalle`: ahora `notas` (como manda la pieza `actualizaciones`). |
| Graba | Sus diálogos llevan `html.vidrio` (fondo translúcido): agrega `html.vidrio .pz-dialogo { … }` en su `app.css`. |
| Corta | Su aviso de error de actualización (`toast(r.texto)`) ya lo hace la pieza: bórralo. |
| Repasa | `mantener()` es su `pintar` (conserva el scroll): pásalo como `pintar`. Sus botones más grandes (para niños) quedan en su `app.css` sobre `.pz-boton`. Sus teclas 1–5 del repaso van después de `ui.manejarTecla`. |
| Alcancía | `--pz-toast-abajo: calc(var(--barra-alto) + 16px)` en celular. En `LECTURA` (celular) no pintes `filasIA` ni `filaActualizacion`. Su `aviso-regla` es propio y se queda. |
| Minuta | No usa `.capa`/`.dialogo`: sus ventanas son `.galeria`/`.galeria-caja` con `role="dialog"` **sin** `aria-modal`. Para que el foco y Esc funcionen, agrega `aria-modal="true"` (o pásalas a `ui.dialogo`). `.boton` en Minuta es un botón de ícono de 34 px: no lo renombres a `.pz-boton` sin revisar cada uno. Su formulario de comentarios publica también con la cuenta de GitHub del respaldo (`comentarios` con `directo`): eso queda en Minuta hasta la pieza `comentarios`; la parte «Abrir en GitHub» pasa a `ui.abrirComentarios`. |
