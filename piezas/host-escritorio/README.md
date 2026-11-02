# Pieza «host-escritorio» — la app de Windows y Linux (Electron)

La parte nativa que cada app repetía (400–900 líneas de `main.js` + `servicios.js` + `rutas.js` + `preload.js`), una sola vez y
sin nada de una app adentro: todo sale de `app.json` y de los parámetros. Misma API y mismas reglas que [`host-mac`](../host-mac/).

| Archivo (en la app) | Qué hace | Electron |
|---|---|---|
| `escritorio/src/host.js` | Ventana, protocolo `<id>://`, puente, capacidades comunes, menú, apariencia, arranque | sí (inyectable) |
| `escritorio/src/enchufe.js` | `app.json`, config validada, idioma, `dentro()`, acciones declaradas | no |
| `escritorio/src/procesador.js` | Scripts de `bin/` con límite de tiempo, entorno limpio, entrada por archivo, secreto por stdin; la fila | no |
| `escritorio/src/vigilante.js` | Vigilar la carpeta de la persona (`fs.watch`) sin avisar lo que escribió la app | no |
| `escritorio/src/preload.js` | Lo único que ve la página: `window.<id>Escritorio.enviar` y `window.<ID>_HOST` (pieza `host-ui`) | — |

## Uso

```js
// escritorio/src/main.js
const electron = require("electron");
const { crearHost } = require("./host");
const { crear: crearActualizaciones } = require("./actualizaciones");      // pieza «actualizaciones» (opcional)
const { lectorProgreso } = require("./progreso");                           // pieza «trabajos» (opcional)

const host = crearHost({
  electron,
  ventana: { ancho: 1280, alto: 800, icono: path.join(__dirname, "..", "iconos", "ana-256.png"), fondo: { claro: "#f7f7f5", oscuro: "#1c1c1e" } },
  sitio: "https://ana-app.github.io/ana/", codigo: "https://github.com/ana-app/ana",
  actualizaciones: crearActualizaciones({ app: electron.app, net: electron.net, repo: "ana-app/ana", nombre: "Ana" }),
  lectorProgreso,
  inyectar: { carpetaActual: () => carpetaActual() },          // valores que pone el host, nunca la interfaz
  estado: async (base) => ({ ...base, carpeta: carpetaActual() }),
  menu: ({ t, item, base }) => base(),                        // o tu plantilla con item("Nuevo…", "nuevo", "CmdOrCtrl+N")
});
host.acciones.registrar("exportar", async (d) => {             // lo propio de la app
  const ruta = await host.dialogos.guardarComo({ nombre: d.nombre, extension: "svg", contenido: d.texto });
  host.llamar("exportado", { ok: !!ruta });
});
host.iniciar();
```

### Parámetros de `crearHost`

