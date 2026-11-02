# Pieza — guía para trabajar en la base

> Para personas y para cualquier IA de programación (Claude Code, Codex, Gemini/Antigravity…). `CLAUDE.md` y `GEMINI.md` solo
> importan este archivo.

Pieza es la base de la familia de apps (Minuta, Graba, Corta, Alcancía, Repasa, Esquema y las que vengan). Guarda **piezas**:
código probado que se enchufa en cualquier app en vez de escribirlo de cero. El objetivo es hacer apps nuevas más rápido y con
menos tokens: elegir piezas, no reescribirlas.

## Antes de escribir algo en una app

0. **¿Es una app nueva?** `python3 herramientas/pieza.py crear <carpeta> --id … --nombre … --plataformas … [--piezas …]` la deja
   andando de una vez (con sus pruebas en verde); la IA escribe solo lo que el comando dice al final.
1. **Mira `docs/catalogo.md`.** Si la pieza existe, `python3 herramientas/pieza.py agregar <pieza> <app>`. No la reescribas.
2. **Si está «por extraer»**, extráela aquí primero (abajo) y después agrégala a la app. Una vez, para todas.
3. **Si es nueva y la van a necesitar dos apps o más**, nace aquí como pieza. Si es solo de una app, va en la app.
4. **Si es de alguien más**, puede vivir en su repo como pieza de la comunidad (`docs/comunidad.md`): se instala segura solo
   cuando está revisada.

## Cómo se hace una pieza

1. Carpeta `piezas/<id>/` con `pieza.json` (formato en `docs/enchufe.md`), su código (`python/`, `ui/`, `mac/`, `escritorio/`; lo
   que cambia por app y no es código —un `Info.plist`, un workflow— va en `plantillas/` y se **genera**: «Plantillas» en `docs/enchufe.md`),
   su `icono.svg` (obligatorio: 24×24, de línea, trazo 2, `currentColor`, solo formas; `herramientas/icono.py` lo valida),
   un `README.md` corto (qué resuelve, API, ejemplo) y lo que necesite en `pruebas/test_piezas.py` (o `test_piezas_datos.py` para las de datos).
2. **Partir de la mejor versión** que ya exista en las apps y sumarle lo que otras resolvieron mejor. Decir de dónde salió en
   `origen`.
3. **Nada de la app adentro**: ni nombres, ni rutas, ni prefijos. Lo que cambia por app sale de `app.json` (`nucleo.app()`).
4. Correr `bash pruebas/correr.sh` (valida todos los `pieza.json` y corre las pruebas).
5. Subir `version` (X.Y.Z) si cambia lo que la app recibe y anotarlo **en `cambios` del `pieza.json`** (tipo `arreglo`, `mejora` o
   `rompe` con sus pasos en `migrar`; `seguridad: true` si corresponde) y en `CHANGELOG.md`. Si cambia lo que otra pieza
   necesita, ajusta su `compatible`. Esto es lo que «Pieza al día» le avisa a cada app: escríbelo para quien lo va a leer.
6. Actualizar `docs/catalogo.md` (mover la fila de «por extraer» a «listas»).

## Las reglas que no se negocian (heredadas de las apps)

- **Solo biblioteca estándar** en Python; sin dependencias ni CDN en la UI.
- **La IA es la de la persona**, con su cuenta, sin herramientas ni memoria, y el pedido **nunca** como argumento del proceso.
- **Lo que escribe la persona nunca va como argumento** de un proceso: va por archivo de entrada o por la entrada estándar.
- **Todo lo que viene de afuera se valida** (catálogos, traducciones, respuestas de la IA) y se escapa antes de mostrarse.
- **Los datos son de la persona**: en su computador o en su git, nunca en un servidor nuestro.
- **El idioma se pregunta primero** en toda bienvenida.
- **Nada personal en el código**: ejemplos y pruebas con datos ficticios (Ana Pérez, Matías Soto).
- **Liviano**: poco consumo, sin sacrificar que se vea bien.

## El host (app nativa)

