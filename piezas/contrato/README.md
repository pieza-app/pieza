# Pieza «contrato» — que la interfaz y cada plataforma digan lo mismo

Una sola prueba del puente para todas las apps (`pruebas/contrato.py`). Antes cada app tenía la suya, de 120 a 240 líneas, que
revisaban casi lo mismo; ahora la app copia esta y pone solo lo propio en **`pruebas/contrato_app.py`** (opcional, chico; la pieza
nunca lo toca).

```bash
python3 <pieza>/herramientas/pieza.py agregar contrato .
python3 pruebas/contrato.py                    # en pruebas/correr.sh de la app
python3 pruebas/contrato.py --json             # para otra herramienta
python3 <pieza>/piezas/contrato/python/contrato.py --app ../otra-app   # revisar otra app sin escribir nada en ella
```

## Qué revisa (sin código de la app)
1. **Cada acción** que manda la interfaz — `host.enviar("x")` en el código propio de `ui/` y lo que mandan por su cuenta las piezas de
   interfaz (`componentes`: `probarIA`, `config`, `buscarActualizacion`, `actualizar`, `abrirEnlace`) — la atiende **cada plataforma**
   que la app tiene en el repo: **registrada** (Mac `p.registrar("x")`; Electron `host.acciones.registrar("x", …)`, `A.registrar`
   o el objeto `ACCIONES` registrado con `Object.entries`; celular `ACCIONES` y `SOLO_MAC` de `movil/host/host.js`), **del host**
   (`listo`, `config`, `abrirEnlace`, `copiar` y, si la app le pasa la pieza «actualizaciones», `buscarActualizacion` y `actualizar`)
   o **declarada** en `acciones.json`. Y la **vista previa** la responde (`case "x"` de `simular()`, las claves de `const SIMULAR`,
   y las de `PiezaHost.simulacionesComunes()` si `simular()` las usa).
2. **Nada sobra**: registrada que nadie pide (`sobra-<plataforma>`), registrada y declarada a la vez (`doble-<plataforma>`: gana la
   registrada), declarada que nadie pide (`sobra-declarada`: va en `app.json` → `sin_acciones`).
3. **`acciones.json` al día** con lo que arma `pieza.py acciones` (las de las piezas en `piezas.json` + `app.json` → `acciones` −
   `sin_acciones`), sus scripts existen en `bin/`, tienen `limite` y ningún `$campo` de `args` es texto (solo `enum` o `entero`).
4. **Cada función** que llaman las plataformas (`llamar("x")`, `window.<App>.x`, `A().x` en el celular, y lo que llama el host) o que
   responde una declarada (`responde`, `progreso`) existe en `window.<App>` (`host.responder({…})`; el nombre sale de `crearHost`).
   `copiado` solo cuenta si la interfaz usa `copiar`.
5. **Seguridad común**: CSP de `ui/index.html` con `script-src 'self'` (o `default-src 'self'` sin `script-src`), sin `unsafe-*`;
   sin `<script>` en línea ni `on…=`; ningún archivo propio (Swift o Electron) arma el comando de una IA (`--disallowedTools`,
   `"claude", [`…: eso es de `bin/ia.py`); `app/Info.plist` y el de iOS sin `NSAppTransportSecurity`; el bundle id de
   `Info.plist` igual al de `--requirements '=designated => identifier "…"'` de `empaquetar.sh`; `acciones.json` dentro del paquete
   (`empaquetar.sh` y `extraResources`); la misma versión en `Info.plist` y `escritorio/package.json`; ventanas propias de Electron con
   `sandbox` y `contextIsolation`; `escritorio/.npmrc` con `ignore-scripts=true`; Capacitor sin `server.url`/`cleartext`/
   `allowNavigation`; Android con `allowBackup="false"` y `usesCleartextTraffic="false"` y sin componentes exportados de más; cada
   `llamar("Plugin", "metodo")` del celular existe en Swift, en Kotlin/Java y en `pruebas/capacitor_falso.js` (los oficiales de
   Capacitor, solo si están instalados).
6. Con la pieza «pagina»: `docs/pagina.json` → `usa.llavero`/`usa.notificaciones` dice lo que el código usa (`Secretos(`,
   `Notificaciones`, `host.notificaciones`): la página no promete de más ni de menos.

Cada problema tiene un **código** (`mac:x`, `simular:x`, `funcion:x`, `csp`, `bundle`…).

## `pruebas/contrato_app.py` (lo propio)

