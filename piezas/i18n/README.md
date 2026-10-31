# Pieza «i18n» — idiomas de la interfaz

La frase en español es la clave; `ui/idiomas/<codigo>.json` trae su traducción. Un archivo (`ui/i18n.js`), sin dependencias,
compatible con una CSP `script-src 'self'`. Lo que viene de afuera se valida y todo lo que va a HTML se escapa.

```html
<script src="i18n.js"></script>  <!-- antes de app.js: queda window.PiezaI18n -->
```
```js
const i18n = PiezaI18n.crear();
await i18n.cargar(i18n.elegir({ config: E.config.idioma_ui }));   // lo elegido > config > ?idioma= > sistema
const { T, Tp, tr, frase } = i18n;
raiz.innerHTML = `<h2>Ajustes</h2>${frase("Hola, **{nombre}**", { nombre: E.perfil.nombre })}`;
i18n.traducirDOM(raiz);   // traduce «Ajustes»; nunca entra a [data-sin-traducir]
```

| Función | Para qué |
|---|---|
| `T(plantilla, valores)` | Frase entera con `{marcadores}` → HTML: se escapa la frase y cada valor; `**así**` va en negrita. En una sola pasada (un valor con «{x}» nunca se reemplaza). |
| `frase(plantilla, valores, etiqueta?)` | `T` dentro de `<span data-sin-traducir>` (ya va traducida). |
| `Tp(plantilla, valores)` | Texto plano (textContent, `aria-label`, avisos). |
| `Thtml(plantilla, valoresHtml)` | Valores que son HTML armado por ti con `esc()`. Nunca texto de afuera. |
| `tr(texto)` | Un texto ya pintado: exacto, con espacios, con íconos alrededor, por partes « · », plantillas (`{n}` solo números, otros marcadores cualquier texto, en cualquier orden) y `palabras` para fechas. |
| `traducirDOM(raiz)` | Textos y `title`, `aria-label`, `placeholder`, `alt`. El texto salta `[data-sin-traducir]`, script, style, svg, textarea, code, pre y lo que digas en `crear({noTraducir})`; de un `textarea` sí traduce `placeholder`, `title` y `aria-label` (son de la app; lo escrito es de la persona). Sin más opciones, los atributos se saltan donde se salta el texto. Con `crear({noTraducirAtributos: "[data-mio]"})` se traducen en todas partes —también en las zonas de `noTraducir`, como un botón «Abrir nota» dentro de una lista de notas— menos ahí y en `[data-sin-traducir]` (siempre, sin nombrarlo). |
| `cargar(codigo, {ruta?, traer?})` / `usar(paquete)` | Carga y valida `idiomas/<codigo>.json`; si falla, queda en español. |
| `elegir({elegido, config, url, sistema, disponibles})`, `idiomaDelSistema()` | Qué idioma usar. |
| `validarPaquete(dato, codigo?)`, `esc(v)` | Para un paquete descargado (catálogo) y para escapar. |

**Formato del paquete** (`ui/idiomas/en.json`, el mismo para los que vienen del catálogo):
`{"codigo": "en", "nombre": "English", "bandera": "🇬🇧", "textos": {"Guardar": "Save"}, "palabras": {"octubre": "october"}}`.
Cada frase se descarta si no es texto, trae HTML o caracteres de control/bidi, o no tiene **los mismos marcadores y `**`** que la clave.

En las pruebas de la app, `window._faltantes = new Set()` (o `crear({faltantes})`) junta las frases sin traducción.

## Pasar una app a esta pieza
Las apps tienen `tr`/`T`/`traducirDOM` dentro de `ui/app.js`. Cambiarlas por `const { T, Tp, tr, frase, traducirDOM } = i18n`
(con `E.idioma` → `i18n.idioma`) y cargar `i18n.js` antes de `app.js`. En Alcancía, Corta y Repasa, donde un valor de `T()` era
HTML armado, usar `Thtml()`. El `en.json` de hoy (`{codigo, nombre, textos}`) ya sirve.

## Si venías de 0.3.0

| Qué cambió | Qué hacer en la app |
|---|---|
| Con `noTraducirAtributos`, `[data-sin-traducir]` siempre cuenta (sus atributos y los de adentro no se traducen) | Si lo agregabas a mano al selector (`noTraducirAtributos: "[data-sin-traducir], [data-mio]"`), puedes quitarlo. |

## Si venías de 0.2.0

| Qué cambió | Qué hacer en la app |
|---|---|
| El `placeholder` (y `title`, `aria-label`) de un `<textarea>` se traduce | Nada. Si lo traducías a mano, bórralo. |
| `crear({noTraducirAtributos})` | Si recorrías el DOM para traducir atributos dentro de tus zonas sin traducir (Minuta: `SIN_ATRIBUTOS`), pásale ese selector y borra el recorrido. |