`host-mac` (Swift) y `host-escritorio` (Electron) son la app nativa genérica. Una acción que solo corre un script **no se programa
en el host**: se declara en el `pieza.json` de la pieza (o en `app.json` → `acciones` si es de la app) y `pieza.py` arma
`acciones.json`. Lo nativo propio se registra en la app; lo nativo que usan dos apps o más (carpeta, vigilante, secretos,
avisos…) va en los dos hosts con la misma API. Si cambias las reglas de una acción, cámbialas en los tres lados
(`errores_accion` de `pieza.py`, `enchufe.js` y `Enchufe.swift`): `test_piezas.py` (`HostGenerico`) los compara. Swift no compila
aquí: imita código que ya compila y deja anotado qué revisar en el Mac (`pruebas/swift/revisar_host_mac.sh`).

## Cuando una app mejora una pieza

Las piezas se copian y la app es dueña de su copia. Si en una app se arregla o mejora una pieza:
`pieza.py diferencias <app> <pieza>` muestra el cambio. Si sirve para todas, se trae aquí, se sube la versión y las demás apps
lo reciben con `pieza.py actualizar <app>` (que nunca pisa lo que una app cambió).

## El creador de proyectos (la skill)

`skills/lanzar-proyecto-open-source/SKILL.md` es la versión oficial del flujo para crear una app nueva; las skills instaladas son
copias que, al usarse, comparan su «Versión del flujo» con esta y siguen la más nueva. El creador no tiene piezas escritas
adentro: las lee con `pieza.py catalogo` y `pieza.py ficha`. Por eso:
- **Pieza nueva o campo nuevo** (pantallas, permisos, red, tareas) → aparece solo en el creador. No hay que tocar la skill.
- **Paso nuevo en el flujo** o aprendizaje → editar ese SKILL.md, subir «Versión del flujo» y anotarlo en `CHANGELOG.md`.
- Igual con `skills/revisar-aportes-open-source/`: sus «Aprendizajes» se anotan aquí, no en la copia instalada.
- **Las skills sirven en cualquier IA.** Nunca nombres una herramienta de una sola IA sin su equivalente: usa la tabla «Si no usas
  Claude Code» de cada skill (y `docs/otras-ias.md`). Al cambiar la versión, sube igual `.claude-plugin/plugin.json` y
  `gemini-extension.json` (la prueba lo revisa): así se actualizan Claude Code y Gemini CLI.

## Mapa

