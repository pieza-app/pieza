# Pieza «host-escritorio» — la app de Windows y Linux (Electron)

La parte nativa que cada app repetía (400–900 líneas de `main.js` + `servicios.js` + `rutas.js` + `preload.js`), una sola vez y
sin nada de una app adentro: todo sale de `app.json` y de los parámetros. Misma API y mismas reglas que [`host-mac`](../host-mac/).

| Archivo (en la app) | Qué hace | Electron |
|---|---|---|
| `escritorio/src/host.js` | Ventana, protocolo `<id>://`, puente, capacidades comunes, menú, apariencia, arranque | sí (inyectable) |
| `escritorio/src/enchufe.js` | `app.json`, config validada, idioma, `dentro()`, acciones declaradas | no |
| `escritorio/src/procesador.js` | Scripts de `bin/` con límite de tiempo, entorno limpio, entrada por archivo, secreto por stdin; la fila | no |
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
| `ventana` | `{ancho, alto, minAncho, minAlto, icono, fondo: {claro, oscuro}, alCerrar: "salir" \| "esconder" \| "cerrar"}`. `"esconder"`: sigue viva (bandeja). |
| `global` | El objeto `window.<App>` (por defecto el id con mayúscula). |
| `sitio`, `codigo` | Enlaces del menú Ayuda (solo https). |
| `menu({t, f, item, salir, abrirEnlace, base, host})` | La plantilla del menú. `item(etiqueta, accion, atajo)` manda `window.<App>.menu({accion})` (nada antes de elegir el idioma). Se rearma al cambiar el idioma. |
| `inyectar` | `{fuente: (entrada) => valor}` para el `inyectar` de las acciones (el host trae `idiomaUI` y `carpetaDatos`). `null` = no corre. |
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
| `acciones.registrar(nombre, fn(datos, host))` | Una acción propia. Gana sobre las del host y las declaradas: así se migra de a poco. |
| `llamar(funcion, json)` | `window.<App>.<funcion>(json)`. Solo nombres simples; nada antes de `listo`. |
| `despachar(accion, datos)` | Correr una acción como si la pidiera la interfaz. |
| `procesador.correrJSON(script, args, {limite, progreso})`, `.conEntrada(script, args, datos, …)`, `.correr(script, args, {secreto, entrada, limite})` | Scripts de `bin/`. `correr` devuelve `{respuesta, salidaEstandar, porLimite}`. |
| `fila.agregar(async () => …)` | De a una y en orden (guardados). |
| `config.leer()`, `config.guardar(cambios, {desdeInterfaz})`, `idioma.t/f/codigo/elegido`, `t` | Con las reglas de `app.json` (las de `nucleo`). |
| `dentro(base, relativa, {extensiones})` | La guarda de `nucleo.ruta_en`. |
| `dialogos.carpeta()`, `.archivos({extensiones, varios})`, `.guardarComo({nombre, extension, contenido})` | Diálogos del sistema (rutas reales). |
| `medios.registrar(nombre, resolver(ruta) → absoluta \| null)` | `<id>://<nombre>/<ruta>` con rangos (videos). |
| `copiar`, `abrirEnlace` (solo https, sin usuario ni clave), `papelera(absoluta)`, `mostrar`, `salir`, `ocupar`/`soltar`/`ocupada`, `enviarEstado` | |

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

En cada mensaje: valida `datos` por su tipo (lo no declarado no pasa; un `$campo` de `args` es obligatorio) → pone lo de `inyectar`
(nunca de la interfaz) → fila si `cola: "escritura"` → corre el script con `limite` (la entrada en un archivo 0600 dentro de una
carpeta temporal propia) → `window.<App>.<responde>({...respuesta, ...eco})` → corre `despues`.

Errores del host (la interfaz los traduce con `T(texto, valores)`; `error` va ya traducido para las interfaces de antes):
`{ok: false, codigo: "datos" | "falta" | "limite" | "fallo", campo?, texto, valores, error}`.

## Seguridad