```python
EXCEPCIONES = {"escritorio:soloMac": "solo en Mac: usa EventKit"}   # «código» → motivo. Una que ya no hace falta, se avisa.
UI = ["ui/proyectos.js"]                        # más archivos de la interfaz (por omisión, todo ui/**/*.js que no es de una pieza)
ENVIA = [r'data-av="(\w+)"']                    # más formas de mandar una acción
REGISTRADAS = {"mac": [r'case "(\w+)"']}        # más formas de registrar lo nativo, por plataforma (mac, escritorio, movil)
LLAMADAS = [r'llamarFuncion\([^"]*"(\w+)"']     # más formas de llamar window.<App>.x
SWIFT = ["app/Sources/Minuta/VisorWeb.swift"]   # dónde está el Swift propio (carpetas o archivos)
DEL_HOST = {"mac": []}                          # si la app no usa el puente del host en una plataforma
PLUGINS = {"Camera": ("movil/node_modules/@capacitor/camera/ios/**/*.swift", "…/android/**/*.java")}
def revisar(c):                                 # lo propio: c.leer(r), c.json(r), c.acciones, c.funciones, c.declaradas,
    if "proyecto" not in c.declaradas: c.problema("propio", "", "…")   # c.registradas[plataforma], c.problema(código, cosa, texto)
```

## Corrido contra las seis apps (nov 2026, solo lectura)

| App | Sin extensión | Qué pondría en `contrato_app.py` |
|---|---|---|
| Graba | ✓ (25 acciones, Mac y Windows/Linux) | Sus revisiones propias en `revisar`: `graba://video` con `Rutas.videoDe`/`videoDe`, `PAGINAS`, `alCerrar: "esconder"`, `userData`, el token de YouTube (Llavero y `.tokens`, nunca a la interfaz). |
| Corta | ✓ (27 acciones, Mac) | `revisar`: la carpeta de un proyecto por el inyector `proyecto`, las de `cola: "escritura"`, `Rutas.proyecto`/`Medios.archivo`, `CORTA_PROGRAMAS`, `corta://video/`. |
| Alcancía | `mac:traer` | `EXCEPCIONES = {"mac:traer": "traer la copia cifrada es solo del celular"}`; `revisar`: lo de Android que es solo de Alcancía (sin INTERNET, `data_extraction_rules`, solo los permisos de avisos), dependencias exactas en `movil/`, probarIA `{ia}`. |
| Repasa | `movil:actualizar`, `movil:soltarMaterial` | `EXCEPCIONES` con esas dos («el teléfono no instala versiones», «arrastrar material es del computador»); `PLUGINS` no hace falta (Camera y Filesystem se buscan solos en `node_modules`); `revisar`: sin `<a href>` en la interfaz (es para niños), enlaces solo de Repasa, `Copia.swift`, guiones con `comillas()`. |
| Esquema | 4 × `sobra-declarada` (`catalogoInstalados`, `catalogoQuitar`, `catalogoUltima`, `listaIA`) | Mejor que una excepción: sumarlas a `app.json` → `sin_acciones` (hoy el host las carga sin que nadie las pida). `UI = ["ui/proyectos.js"]` ya no hace falta (se leen todos los `ui/*.js` propios). `revisar`: `puente.json`, `proyecto` con sus `ORDENES`, límites por orden, `abrirArchivo`/`guardarArchivo` con `vigilar`, carpeta inyectada, catálogo, Electron ≥ 44.9.1. |
| Minuta | 105 (no usa `Host.arrancar` ni `p.registrar`: sus puentes son `switch` en `VisorWeb.swift`/`BarraMenu.swift`) | `SWIFT = ["…/VisorWeb.swift", "…/BarraMenu.swift"]`, `REGISTRADAS = {"mac": [r'case "(\w+)"']}`, `DEL_HOST = {"mac": []}`, `ENVIA = [r'data-av="(\w+)"', r'data-pn="(\w+)"']`, `LLAMADAS = [r'llamarFuncion\((?:[^,"]+,\s*)?"(\w+)"']`, `EXCEPCIONES` para `mac:calendarioICS` y los `case` del teclado que no son acciones (`sobra-mac:a`, `…:zoom`). Con eso quedan cosas reales: **47 acciones sin vista previa** (`simular`), `abrirEnlace` y `config` que manda «componentes» sin caso en Mac, `menu` y `copiado` que llama el host de Electron sin función en `window.Minuta`, y dos ventanas de Electron (`alerta`, `grabadora`) sin `sandbox: true` explícito. |

## Pruebas
`pruebas/test_pagina_contrato.py` (`Contrato`): una app ficticia con host-mac, host-escritorio, componentes e ia; en orden, lo que
detecta (acción sin atender, sin vista previa, ventana sin sandbox, manejador en línea, bundle id distinto, función que no existe,
`acciones.json` atrasado, texto como argumento), excepciones con motivo y que avisan si sobran, `revisar` propio y `--app` sin escribir.

## Revisar a mano
Nada nativo: es Python con la biblioteca estándar. Lo que lee de Swift y JS es por patrones: si una app registra de otra forma, va en
`REGISTRADAS`/`LLAMADAS` de su extensión (y, si sirve para todas, aquí).
