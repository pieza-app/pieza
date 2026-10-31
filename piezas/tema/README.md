# Pieza «tema» — sistema, claro u oscuro, con un solo juego de tokens

`ui/tema.css` define los colores de toda la interfaz como **tokens** en `:root`. Cada color se escribe una vez, como par
(`--fondo-claro`, `--fondo-oscuro`), y el token (`--fondo`) lo elige con `light-dark()` según `color-scheme`. `ui/tema.js` pone
`<html data-tema="claro|oscuro">` (o lo quita para seguir al sistema) y trae el selector «Apariencia» de Ajustes. Sin
dependencias; sin estilos ni código en línea.

```html
<link rel="stylesheet" href="tema.css">        <!-- primero -->
<link rel="stylesheet" href="componentes.css"> <!-- si usas la pieza componentes -->
<link rel="stylesheet" href="app.css">         <!-- después: aquí van tu acento y lo propio de tu app -->
<script src="tema.js"></script>
```
```css
/* app.css: tu acento (y, si quieres, tus neutros) redefiniendo los pares en :root. Nunca los tokens resueltos. */
:root { --acento-claro: #ad4f27; --acento-oscuro: #ec8d5e; --sobre-acento-oscuro: #111111; }
```
```js
const tema = PiezaTema.crear({ guardar: (v) => host.enviar("config", { tema: v }) });
tema.aplicar(tema.elegir({ config: E.config.tema }));         // ?tema=oscuro gana: vistas previas y capturas
ajustes += `<h3>Apariencia</h3>${tema.selectorHTML()}`;         // traducirDOM traduce las etiquetas
document.addEventListener("click", (ev) => { if (tema.manejarClic(ev)) return pintar(); });
```

| API | |
|---|---|
| `crear({guardar?, alCambiar?(resuelto, valor), documento?, ventana?})` | |
| `aplicar(valor)` | `"sistema"`, `"claro"` u `"oscuro"` (otro valor = sistema). Devuelve el que quedó. |
| `elegir({config, url?})` | `?tema=` > lo guardado > sistema. |
| `valor`, `resuelto()` | Lo elegido y cómo se ve ahora (`"claro"`/`"oscuro"`). |
| `selectorHTML()`, `manejarClic(ev)` | Tres botones `data-pz-tema` con `aria-pressed` (clase `.pz-seg`, de la pieza `componentes`). |
| `escuchar(fn)` | Avisa cuando el sistema cambia y está en «sistema» (para un lienzo o un SVG que pinta con colores fijos). |

## Los tokens (un nombre, un significado)

| Token | Qué es | Par que redefine la app |
|---|---|---|
| `--fondo` | fondo de la página | `--fondo-claro`, `--fondo-oscuro` |
| `--panel` | superficies: tarjetas, diálogos, campos | `--panel-claro/-oscuro` |
| `--panel-2` | fondo secundario: barra lateral, selector segmentado, zonas hundidas | `--panel-2-claro/-oscuro` |
| `--linea` | bordes y separadores | `--linea-claro/-oscuro` |
| `--texto` | texto principal | `--texto-claro/-oscuro` |
| `--texto-suave` | texto secundario (cumple AA sobre `--fondo`, `--panel` y `--panel-2`) | `--texto-suave-claro/-oscuro` |
| `--tenue` | decoración, deshabilitado. **Nunca texto que haya que leer** | `--tenue-claro/-oscuro` |
| `--acento`, `--sobre-acento` | el único color de acción, y el texto encima | `--acento-claro/-oscuro`, `--sobre-acento-claro/-oscuro` |
| `--rojo`, `--verde` | error/atrasado y listo/lo que entra (AA como texto) | `--rojo-claro/-oscuro`, `--verde-claro/-oscuro` |
| `--sombra` | sombra de lo que flota | `--sombra-claro/-oscuro` |
| `--hover`, `--acento-suave`, `--rojo-suave`, `--verde-suave`, `--velo` | derivados con `color-mix()`: **no se redefinen** | — |
| `--foco` | contorno de `:focus-visible` (= `--acento`) | — |
| `--radio`, `--radio-chico`, `--fuente`, `--mono` | forma y letra | se redefinen directo |

Además conecta las variables de la pieza `bienvenida` (`--bv-acento`, `--bv-linea`, `--bv-panel`, `--bv-texto-suave`): con `tema`
no hay que definirlas. En navegadores sin `light-dark()` (Safari < 17.5, Chrome < 123) un bloque `@supports not` elige los
mismos pares con `prefers-color-scheme`: nada que hacer en la app.