| Parámetro | |
|---|---|
| `electron` | El módulo (en las pruebas, uno falso). |
| `ventana` | `{ancho, alto, minAncho, minAlto, icono, fondo: {claro, oscuro}, alCerrar: "salir" \| "esconder" \| "cerrar", frame}`. `"esconder"`: sigue viva (bandeja); desde 0.3.0, un `app.quit()` (apagar el equipo, cerrar sesión) igual guarda y sale. `frame: false`: sin marco (la interfaz dibuja su barra con `-webkit-app-region`). |
| `abrirAlArrancar` | `(host) => boolean` o `boolean`: ¿mostrar la ventana al arrancar? Sin decirlo, sí, salvo que la app se abrió con `--oculta` (al iniciar sesión): queda en la bandeja hasta `host.mostrar()`. |
| `userData` | `"sistema"`: lo que Chromium guarda (y la llave de `safeStorage` en Windows, en `Local State`) se queda donde estaba (`~/.config/<App>`, `%APPDATA%\\<App>`). Sin decirlo, va a `<datos>/electron`. **Una app que ya existía pasa `"sistema"`**: si no, pierde sus secretos cifrados (Windows), la caché y los permisos. |
| `entorno` | `{ANA_PROGRAMAS: …}` o `() => ({…})`: variables de la app para **todos** sus scripts, también los declarados (las de cada llamada ganan; nunca pisan `<ID>_RECURSOS`, `_DATOS`, `_PROGRESO` ni `_LATIDO`). |
| `tituloAjustes`, `menuApp({t, f, item, abrirEnlace, host})` | «Ajustes…» con otro nombre (`false`: sin él) e ítems propios debajo, en el menú de `base()`. |
| `limiteEstado`, `estadoEnFila` | Segundos del script del estado (60) y leerlo dentro de la fila (nunca a medio guardar). |
| `global` | El objeto `window.<App>` (por defecto el id con mayúscula). |
| `sitio`, `codigo` | Enlaces del menú Ayuda (solo https). `ayuda: false`: sin menú Ayuda. |
| `carpeta` | `{clave: "carpeta", titulo, boton, falta}`: la carpeta que elige la persona (`host.carpeta`). Su ruta real queda en `config.<clave>` (en `app.json` con `"interfaz": false`) y trae el inyector `carpetaActual` (sin carpeta: `codigo: "falta"` con «Elige una carpeta primero.» o tu `falta`). En Windows y Linux no hay marcador del sistema: si la carpeta se movió, `actual()` es `null`. |
| `vigilar` | `{extensiones: [".md"], alCambiar(base, host), alCambiarArchivo(ruta, texto, host)}`: el vigilante de la carpeta (`host.vigilante`). Por defecto, un archivo conocido que cambió afuera manda `archivoCambiado {ruta, texto}`; `alCambiar` sirve para volver a listar. |
| `latido` | `{muerto: 45, primero: 120, revisar: 5}` segundos para las acciones `"limite": "trabajo"` (solo pruebas). |
| `alTocarAviso(id, host)` | La persona tocó un aviso de `host.notificaciones` (la ventana ya se mostró). |
| `menu({t, f, item, salir, abrirEnlace, base, host})` | La plantilla del menú. `item(etiqueta, accion, atajo)` manda `window.<App>.menu({accion})` (nada antes de elegir el idioma). Se rearma al cambiar el idioma. |
| `inyectar` | `{fuente: (entrada) => valor}` para el `inyectar` de las acciones (el host trae `idiomaUI`, `carpetaDatos` y, con `carpeta`, `carpetaActual`; lo tuyo gana). `null` = no corre (`codigo: "falta"`); `host.falta("Elige un proyecto primero.", valores)` = no corre y responde ese texto. |
| `estado(base, host)` | Suma lo propio al estado (`base`: lo de `bin/estado.py` si existe + `version`, `idioma`, `plataforma`, `config`, `actualizacion`). |
| `estadoScript` | Otro script de estado, o `null` para ninguno. |
| `actualizaciones` | Una instancia de la pieza «actualizaciones»: el host atiende `buscarActualizacion`/`actualizar` (nunca con algo en curso) y revisa cada 6 h con el idioma elegido. |
| `lectorProgreso` | De la pieza «trabajos»: habilita `progreso` en las acciones. |
| `tareas(host)` | Lo que corre solo, una vez y recién con el idioma elegido. |
| `alCambiarConfig(nueva, anterior, host)`, `antesDeSalir(host)`, `alCrearVentana(ventana, host)` | Ganchos. |
| `permisos(permiso, detalles)` | Los permisos del navegador que la app acepta (todo lo demás se niega; solo para páginas `<id>://`). |
| `idiomaElegido()` | Si la app no guarda `idioma_ui` en `config.json`. |
| `guardarAlSalir` | `false` si la interfaz no atiende `menu({accion: "guardar"})`. |
| `recursos`, `datos`, `python`, `preload` | Solo desarrollo y pruebas. |

### Lo que devuelve

