# Pieza «cifrado» — con una frase que solo conoce la persona

WebCrypto, sin dependencias, el mismo código en el computador (interfaz), en el teléfono y en Node. PBKDF2-SHA256 (600.000
vueltas, sal de 16 bytes, frase NFC) → 512 bits: AES-256-GCM (IV de 12 bytes por sobre, AAD que ata cada sobre a su lugar) +
HMAC-SHA256 para nombres opacos. Un verificador dice «la frase no es la correcta» antes de tocar nada. La frase nunca se guarda:
se guarda `llaves.raw` (en el Llavero o el Keystore), si la persona quiere.

```js
const c = PiezaCifrado.crear({ app: "Ana", contexto: "ana:copia", marca: "ana", tipo: "copia" });
const { cabecera, llaves } = await c.nuevaCabecera(frase);          // revisa la frase (12+ caracteres)
const texto = await c.armar(contenido, cabecera, llaves);           // un archivo JSON: cabecera + datos cifrados
const { contenido } = await c.abrir(texto, { frase });              // o { raw: llaves.raw }
const sobre = await c.cifrarJSON(llaves, valor, "perfiles/ana");    // descifrarJSON(llaves, sobre, "perfiles/ana")
const nombre = await c.nombreOpaco(llaves, "perfiles/ana.json");    // 32 hex
PiezaCifrado.fuerzaFrase(frase)  // {nivel 0..3, texto: "Muy corta" | "Aceptable" | "Buena" | "Muy buena"}
// Varios sobres en un archivo (el formato de la copia de Repasa):
const t2 = await c.armarVarios([a, b], cabecera, llaves, { aad: "ana:copia:v1", extra: { creada: hoy } });
const { contenidos, archivo } = await c.abrirVarios(t2, { frase }, { aad: "ana:copia:v1" });   // archivo.creada
throw c.error("no_es");          // un error con las frases y la marca de esta app (para lo que revisa la app misma)
```

**Desde un ES module:** es un script clásico. En el navegador (o el WebView), cargar `<script src="cifrado.js">` antes del módulo y
usar `globalThis.PiezaCifrado`; en Node, `createRequire(import.meta.url)("./cifrado.js")`.

| Opción de `crear` | Para qué |
|---|---|
| `contexto` | Ata todo a esta app y este uso: AAD de los datos (`contexto:<versión>`), del verificador (`contexto:verificador`) y nombres (`contexto:ruta:`) |
| `verificador`, `aadVerificador` | Si un formato viejo usaba otros (Alcancía) |
| `marca`, `tipo`, `formato` | Cómo se reconoce un archivo de `armar` (`{[marca]: tipo, version: formato, …}`); uno con versión mayor da `version` |
| `maximo` | Un texto más grande ni se intenta leer (100 MB por defecto) |
| `claveVersion`, `claveSobres` | Los nombres que ya usaba la app (`"v"` en Repasa; `"archivos"` por defecto para `armarVarios`) |
| `mensajes` | `{codigo: frase}`: las frases propias de la app (con `{app}` si quiere); las demás, las de la pieza |

Errores: `ErrorCifrado` con `codigo` (`frase`, `danado`, `version`, `no_es`, `sin_cifrado`, `corta`), `plantilla` y `valores`
(`{app}`): `Tp(e.plantilla, e.valores)`; `e.frase` (= `message`) ya rellena y `e.comoDict()` / `JSON.stringify(e)` →
`{ok: false, codigo, plantilla, valores, error}`. Nunca acepta menos de 100.000 vueltas. Las frases de `fuerzaFrase` solo se suman
al `en.json` de la app si la usa (`textos_si_usa`).

## Si venías de la 0.1
Nada obligatorio. **Repasa:** `crear({app: "Repasa", contexto: "repasa", claveVersion: "v"})` y la copia con `armarVarios` /
`abrirVarios` (`aad: "repasa:copia:v1"`, `extra: {creada}`): el mismo archivo de siempre; `C.error("no_es")` en vez de su
`errorCifrado`. **Todas:** si no usas `fuerzaFrase`, puedes borrar «Muy corta», «Aceptable», «Buena» y «Muy buena» de `en.json`.

## Pasar una app a esta pieza
**Repasa** (`motor/cifrado.js`, ES module): borrarlo y agregar `ui/cifrado.js` (script clásico: `window.PiezaCifrado`; en el motor,
`const C = globalThis.PiezaCifrado.crear({ app: "Repasa", contexto: "repasa" })` o `createRequire` en Node). Lo de antes →
`C.derivar/cifrar/descifrar/cifrarJSON/descifrarJSON/nombreOpaco/nuevaCabecera/abrirCabecera` (mismos formatos: lo ya
guardado se abre). Cambios no mecánicos: `nuevaCabecera(frase, {iteraciones})` ahora revisa la frase (pasar `{revisar: false}`
donde ya se revisó antes) y devuelve las llaves con `raw`; `ErrorFrase`/`ErrorDañado` pasan a `ErrorCifrado` con `codigo`
(`frase` / `danado`); `MENSAJES` cambia a la frase con `{app}`. `movil/armar.mjs` y `empaquetar.sh` copian `ui/cifrado.js`.
**Alcancía** (`ui/copia.js`): la parte de cifrado se va; queda `paraCelular` y lo del celular. `AlcanciaCopia.nuevaCabecera`,
`abrirCabecera`, `armar`, `leer`, `abrir`, `salDe`, `huella`, `revisarFrase`, `fuerzaFrase` salen de
`PiezaCifrado.crear({ app: "Alcancía", contexto: "alcancia:celular", verificador: "alcancia", marca: "alcancia", tipo:
"copia-celular" })` (lo que ya está en la nube se abre igual; probado). La llave guardada de 32 bytes sigue sirviendo, pero las
nuevas son de 64 (`raw`): `Celular.swift` debe aceptar los dos largos. `abrir` devuelve `{contenido, llaves}` (antes `{contenido,
raw}`: usar `llaves.raw`). La revisión de `contenido.formato`/`estado` queda en Alcancía.