- Ventana con `sandbox`, `contextIsolation`, sin `nodeIntegration` ni `webview`; solo navega dentro de `<id>://ui/` (`will-navigate`,
  `will-redirect`, `setWindowOpenHandler`); un enlace https va al navegador.
- El puente (`ipcMain.on(<id>)`) solo atiende la ventana propia, su **marco principal** y el **origen** `<id>://ui/`. El preload
  recibe el id del host (`--pieza-host=<id>`), nunca de la página, y manda una copia JSON.
- El protocolo sirve solo archivos de `ui/` (sin `..`, sin enlaces hacia afuera, sin `?`) y lo que aprueba un resolvedor de medios.
- Todo permiso del navegador se niega salvo lo que la app acepte con `permisos`, y solo para sus páginas.
- Scripts: sin variables `<ID>_*` de afuera, lo de la persona nunca como argumento, el secreto por stdin y **límite de tiempo** que
  corta también lo que lanzó el script (grupo de procesos en Linux, `taskkill /T` en Windows).

## Pasar una app a esta pieza

En todas: `pieza.py agregar host-escritorio <app>` (antes **borra `escritorio/src/preload.js`**: el de la pieza lo reemplaza;
`pieza.py` no pisa un archivo que ya existe), suma `acciones.json` a `extraResources` de `escritorio/package.json`
(`{"from": "../acciones.json", "to": "<id>/acciones.json"}`, junto a `app.json`) y escribe `main.js` como arriba. Prueba con
`HOME=$(mktemp -d) xvfb-run -a node pruebas/arranque.mjs` de la app.

| App | Se borra | Queda como acción propia (`acciones.registrar`) | Ojo |
|---|---|---|---|
| Esquema | `servicios.js` y `rutas.js` (`absoluta` → `host.dentro(base, r, {extensiones: [".md", ".mmd"]})`), `preload.js`; de `main.js`: ventana, protocolo, `ipcMain`, `Config`, `Idioma`, `Procesador`, `EnOrden`, `listo`, `config`, `copiar`, `abrirEnlace`, `probarIA`, `buscarActualizacion`, `actualizar`, permisos y arranque | `elegirCarpeta`, `abrirProyecto`, `proyecto` (o declararla con `"*": "pasar"`, `inyectar: {carpeta: "carpetaActual"}` y `progreso: "proyectoProgreso"`), `papelera`, `abrirArchivo`, `guardarArchivo` (con `host.fila`), `estructura`, `crearReadme`, `dibujar`, `exportar` (`host.dialogos.guardarComo`), catálogo | `vigilante.js` queda; `progreso.js` de «trabajos» como `lectorProgreso`; el menú con `item(...)` |
| Graba | `servicios.js` (config, idioma, `Procesador`), `rutas.js`, `preload.js` | Todo lo de grabar (`grabar`, `terminar`, `pausar`, `recortar`, `teleprompter`…), YouTube, permisos | `ventana.alCerrar: "esconder"` (bandeja), `permisos: (p) => p === "media"`, `medios.registrar("video", …)` y `medios.registrar("app", …)` para `barra.html` y las demás ventanas propias (siguen con su `preload-interno.js`); `probarIA` ya va por la pieza `ia` |
| Minuta | `rutas.js`, `preload.js`, la ventana y el puente de `main.js` | Casi todo (perfil, universos, gimnasio, calendario, ventana sin bordes) | **La última en migrar:** guarda `idioma_ui` en `perfil.json` (`idiomaElegido`), tiene el panel de la bandeja con su propia página y su `ventana`/`cerrar`/`minimizar`. Antes: el puente de hoy no revisa marco ni origen (ver brechas) |
| Corta, Repasa, Alcancía | — (aún no tienen Windows/Linux) | — | Con esta pieza parten con `main.js` de ~50 líneas: sus acciones de script (`guardarProyecto`, `guardarProgreso`, `importar`…) se declaran en `app.json`; lo nativo (diálogos, `medios.registrar("video" \| "material", …)`) se registra |