| | |
|---|---|
| `acciones.registrar(nombre, fn(datos, host, {responderA, ventana}))` | Una acción propia. Gana sobre las del host y las declaradas: así se migra de a poco. `responderA`: el `webContents` de otra ventana agregada que la pidió (`null` si fue la principal). |
| `llamar(funcion, json, destino?)` | `window.<App>.<funcion>(json)`. Solo nombres simples; nada antes de `listo`. `destino`: el `webContents` de una ventana agregada. |
| `despachar(accion, datos, {responderA}?)` | Correr una acción como si la pidiera la interfaz (con `responderA`, como si la pidiera esa ventana). |
| `ventanas.agregar(w)`, `.quitar(w)`, `.preferencias()`, `.todas()` | Otra ventana con la misma interfaz (el panel de la bandeja, una barra): créala con `webPreferences: host.ventanas.preferencias()` y cárgala con `<id>://ui/…`. Habla con el puente con las mismas guardas, no navega fuera de `ui/` y recibe la respuesta a lo que pidió (también las declaradas y `listo` → su `estado`). |
| `procesador.correrJSON(script, args, {limite, latido, progreso})`, `.conEntrada(script, args, datos, …)`, `.correr(script, args, {secreto, entrada, limite})`, `.cortarTodo()` | Scripts de `bin/`. `correr` devuelve `{respuesta, salidaEstandar, porLimite}`. `latido: true`: sin tope mientras el script lata (pieza «trabajos»). |
| `fila.agregar(async () => …)` | De a una y en orden (guardados). |
| `config.leer()`, `config.guardar(cambios, {desdeInterfaz})`, `idioma.t/f/codigo/elegido`, `t` | Con las reglas de `app.json` (las de `nucleo`). |
| `dentro(base, relativa, {extensiones})` | La guarda de `nucleo.ruta_en`. |
| `dialogos.carpeta()`, `.archivos({extensiones, varios, mensaje, desde})`, `.guardarComo({nombre, extension, contenido, mensaje, privado})`, `.guardarArchivo(…)` | Diálogos del sistema (rutas reales). `privado`: 0600 (sin decirlo, `app.json` → `"privado"`). `guardarArchivo` dice cómo terminó: `{ok: true, ruta}` o `{ok: false, codigo: "cancelado" \| "vacio" \| "tamano" \| "extension" \| "escribir"}`. |
| `medios.registrar(nombre, resolver(ruta) → absoluta \| null)` | `<id>://<nombre>/<ruta>` con rangos (videos). |
| `copiar`, `abrirEnlace` (solo https, sin usuario ni clave), `papelera(absoluta)`, `mostrarEnCarpeta(absoluta)`, `mostrar`, `salir`, `ocupar`/`soltar`/`ocupada`, `await esperarLibre(ms)` (true si quedó libre: fila, scripts y lo marcado), `enviarEstado` | |
| `carpeta.actual()`, `.elegir({titulo, boton})`, `.usar(ruta)`, `.olvidar()` | Con `carpeta`. `usar` solo con rutas que eligió la persona o que la app leyó de lo suyo, nunca de la interfaz. Mueve el vigilante. |
| `vigilante.conocer(ruta, texto)`, `.olvidar(ruta)`, `.conocidos`, `.importa(rel)`, `.absoluta(rel)`, `.empezar(base)`, `.detener()` | Con `vigilar`. Lo que conoce (lo que la app leyó o escribió) no se avisa. |
| `secretos(nombre, {archivo})` → `{disponible, guardar(cuenta, valor), leer(cuenta), borrar(cuenta)}` | Cifrados con `safeStorage` en `<datos>/.<nombre>.json` (0600; `archivo` para seguir usando uno de antes, p. ej. `.tokens`). En Linux sin llavero (`basic_text`) `disponible` es false y no se guarda nada. Un secreto llega a un script solo por stdin (`procesador.correr(…, {secreto})`). |
| `notificaciones.mostrar({id, titulo, texto, silencioso})`, `.quitar(id)`, `.soportado`, `await .pedirPermiso()` | Avisos del sistema. Nada antes de elegir el idioma; tocar uno muestra la ventana y llama `alTocarAviso`. |
| `falta(texto, valores)` | Lo que devuelve un inyector cuando falta algo, con su texto. |

