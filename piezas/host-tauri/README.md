# Pieza «host-tauri» — la app de Mac, Windows y Linux (Rust + Tauri)

Un solo host nativo para los tres sistemas. Reemplaza a [`host-mac`](../host-mac/) (Swift) y a
[`host-escritorio`](../host-escritorio/) (Electron) con **la misma API**: la interfaz de `ui/` (pieza `host-ui`) no cambia, el
núcleo Python de `bin/` tampoco, y las acciones declaradas (`acciones.json`) siguen las mismas reglas que `pieza.py`.

Por qué: un solo código que mantener en vez de dos, y apps **mucho más livianas**. Electron trae un Chromium entero en cada app;
Tauri usa el WebView que ya tiene el sistema (WebKit en Mac y Linux, WebView2 en Windows). Y Rust es estricto: el compilador
revisa memoria, nulos, errores y casos de cada `enum` antes de que algo llegue a la persona.

| Archivo (en la app) | Qué hace | Equivale a |
|---|---|---|
| `escritorio/src/pieza/enchufe.rs` | `app.json`, carpeta de datos, config validada, idioma, `dentro()`, las reglas de una acción y validar lo que manda la interfaz | `enchufe.js`, `Enchufe.swift` + `Host.swift` |
| `escritorio/src/pieza/procesador.rs` | Scripts de `bin/` con límite de tiempo (corta su grupo de procesos), latido, entorno sin `<ID>_*`, entrada por archivo, secreto por stdin; la fila | `procesador.js`, `Procesador.swift` |
| `escritorio/src/pieza/protocolo.rs` | El protocolo propio: `ui/` y los medios que la app aprueba, en el mismo origen y con rangos | protocolo `<id>://` |
| `escritorio/src/pieza/vigilante.rs` | Vigilar la carpeta de la persona sin avisar lo que escribió la app (crate `notify`: FSEvents, ReadDirectoryChangesW, inotify) | `vigilante.js`, `Vigilante` |
| `escritorio/src/pieza/sistema.rs` | Secretos en el llavero del sistema, avisos, portapapeles, enlaces https, mostrar en carpeta, papelera | `Sistema.swift`, `safeStorage` |
| `escritorio/src/pieza/host.rs` | Ventana, puente, acciones (registradas → del host → declaradas), estado, menús, bandeja, apariencia, diálogos, salir | `host.js`, `Puente.swift` |
| `escritorio/Cargo.toml`, `build.rs`, `tauri.conf.json`, `Info.plist`, `vacio/` (generados) | El proyecto de Tauri desde `app.json`: nombre, versión, identificador (el mismo `app.<id>.mac` de antes), recursos, permisos del Mac | `Package.swift`, `Info.plist`, `package.json` |
| `escritorio/src/main.rs` (una vez) | La entrada de la app: desde aquí es de la app | `<App>App.swift`, `main.js` |
| `escritorio/iconos/` (de partida) | Íconos genéricos; pon el tuyo en `iconos/icono.png` (1024×1024) y `empaquetar.sh` arma los de cada sistema | — |

## Uso

`escritorio/src/main.rs`:
```rust
mod pieza;
use pieza::host::{arrancar, item, AlCerrar, MenuPropio, Opciones, OpcionesCarpeta, Ventana};
use serde_json::json;

fn main() {
    let op = Opciones {
        global: Some("Ana".into()),
        sitio: Some("https://ana-app.github.io/ana/".into()),
        codigo: Some("https://github.com/ana-app/ana".into()),
        carpeta: Some(OpcionesCarpeta::default()),            // host.elegir_carpeta() y el inyector carpetaActual
        vigilar: Some(vec![".md".into()]),                       // avisa archivoCambiado {ruta, texto}
        menu: MenuPropio { archivo: vec![item("Nuevo…", "nuevo", Some("CmdOrCtrl+N"))], ..Default::default() },
        ventana: Ventana { al_cerrar: AlCerrar::Salir, ..Default::default() },
        ..Default::default()
    };
    arrancar(tauri::generate_context!(), op, |host| {
        host.registrar("exportar", |d, h, ctx| {
            let r = h.guardar_archivo(d["nombre"].as_str().unwrap_or("ana"), "svg", d["texto"].as_str().unwrap_or("").as_bytes(), None);
            h.llamar("exportado", json!({"ok": r.is_ok()}), ctx.destino());
        });
        let h = host.clone();
        host.registrar_medios("video", move |ruta, _| h.carpeta_actual().and_then(|c| h.dentro(&c, ruta, Some(&[".mp4"]))));
    });
}
```
La interfaz pide un medio con `host.medio("video", "clips/a.mp4")` (pieza `host-ui` 0.3): en Mac y Linux es
`ana://localhost/video/clips/a.mp4`, en Windows `http://ana.localhost/video/clips/a.mp4`. Mismo origen que la interfaz: sin CORS.

