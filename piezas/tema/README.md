# Pieza «tema» — sistema, claro, oscuro o vidrio, con un solo juego de tokens

`ui/tema.css` define los colores de toda la interfaz como **tokens** en `:root`. Cada color se escribe una vez, como par
(`--fondo-claro`, `--fondo-oscuro`), y el token (`--fondo`) lo elige con `light-dark()` según `color-scheme`. `ui/tema.js` pone
`<html data-pz-modo="claro|oscuro">` (o lo quita para seguir al sistema) y trae el selector «Apariencia» de Ajustes. El atributo
lleva prefijo: un `data-tema` de la app (en una tarjeta, en un universo) nunca choca con el de la pieza. Sin
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
| `crear({guardar?, alCambiar?(resuelto, valor), documento?, ventana?})` | `alCambiar` avisa cada vez que se aplica (para lo que la app pinta con colores fijos). |
| `aplicar(valor)` | `"sistema"`, `"claro"` u `"oscuro"` (otro valor = sistema). Devuelve el que quedó. |
| `elegir({config, url?})` | `?tema=` > lo guardado > sistema. |
| `valor`, `resuelto()` | Lo elegido y cómo se ve ahora (`"claro"`/`"oscuro"`). Así se lee el tema desde la app: no leas el atributo de `<html>`. |
| `ATRIBUTO` | `"data-pz-modo"`: para el CSS propio que cambia con el modo elegido (`:root[data-pz-modo="oscuro"] .x { … }`). |
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
| `--sobre-rojo` | texto sobre `--rojo` (botón de peligro, aviso de error). Sólido: nunca `--panel`, que una app puede hacer transparente | `--sobre-rojo-claro/-oscuro` |
| `--sobre-texto` | texto sobre `--texto` (el aviso). Sólido, por lo mismo | `--sobre-texto-claro/-oscuro` |
| `--sombra` | sombra de lo que flota. **No** va con `light-dark()` (solo acepta colores: con una sombra entera queda en `none`); la pieza la elige por modo con selectores | `--sombra-claro/-oscuro` (sombras enteras; `none` vale) |
| `--hover`, `--acento-suave`, `--rojo-suave`, `--verde-suave`, `--velo` | derivados con `color-mix()`: **no se redefinen** | — |
| `--foco` | contorno de `:focus-visible` (= `--acento`) | — |
| `--radio`, `--radio-chico`, `--fuente`, `--mono` | forma y letra | se redefinen directo |

Además conecta las variables de la pieza `bienvenida` (`--bv-acento`, `--bv-linea`, `--bv-panel`, `--bv-texto-suave`): con `tema`
no hay que definirlas. En navegadores sin `light-dark()` (Safari < 17.5, Chrome < 123) un bloque `@supports not` elige los
mismos pares con `prefers-color-scheme`: nada que hacer en la app con los tokens de la pieza. **Un token propio** que escribas con
`light-dark()` (`--lienzo: light-dark(#fbfcfd, #12171f)`) no tiene ese respaldo: en esos navegadores queda sin valor. Si importa,
repítelo como en `tema.css`: el claro en `:root`, el oscuro en `@media (prefers-color-scheme: dark) { :root:not([data-pz-modo="claro"]) }`
y en `:root[data-pz-modo="oscuro"]`, dentro de `@supports not (color: light-dark(#000, #fff))`. Y `light-dark()` nunca con algo
que no sea un color (sombras, tamaños): para eso, los mismos selectores.

**La ventana nativa** (barra de título, menús, el fondo mientras carga) sigue al sistema aunque se elija claro u oscuro: que la
siga a la apariencia elegida (`NSWindow.appearance` en Mac, `nativeTheme.themeSource` en Electron) queda para las piezas
`host-mac` y `host-escritorio` (ver `docs/catalogo.md`). Mientras, la app puede hacerlo con `alCambiar`.

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
| `data-tema="claro\|oscuro"` (en `<html>`) | `data-pz-modo` | (no tenía) | (no tenía) | (no tenía) | (no tenía) | `data-modo` → `data-pz-modo` |

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

En todas: `pieza.py agregar tema <app>` (`--sin-config=tema` si la app no ofrece «Apariencia»: así no suma `tema` a `app.json`), `<link rel="stylesheet" href="tema.css">` antes de `app.css` en `ui/index.html`, cambiar su
`:root` y su `@media (prefers-color-scheme: dark)` por su bloque de arriba, y renombrar con la tabla (en `app.css` y en los
`var(--…)` de `app.js`; `sed -i 's/var(--suave)/var(--texto-suave)/g'` en todas menos Esquema). Borrar `html, body {background;
color}`, `:focus-visible` y `color-scheme`, que ya trae la pieza.