### Lo que atiende solo

`listo` (manda el estado), `config` (guarda, rearma el menú si cambió el idioma, aplica `config.tema` a `nativeTheme.themeSource` y
al fondo de la ventana, y arranca las tareas con el idioma elegido), `abrirEnlace`, `copiar` → `copiado`, y con `actualizaciones`,
`buscarActualizacion` → `actualizacionRevisada` y `actualizar` → `actualizacionProgreso`. Y **toda acción declarada** en
`acciones.json` (abajo).

## Acciones declaradas (`acciones.json`)

`pieza.py agregar`/`actualizar` lo arman en la raíz de la app con las `acciones` de cada `pieza.json` instalado y las de `app.json`
→ `"acciones"` (las propias, con su script en `bin/`). Va **dentro de la app** junto a `app.json` (en `extraResources`). Formato y
reglas en [`docs/enchufe.md`](../../docs/enchufe.md#una-acción). Al cargar, el host vuelve a revisar cada una con las mismas reglas
que `pieza.py` (lo que no pasa no se carga y se avisa en la consola) y que su script exista.

En cada mensaje: valida `datos` por su tipo (lo no declarado no pasa; un `$campo` de `args` es obligatorio; la entrada entera hasta
`maximo` bytes, 5 MB si no lo dice) → pone lo de `inyectar` (nunca de la interfaz) → fila si `cola: "escritura"` → con `vigilar:
"escribe"`, el vigilante conoce `texto` antes de escribir → corre el script con su límite (`limite`: segundos, `"trabajo"` = sin tope
mientras lata, o el de su orden con `{segun, valores, otro}`; la entrada en un archivo 0600 dentro de una carpeta temporal propia)
→ con `vigilar: "lee"`, el vigilante conoce el `texto` de la respuesta → `window.<App>.<responde>({...respuesta, ...eco})` → corre
`despues`. Si los datos no pasan, el error igual trae los campos de `eco` que sí son válidos (la interfaz sabe a qué orden responde).

Errores del host (la interfaz los traduce con `T(texto, valores)`; `error` va ya traducido para las interfaces de antes):
`{ok: false, codigo: "datos" | "falta" | "limite" | "fallo", campo?, texto, valores, error}`. Un trabajo que deja de latir responde
`codigo: "limite"` con «Dejó de avanzar y lo detuve. Intenta de nuevo.».

## Seguridad

- Ventana con `sandbox`, `contextIsolation`, sin `nodeIntegration` ni `webview`; solo navega dentro de `<id>://ui/` (`will-navigate`,
  `will-redirect`, `setWindowOpenHandler`); un enlace https va al navegador **por `abrirEnlace`** (si la app registró el suyo, decide ella).
- Con `"datos": "visible"`, `~/<Nombre>` recién creada queda 0700, como en `nucleo` (antes, la de siempre del sistema).
- El puente (`ipcMain.on(<id>)`) solo atiende las ventanas propias (la principal y las agregadas), su **marco principal** y el **origen** `<id>://ui/`. El preload
  recibe el id del host (`--pieza-host=<id>`), nunca de la página, y manda una copia JSON.
- El protocolo sirve solo archivos de `ui/` (sin `..`, sin enlaces hacia afuera, sin `?`) y lo que aprueba un resolvedor de medios.
- Todo permiso del navegador se niega salvo lo que la app acepte con `permisos`, y solo para sus páginas.
- Scripts: sin variables `<ID>_*` de afuera, lo de la persona nunca como argumento, el secreto por stdin y **límite de tiempo** que
  corta también lo que lanzó el script (grupo de procesos en Linux, `taskkill /T` en Windows); un trabajo sin tope se corta si deja
  de latir, y al salir se corta lo que siga corriendo (nada queda huérfano: un trabajo queda «interrumpido» y se sigue después).
- Secretos solo cifrados por el sistema (`safeStorage`), nunca en texto plano: sin llavero en Linux, no se guardan.

## Si venías de la 0.2.0

Nada obligatorio. Lo que cambia solo: un enlace tocado pasa por tu `abrirEnlace` registrado; `~/<Nombre>` recién creada queda 0700;
las acciones registradas reciben un tercer argumento (`{responderA, ventana}`). Lo que cada app puede borrar:

| App | Se borra | Con |
|---|---|---|
| Minuta | La clase `VentanaSinMarco` y el `new Proxy(electron, …)`; `USERDATA_DE_SIEMPRE` y el `app.setPath("userData", …)` después de `iniciar()`; el `w.removeAllListeners("ready-to-show")` de `prepararVisor` (y `mostrarAlAbrir`); `app.on("before-quit", …)`; el segundo `ipcMain.on(host.id, …)` del panel y su `webPrefs()`; el `entorno: entornoScripts()` de cada llamada | `ventana: {frame: false}`; `userData: "sistema"`; `abrirAlArrancar: () => Perfil.falta \|\| !process.argv.includes("--oculta")`; nada (lo hace `alCerrar: "esconder"`); `host.ventanas.agregar(panel)` con `host.ventanas.preferencias()` (sus `ACCIONES(d, panel)` registradas usan `ctx.ventana`); `entorno: entornoScripts` en `crearHost` |
| Graba | `datosDeElectron` y el `app.setPath("userData", …)` después de `iniciar()`; el `v.removeAllListeners("ready-to-show")` de `alCrearVentana` | `userData: "sistema"`; `abrirAlArrancar: () => !OCULTA \|\| faltaAlgo()`. Para declarar `procesar.py`: `entorno: () => ({GRABA_HERRAMIENTAS: …})` |
| Esquema | Nada | — |

Sigue en las apps (anotado en `docs/catalogo.md`): `listo` que la interfaz no manda (Minuta lo despacha en `did-finish-load`),
scripts largos con registro y sin salida JSON, `idiomas/` descargados en `Idioma`, y el vidrio de Windows 11 (`setBackgroundMaterial`).

## Si venías de la 0.1.0

Nada se rompe: lo de 0.1.0 sigue igual. Al actualizar (`pieza.py actualizar <app> host-escritorio`) llega `vigilante.js`.
- `await host.esperarLibre(ms)` ahora también espera a los scripts que corren y devuelve true si quedó libre; al salir se cortan
  los que queden (antes quedaban huérfanos).
- Un `"limite": 3600` puesto «por si acaso» puede ser `"trabajo"` (con «trabajos» 0.2.0) o `{"segun": "orden", …}`.
- **Esquema:** `main.js` puede pasar a `carpeta: {clave: "carpeta"}` (borra `carpetaActual()` y `usarCarpeta`: `host.carpeta.usar(c)`;
  el inyector que manda `""` sin carpeta queda en `inyectar`) y `vigilar: {extensiones: [".md", ".mmd"], alCambiar: relistar}`
  (borra `src/vigilante.js` propio: la lista de archivos que se compara pasa a `alCambiar`). `abrirArchivo`/`guardarArchivo`
  se pueden declarar en `app.json` (`carpeta.py leer|guardar`, `vigilar: "lee" | "escribe"`, `maximo` si los documentos pesan más
  de 5 MB, `eco: ["ruta"]`); la traducción de `error` que hacía `main.js` la hace la interfaz con `texto`.

## Pasar una app a esta pieza

Lo aprendido al pasar las seis está en «Pasar una app a esta pieza» de [`host-mac`](../host-mac/README.md#pasar-una-app-a-esta-pieza)
(`menu` y `listo` en la interfaz, `config` que no manda el estado, `config.guardar(x, {desdeInterfaz: false})`, límites por orden).
Además: el protocolo `<id>://` no lleva `corsEnabled` (un `fetch` a `<id>://video/…` desde `<id>://ui/` falla por CORS, no con
404); y una app que ya existía pasa `userData: "sistema"`.

En todas: `pieza.py agregar host-escritorio <app>` (antes **borra `escritorio/src/preload.js`**: el de la pieza lo reemplaza;
`pieza.py` no pisa un archivo que ya existe), suma `acciones.json` a `extraResources` de `escritorio/package.json`
(`{"from": "../acciones.json", "to": "<id>/acciones.json"}`, junto a `app.json`) y escribe `main.js` como arriba. Prueba con
`HOME=$(mktemp -d) xvfb-run -a node pruebas/arranque.mjs` de la app.

| App | Se borra | Queda como acción propia (`acciones.registrar`) | Ojo |
|---|---|---|---|
| Esquema | `servicios.js` y `rutas.js` (`absoluta` → `host.dentro(base, r, {extensiones: [".md", ".mmd"]})`), `preload.js`; de `main.js`: ventana, protocolo, `ipcMain`, `Config`, `Idioma`, `Procesador`, `EnOrden`, `listo`, `config`, `copiar`, `abrirEnlace`, `probarIA`, `buscarActualizacion`, `actualizar`, permisos y arranque | `elegirCarpeta`, `abrirProyecto`, `proyecto` (o declararla con `"*": "pasar"`, `inyectar: {carpeta: "carpetaActual"}` y `progreso: "proyectoProgreso"`), `papelera`, `abrirArchivo`, `guardarArchivo` (con `host.fila`), `estructura`, `crearReadme`, `dibujar`, `exportar` (`host.dialogos.guardarComo`), catálogo | `vigilante.js` queda; `progreso.js` de «trabajos» como `lectorProgreso`; el menú con `item(...)` |
| Graba | `servicios.js` (config, idioma, `Procesador`, `Tokens` → `host.secretos("tokens", {archivo: ".tokens"})`), `rutas.js`, `preload.js` | Todo lo de grabar (`grabar`, `terminar`, `pausar`, `recortar`, `teleprompter`…), YouTube, permisos | `ventana.alCerrar: "esconder"` (bandeja), `permisos: (p) => p === "media"`, `medios.registrar("video", …)` y `medios.registrar("app", …)` para `barra.html` y las demás ventanas propias (siguen con su `preload-interno.js`); `probarIA` ya va por la pieza `ia` |
| Minuta | `rutas.js`, `preload.js`, la ventana y el puente de `main.js`, el token de `bienvenida.js` → `host.secretos(…)`, `new Notification` → `host.notificaciones` (y su `click` → `alTocarAviso`) | Casi todo (perfil, universos, gimnasio, calendario, ventana sin bordes) | **La última en migrar:** guarda `idioma_ui` en `perfil.json` (`idiomaElegido`), tiene el panel de la bandeja con su propia página y su `ventana`/`cerrar`/`minimizar`. Antes: el puente de hoy no revisa marco ni origen (ver brechas) |
| Corta, Repasa, Alcancía | — (aún no tienen Windows/Linux) | — | Con esta pieza parten con `main.js` de ~50 líneas: sus acciones de script (`guardarProyecto`, `guardarProgreso`, `importar`…) se declaran en `app.json`; lo nativo (diálogos, `medios.registrar("video" \| "material", …)`) se registra. Alcancía: el Llavero con `host.secretos("conexiones")`, los avisos de compromisos con `host.notificaciones` y la carpeta vigilada de Descargas con un `Vigilante` propio (`new Vigilante({extensiones: [".csv", ".xlsx", ".pdf", ".ofx"]})`) |