### `Opciones` (todo opcional)

| Campo | |
|---|---|
| `ventana` | `Ventana {ancho, alto, min_ancho, min_alto, fondo_claro, fondo_oscuro, al_cerrar: Salir \| Esconder, marco, barra_transparente (Mac), vidrio (Mac: vibrancy; Windows 11: Mica), nombre}`. Recuerda tamaño y lugar en `<datos>/<nombre>.json`. |
| `sitio`, `codigo`, `ayuda` | Enlaces del menú Ayuda (solo https). `ayuda: false`: sin menú Ayuda. |
| `global` | El objeto `window.<App>` (por defecto el id con mayúscula). |
| `carpeta`, `vigilar` | La carpeta de la persona (su ruta en `config.<clave>`, `"interfaz": false` en `app.json`) y su vigilante. |
| `estado_script`, `limite_estado`, `estado_en_fila` | El script del estado (`bin/estado.py` si existe), sus segundos (60) y leerlo dentro de la fila. |
| `titulo_ajustes`, `menu` | «Ajustes…» con otro nombre (`Some(None)`: sin él) y lo propio del menú (`archivo`, `ver`, `extra`). En Mac, Ajustes y Salir van en el menú de la app. |
| `bandeja`, `solo_barra_de_menu` | Ícono en la bandeja o la barra de menú (con `AlCerrar::Esconder`, siempre). `solo_barra_de_menu`: en Mac, sin ícono en el Dock. |
| `abrir_al_arrancar` | Sin decirlo: sí, salvo `--oculta` (al iniciar sesión). |
| `soltar` | Soltar archivos: el host guarda las rutas y avisa `soltados {nombres}` (y `soltando {encima}` mientras se arrastra encima, para marcar la zona); la app pide la ruta con `host.soltado(nombre)`. Sin esto, la página recibe su `drop` de HTML como siempre. |
| `lector_progreso`, `actualizaciones` | De las piezas `trabajos` (`progreso::Lector`) y `actualizaciones`. |
| `idioma_elegido`, `guardar_al_salir`, `devtools` | Si la app guarda el idioma en otro lado; si la interfaz atiende `menu({accion: "guardar"})`; herramientas de la página (solo en desarrollo). |

### Lo que tiene el `Host`

| | |
|---|---|
| `registrar(nombre, \|datos, host, ctx\| …)` | Una acción propia. Gana sobre las del host y las declaradas (se migra de a poco). Corre en un hilo propio: puede bloquear. |
| `llamar(funcion, json, destino)` | `window.<App>.<funcion>(json)`. Solo nombres simples; nada antes de `listo`. `destino`: `ctx.destino()` (la ventana que pidió). |
| `despues_del_estado(f)` | Justo después de mandarle el estado a la ventana principal (al abrir y con `enviar_estado`): p. ej. pedirle a la página algo que se arma con ese estado. |
| `config_de_interfaz(d)` | Lo que hace la acción `config` (guardar, menús en el idioma nuevo, apariencia, `al_cambiar_config`, tareas). Para una app que registra su propio `config` y después sigue con esto. `config.poner_propia(clave, valor)` guarda antes una clave que app.json no describe (un objeto propio, que la app valida). |
| `pedir(funcion, datos, limite)` | Le pide algo a la página principal y espera la respuesta (como `callAsyncJavaScript` en el Mac): la página lo atiende con `host.atender("<funcion>", async (datos) => …)` de «host-ui». `None` si no está lista, no responde a tiempo o falla. Bloquea: úsalo dentro de una acción. |
| `despachar(accion, datos, ctx)` | Correr una acción como si la pidiera la interfaz. |
| `inyector(fuente, …)`, `falta(texto, valores)` | Valores para el `inyectar` de las acciones (el host trae `idiomaUI`, `carpetaDatos` y, con `carpeta`, `carpetaActual`). |
| `registrar_medios(nombre, resolver)` | Lo que sirve `host.medio(nombre, ruta)`: el resolvedor devuelve la ruta absoluta o `None`. |
| `al_estado`, `al_iniciar_tareas`, `al_cambiar_config`, `antes_de_salir`, `al_tocar_aviso`, `al_soltar`, `al_crear_ventana` | Ganchos. |
| `config`, `idioma`, `t`, `f`, `procesador`, `fila`, `datos`, `recursos`, `app` | Lo mismo que en los otros hosts. `procesador.poner_entorno(\|\| …)`: variables para todos los scripts. Los programas que trae la app (`vendor/<os>/herramientas` de la pieza «empaquetado»: ffmpeg, whisper-cli…) llegan a cada script en `<ID>_HERRAMIENTAS` (`procesador.herramientas`; la app no la puede pisar). |
| `carpeta_actual`, `elegir_carpeta`, `usar_carpeta`, `olvidar_carpeta`, `vigilante()` | La carpeta de la persona y su vigilante. |
| `dialogo_carpeta`, `dialogo_archivos`, `guardar_archivo` | Diálogos del sistema (en el hilo de la ventana, como piden Mac y GTK). `guardar_archivo` dice cómo terminó: `Ok(ruta)` o `Err("cancelado" \| "vacio" \| "tamano" \| "extension" \| "escribir")`; `guardar_archivo_con(…, ComoGuardar {privado, maximo, desde, titulo})` cambia el tope (50 MB), la carpeta y el título. |
| `secretos(nombre)`, `notificaciones()` | El llavero del sistema (en Mac, el mismo servicio que `host-mac`: los tokens de siempre siguen ahí) y los avisos. |
| `agregar_ventana(etiqueta, pagina, ajustar)` | Otra ventana con la misma interfaz (panel, barra flotante): habla con el puente con las mismas guardas y recibe su respuesta. |
| `ocupar`, `soltar_ocupada`, `ocupada`, `esperar_libre(ms)`, `mostrar`, `salir` | Lo que no se puede cortar, y salir ordenado (guarda, espera 3 s, corta lo que siga). |