| App | Además (lo que no es mecánico) |
|---|---|
| Esquema | El orden importa: primero `--suave` → `--panel-2`, después `--gris` → `--texto-suave` (si no, se mezclan). `--borde` → `--linea`. Cambia su `dataset.tema` a mano por `tema.aplicar(E.config.tema)`, sus `[data-tema=…]` del CSS por `[data-pz-modo=…]` y el selector de Ajustes por `tema.selectorHTML()` (botones `data-pz-tema`). Sus `--d-*` pasan a `light-dark()` (sin respaldo `@supports`: ver arriba). |
| Graba | `html.vidrio` redefine `--panel`, `--lateral` y `--linea` con transparencias: cámbialo a `--panel-2`/`--linea` y deja `--campo`/`--solido` como propios. Recién ahora puede ofrecer «Apariencia» (antes solo seguía al sistema): suma `tema` a `app.json` → `config`. |
| Corta | Era oscura por defecto y clara con `prefers-color-scheme: light`; con «sistema» se ve igual. Su `--lateral` queda propio (con `light-dark`). Suma «Apariencia» si quiere. |
| Repasa | `--papel` queda propio; el fondo cuadriculado sigue en `body`. El celular (`movil/`) usa la misma `ui/`: nada aparte. |
| Alcancía | `--barra-alto` queda propio; su `#toast` pasa a `--pz-toast-abajo: calc(var(--barra-alto) + 16px)` si usa `componentes`. |
| Minuta | Cada universo trae sus colores y su modo: al cargar un universo, `tema.aplicar(universo.modo)` (en vez de `dataset.modo`) y sus colores van **directo a los tokens** (`--fondo`, `--panel`, `--acento`…, ya resueltos para ese modo) en vez de los pares. `:root[data-modo="claro"]` → `:root[data-pz-modo="claro"]`. No ofrece «Apariencia» (lo decide el universo): `pieza.py agregar tema minuta --sin-config=tema`. |

## Si venías de 0.2.0

| Qué cambió | Qué hacer en la app |
|---|---|
| El título de una ventana `aria-modal` (con `tabindex="-1"`, que la pieza `componentes` enfoca al abrir) no lleva anillo de foco | Si lo quitabas en tu `app.css` (`.galeria h2:focus { outline: none }`), bórralo. |

## Si venías de 0.1.0

| Qué cambió | Qué hacer en la app |
|---|---|
| `<html data-tema>` → `<html data-pz-modo>` | En `app.css`: `:root[data-tema=` → `:root[data-pz-modo=`. En `app.js`: deja de leer `document.documentElement.dataset.tema`; usa `tema.valor` / `tema.resuelto()` (o `alCambiar`). Los `data-tema` de tus propios elementos no cambian, y un `closest("[data-tema]")` ya no encuentra `<html>`. |
| `--sombra` ya no usa `light-dark()` | Si la redefinías para arreglarla (`--sombra: 0 8px 28px light-dark(…)`), bórralo: los pares `--sombra-claro`/`--sombra-oscuro` ya funcionan. |
| Tokens nuevos `--sobre-rojo`, `--sobre-texto` | Nada: los usa `componentes` 0.2.0. Si tu app pinta texto sobre `--rojo` o `--texto`, úsalos en vez de `--panel`/`--fondo`. |
| El anillo de foco no rodea la caja de un diálogo enfocado | Borra tu regla `[aria-modal]:focus-visible { outline: none }` si la tenías. |
| `pieza.py agregar … --sin-config=tema` | Si tu app no ofrece «Apariencia» (Minuta), saca `tema` de `app.json` → `config`; `actualizar` no lo vuelve a sumar si la agregaste con el flag (o anota `"sin_config": ["tema"]` en `piezas.json` → `tema`). |

## Vidrio (0.3.0)

1. «Vidrio» sigue al sistema: claro u oscuro.
2. `tema.js` pone `<html data-pz-estilo="vidrio">`.
3. `tema.css` pone luces de color detrás (`body`) y hace translúcidos `--panel`, `--panel-2` y `--linea`.
4. Lo que flota se esmerila solo: diálogos y avisos de «componentes», `[role=dialog]`, `header`, `nav`, `aside` y `fieldset`.
   Usa la clase `.pz-vidrio` para esmerilar algo propio.
5. Con «reducir transparencia» del sistema, los paneles quedan sólidos.

`tema.estilo` dice `"vidrio"` o `"plano"`. `tema.resuelto()` sigue diciendo el modo (`"claro"` u `"oscuro"`).

## Temas de afuera

Un universo o la comunidad suman temas con `tema.registrar()`:

```js
tema.registrar({ id: "mar", nombre: "Mar", base: "oscuro", colores: { acento: "#33aaff", fondo: "#001122" } });
```

- `id`: minúsculas, números y guion. No puede ser `sistema`, `claro`, `oscuro` ni `vidrio`.
- `base`: `claro`, `oscuro` o `vidrio`.
- `colores`: solo los tokens de `PiezaTema.TOKENS`, en `#rrggbb`. Lo demás se descarta.
- Los colores se ponen con CSSOM (`style.setProperty`) en los dos pares del token. Nunca como CSS escrito.
- El selector «Apariencia» suma el tema con su nombre escapado. Guardarlo es de la app: `config.tema` solo acepta los cuatro de
  la pieza. Un universo guarda el suyo en su propia clave.