## Nombre viejo en cada app → token nuevo

| Hoy | Esquema | Graba | Corta | Repasa | Alcancía | Minuta |
|---|---|---|---|---|---|---|
| `--fondo` | `--fondo` | `--fondo` | `--fondo` | `--fondo` | `--fondo` | `--fondo` (del universo) |
| `--panel` | `--panel` | `--panel` | `--panel` | `--panel` | `--panel` | `--panel` (del universo) |
| `--suave` | **`--panel-2`** (es fondo) | `--texto-suave` | `--texto-suave` | `--texto-suave` | `--texto-suave` | `--texto-suave` |
| `--gris` | `--texto-suave` | — | — | — | — | — |
| `--borde` | `--linea` | — | — | — | — | — |
| `--linea` | — | `--linea` | `--linea` | `--linea` | `--linea` | `--linea` |
| `--lateral` | — | `--panel-2` | propio de Corta (más oscuro que el panel) | — | `--panel-2` | — |
| `--panel2` | — | — | `--panel-2` | — | — | — |
| `--papel` | — | — | — | propio de Repasa | — | — |
| `--tenue` | — | — | — | — | `--tenue` | — |
| `--hover` | `--hover` (derivado: borra el valor) | — | — | — | — | — |
| `--acento-suave`, `--rojo-suave`, `--verde-suave` | derivados: borra el valor | ídem | ídem | ídem | ídem | ídem |
| `--radio-c` | — | — | — | — | — | `--radio-chico` |
| `--mono` | `--mono` | — | — | — | — | — |
| `data-tema="claro\|oscuro"` | igual | (no tenía) | (no tenía) | (no tenía) | (no tenía) | `data-modo` → `data-tema` |

Lo que no está en la tabla es de la app y se queda en su `app.css` (Esquema `--lienzo`, `--punto`, `--d-*`; Corta `--corte`,
`--escenario`, `--violeta*`, `--azul*`; Repasa `--cuadricula`, `--destacador`, los colores de cada ramo; Alcancía `--barra-alto`;
Graba `html.vidrio`; Minuta `--fondo2`, `--acento2`, `--acento-t`, `--patron`). Si uno de ellos cambia con el modo, escríbelo
igual: `--lienzo: light-dark(#fbfcfd, #12171f)`.

## Los colores de cada app como pares

Para que cada app se vea igual que hoy, estos bloques van al comienzo de su `app.css` (en lugar de su `:root` y su bloque oscuro).
`pruebas/interfaz.mjs` lee esta sección y revisa el contraste AA de cada par (texto y texto suave sobre fondo, panel y panel 2;
acento sobre panel; texto sobre el acento; rojo y verde sobre fondo y panel). Graba y Repasa tenían rojo y verde bajo AA como
texto: aquí van con el mismo tono, un poco más oscuro.