## Seguridad

- **El puente** es un solo comando de Tauri (`pieza`): solo de la ventana principal o de una agregada, y solo si su página está
  en `ui/`. La página no ve nada más de Tauri (`withGlobalTauri: false`); el contrato lo revisa.
- **La ventana** solo navega dentro de `ui/` y nunca abre otras ventanas: un enlace https va por `abrirEnlace`.
- **El protocolo** sirve solo archivos que de verdad están en `ui/` (sin `..` ni enlaces hacia afuera) y lo que apruebe el
  resolvedor de cada medio. Con rangos, en trozos de 4 MB.
- **Las acciones declaradas** se revisan al cargar con las mismas reglas que `pieza.py` (`pruebas/test_piezas.py` las compara
  compiladas de verdad) y cada mensaje se valida antes de correr nada. Lo de la persona va por archivo, un secreto por stdin.
- **Los secretos** van al llavero del sistema; si no hay (Linux sin gnome-keyring ni KWallet), no se guarda nada.

## Pasar una app a esta pieza

1. `pieza.py agregar host-tauri <app>` (trae `escritorio/src/pieza/`, genera el proyecto de Tauri y, con `trabajos` o
   `actualizaciones` instaladas, su parte en Rust).
2. Escribe `escritorio/src/main.rs` con lo propio: cada `p.registrar("x")` de Swift o `host.acciones.registrar("x")` de Electron
   pasa a `host.registrar("x", …)`. Lo que solo corría un script ya está declarado: no se toca.
3. En la interfaz, cada `<id>://video/${…}` armado a mano pasa a `host.medio("video", ruta)`.
4. Borra `app/` (Swift), `escritorio/src/*.js`, `escritorio/package.json`, `escritorio/.npmrc` y `escritorio/node_modules/`.
5. `pieza.py agregar empaquetado <app>` (0.2): `herramientas/empaquetar.sh <mac|windows|linux>` y `publicar.yml` con Tauri.
6. `cd escritorio && cargo run` para probar; `bash pruebas/correr.sh` (compila y prueba el Rust si hay cargo).

**Lo que solo existe en Apple** (capturar pantalla o audio con ScreenCaptureKit, dictado, diarización): no se reescribe en Rust.
Queda como un **ayudante** pequeño en Swift (un ejecutable aparte) que la app corre igual que un script de `bin/`, con su entrada
y su salida JSON. Falta armarlo en `empaquetado` (llega al pasar Minuta y Graba, las que lo necesitan).

**Secretos guardados en Windows y Linux con Electron:** quedaron cifrados con la llave de Chromium y Rust no puede leerlos. La
persona vuelve a conectar su cuenta una vez. En Mac no pasa: es el mismo Llavero y el mismo servicio.

## Pruebas

- `pruebas/tauri/` (en Pieza): `cargo test` (enchufe, procesador, protocolo, vigilante, sistema, host, progreso,
  actualizaciones) y `bash arranque.sh`, que abre la app de prueba de verdad con Xvfb y revisa el puente de punta a punta.
- `pruebas/test_piezas.py` → `HostGenerico`: las reglas de una acción son las mismas en `pieza.py`, `enchufe.js` y `enchufe.rs`.
- En cada app, `pruebas/correr.sh` corre `cargo test` de `escritorio/` si hay cargo.