| Ruta | Qué es |
|---|---|
| `piezas/<id>/` | Cada pieza: `pieza.json` + código + README |
| `herramientas/pieza.py` | `crear` (una app nueva andando de una vez: las piezas + el esqueleto de la pieza `esqueleto` + todo lo generado; dice qué le toca a la IA y a la persona), `listar`, `catalogo`, `ficha`, `iniciar`, `agregar`, `estado`, `actualizar`, `aviso`, `diferencias`, `revisar`, `acciones` (arma `acciones.json` para el host), `generar` (vuelve a llenar lo que generan las piezas desde `app.json`), `repo configurar` (los `gh` que dejan el repo de una app listo), `skills estado/instalar` |
| `herramientas/plantillas.py` | El motor de las plantillas (`pieza.json` → `generar`): solo datos, filtros que escapan o validan; ver `docs/enchufe.md`, «Plantillas». Lo usan `empaquetado`, `github`, `pagina` y `esqueleto` |
| `docs/enchufe.md` | El contrato: `pieza.json`, `app.json`, `piezas.json`, reglas de seguridad, host genérico |
| `docs/catalogo.md` | Qué piezas hay, cuáles faltan y en qué orden, y brechas encontradas en las apps |
| `comunidad/catalogo.json`, `herramientas/comunidad.py`, `.github/workflows/comunidad.yml` | El catálogo de la comunidad: piezas en repos de otras personas (topic `pieza-comunidad`), validadas cada día (ícono incluido) y con su estado de revisión fijado a un commit y a la huella de cada archivo. Guía en `docs/comunidad.md` |
| `comunidad/proyectos.json` | Las apps hechas con Pieza (topic `hecho-con-pieza`) con su ícono validado y su revisión (`comunidad.py proyecto <dueño/repo> aprobar\|rechazar`). La página las muestra; las rechazadas no |
| `herramientas/icono.py` | Valida un ícono SVG que viene de afuera (solo formas, sin scripts ni enlaces, ≤ 8 KB). Lo usan `pieza.py revisar`, `comunidad.py` y `pagina.py` |
| `plantillas/pieza-al-dia.yml` | El workflow que `iniciar` agrega a cada app para que se entere de las versiones nuevas |
| `docs/` | La página pública (`index.html`, `pagina.js`, `pagina.css`, `sello.svg`) y los datos que arma `herramientas/pagina.py` |
| `.claude-plugin/` | El plugin de Claude Code (las skills de `skills/`) y su marketplace |
| `gemini-extension.json`, `gemini/contexto.md`, `commands/pieza/` | La extensión de Gemini CLI: las mismas skills, su contexto y los comandos `/pieza:crear` y `/pieza:revisar` |
| `.agents/skills/` | Enlaces a `skills/` para que Codex las vea dentro del repo (`pieza.py skills instalar codex` las deja en `~/.agents/skills`) |
| `docs/otras-ias.md` | Cómo usar Pieza en Claude Code, Gemini CLI, Codex u otra IA, y la tabla de equivalencias |
| `skills/` | Los flujos oficiales (las skills), cada uno con su «Versión del flujo»: `lanzar-proyecto-open-source` (crear una app) y `revisar-aportes-open-source` (revisar PRs, con sus aprendizajes) |
| `MANIFIESTO.md` | Lo que creemos (español e inglés): compartir, crear, sin fines de lucro, tu computador y tu IA son tuyos. Toda decisión se mide contra esto |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | Cómo aportar (sin programar, con o sin IA, proponer una pieza, aportar a un flujo, cómo revisamos), código de conducta y cómo reportar una falla en privado (qué cubre: `pieza.py`, plantillas, «Pieza al día», las piezas) |
| `.github/` | `workflows/` (`revisar.yml`, `pagina.yml`: actions fijadas por SHA, permisos mínimos, `persist-credentials: false`), `ISSUE_TEMPLATE/` (error, idea, pieza, probar; seguridad y Discussions en `config.yml`), `pull_request_template.md` (checklist) y `dependabot.yml` (solo actions, con `cooldown`) |
| `herramientas/revisar_privacidad.sh` | Busca datos personales antes de cada commit (`.terminos-privados`, local y nunca versionado); `--generico` corre en `pruebas/correr.sh` |
| `.claude/agents/` | `pieza-revisor` (revisar PRs: regla de oro, ficha honesta, versión y cambios, brechas conocidas; nunca junta sin aprobación) y `pieza-privacidad` (antes de cada commit) |
| `pruebas/` | `correr.sh` (valida los `pieza.json`, la versión de cada flujo, que toda action esté fijada por SHA y que la plantilla «Pieza al día» use las mismas versiones, la privacidad, `test_piezas.py`: una app ficticia con CLIs de IA falsos, y `test_piezas_datos.py`: red, catálogo, transcribir, trabajos, contenido e IA en vivo con servidores, whisper y CLIs falsos), `piezas_js.mjs` (las piezas de JavaScript en Node), `host_escritorio.mjs` (el host de Electron en Node, con un Electron falso) y `host_escritorio_electron.mjs` (con Electron de verdad y Xvfb, si `ELECTRON` apunta a uno), `test_pagina_contrato.py` (las piezas `pagina` y `contrato` con una app ficticia), `test_crear.py` (`pieza.py crear` de dos apps, Receta y Nota, y sus propias pruebas en verde; con `ELECTRON`, `crear_electron.mjs` abre la de Linux) y `pagina.mjs` (la página generada en Chromium), `swift/revisar_host_mac.sh` (solo en un Mac: compila y prueba `host-mac`) e `interfaz.mjs` (las piezas de interfaz en Chromium con Playwright, con la CSP de las apps: foco, tema, contraste AA, 390 px; sin Playwright se salta) |

Licencia AGPL-3.0, como las apps.