```css
/* app: esquema */
:root { --texto-suave-claro: #596377; --rojo-claro: #c02b2b; --rojo-oscuro: #ff8080; --verde-claro: #1d7444; --linea-claro: #e2e6ec; --linea-oscuro: #273041; }
```
```css
/* app: graba */
:root {
  --fondo-claro: #f6f5f9; --fondo-oscuro: #121116; --panel-claro: #ffffff; --panel-oscuro: #1b1a21; --panel-2-claro: #efedf4; --panel-2-oscuro: #16151b;
  --linea-claro: #e3e0ea; --linea-oscuro: #2c2a35; --texto-claro: #17151c; --texto-oscuro: #f1eff6; --texto-suave-claro: #6b6876; --texto-suave-oscuro: #a19dae;
  --acento-claro: #5a48f5; --acento-oscuro: #8b7dff; --sobre-acento-oscuro: #111111;
  --rojo-claro: #d61e24; --rojo-oscuro: #e65156; --verde-claro: #247b53; --verde-oscuro: #2f9e6b;
  --sombra-claro: 0 1px 2px rgba(20, 16, 40, 0.06), 0 6px 20px rgba(20, 16, 40, 0.06); --sombra-oscuro: none;
}
```
```css
/* app: corta */
:root {
  --fondo-claro: #f3f3ef; --fondo-oscuro: #0d0e10; --panel-claro: #ffffff; --panel-oscuro: #16171a; --panel-2-claro: #f6f6f2; --panel-2-oscuro: #1d1f23;
  --linea-claro: #deded8; --linea-oscuro: #2a2c31; --texto-claro: #141518; --texto-oscuro: #f4f4f0; --texto-suave-claro: #63656d; --texto-suave-oscuro: #9a9ca3;
  --acento-claro: #4f7a00; --acento-oscuro: #c6f432; --sobre-acento-oscuro: #111214;
  --rojo-claro: #c93636; --rojo-oscuro: #ff6b6b; --verde-claro: #4f7a00; --verde-oscuro: #c6f432;
  --lateral: light-dark(#ebebe6, #121315);
}
```
```css
/* app: repasa */
:root {
  --fondo-claro: #f7f5ef; --fondo-oscuro: #12141b; --panel-claro: #ffffff; --panel-oscuro: #1d212c; --panel-2-claro: #fffefa; --panel-2-oscuro: #171a23;
  --linea-claro: #e6e2d6; --linea-oscuro: #2c3140; --texto-claro: #1d2333; --texto-oscuro: #f2f3f7; --texto-suave-claro: #646b7d; --texto-suave-oscuro: #a2a8b8;
  --acento-claro: #2f5bea; --acento-oscuro: #7c9bff; --sobre-acento-oscuro: #0e1220;
  --rojo-claro: #ce342c; --rojo-oscuro: #ff7b72; --verde-claro: #197f49; --verde-oscuro: #4cc98a; --radio: 18px;
}
```
```css
/* app: alcancia */
:root {
  --fondo-claro: #f5f4f2; --fondo-oscuro: #131211; --panel-claro: #ffffff; --panel-oscuro: #1c1a18; --panel-2-claro: #efedea; --panel-2-oscuro: #171615;
  --linea-claro: #e5e2de; --linea-oscuro: #2d2a27; --texto-claro: #1c1a18; --texto-oscuro: #f2efeb; --texto-suave-claro: #625c56; --texto-suave-oscuro: #aaa39c;
  --tenue-claro: #b3ada6; --tenue-oscuro: #57524d;
  --acento-claro: #ad4f27; --acento-oscuro: #ec8d5e; --sobre-acento-oscuro: #111111;
  --rojo-claro: #c0312a; --rojo-oscuro: #f2766e; --verde-claro: #1f7a49; --verde-oscuro: #55c38c;
}
```

## Pasar una app a esta pieza

En todas: `pieza.py agregar tema <app>`, `<link rel="stylesheet" href="tema.css">` antes de `app.css` en `ui/index.html`, cambiar su
`:root` y su `@media (prefers-color-scheme: dark)` por su bloque de arriba, y renombrar con la tabla (en `app.css` y en los
`var(--…)` de `app.js`; `sed -i 's/var(--suave)/var(--texto-suave)/g'` en todas menos Esquema). Borrar `html, body {background;
color}`, `:focus-visible` y `color-scheme`, que ya trae la pieza.

| App | Además (lo que no es mecánico) |
|---|---|
| Esquema | El orden importa: primero `--suave` → `--panel-2`, después `--gris` → `--texto-suave` (si no, se mezclan). `--borde` → `--linea`. Su `data-tema` ya es el mismo: cambia su `dataset.tema` a mano por `tema.aplicar(E.config.tema)` y el selector de Ajustes por `tema.selectorHTML()` (`data-tema` → `data-pz-tema`). Sus `--d-*` pasan a `light-dark()`. |
| Graba | `html.vidrio` redefine `--panel`, `--lateral` y `--linea` con transparencias: cámbialo a `--panel-2`/`--linea` y deja `--campo`/`--solido` como propios. Recién ahora puede ofrecer «Apariencia» (antes solo seguía al sistema): suma `tema` a `app.json` → `config`. |
| Corta | Era oscura por defecto y clara con `prefers-color-scheme: light`; con «sistema» se ve igual. Su `--lateral` queda propio (con `light-dark`). Suma «Apariencia» si quiere. |
| Repasa | `--papel` queda propio; el fondo cuadriculado sigue en `body`. El celular (`movil/`) usa la misma `ui/`: nada aparte. |
| Alcancía | `--barra-alto` queda propio; su `#toast` pasa a `--pz-toast-abajo: calc(var(--barra-alto) + 16px)` si usa `componentes`. |
| Minuta | Cada universo trae sus colores y su modo: al cargar un universo, `tema.aplicar(universo.modo)` (en vez de `dataset.modo`) y sus colores van **directo a los tokens** (`--fondo`, `--panel`, `--acento`…, ya resueltos para ese modo) en vez de los pares. `:root[data-modo="claro"]` → `:root[data-tema="claro"]`. No ofrece «Apariencia» (lo decide el universo). |
