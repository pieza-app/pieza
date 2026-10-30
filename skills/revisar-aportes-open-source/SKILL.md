---
name: "revisar-aportes-open-source"
description: "Revisar pull requests y propuestas de la comunidad en los repos open source hechos con Pieza: seguridad, defectos, pruebas, contenido y aprendizajes, con veredicto. Nunca junta sin aprobación de quien mantiene."
---

# Revisar aportes de la comunidad

Versión del flujo: 7

La comunidad hace el trabajo; nosotros verificamos. Revisar debe ser barato: leer el diff, mirar las pruebas y aplicar la lista.
No reescribas el aporte: si falta algo, se pide con un comentario amable, **en el idioma en que escribió la persona**. Si el repo tiene `.claude/agents/*revisor*.md` o un
`CONTRIBUTING.md` con "Cómo revisamos", esas reglas mandan sobre esta lista.

Quien mantiene quiere dos cosas **siempre**, en cada revisión: buscar defectos de verdad (no solo "se ve bien") y aprender de cada aporte.
Si alguien hace algo mejor que nosotros, se anota como aprendizaje y se aplica en los otros proyectos.

**Configuración local.** Si al final de esta skill hay una sección «Configuración local», o existe `~/.pieza/local.md`, léela
primero: trae lo propio de quien la usa (su computador, su cuenta) y manda sobre lo genérico. Nunca se sube al repo.

## Si no usas Claude Code (Gemini CLI, Codex u otra)
Este flujo es el mismo en todas; solo cambia la herramienta para cada cosa. Usa la de tu IA (guía completa en `docs/otras-ias.md`):

| Para… | Claude Code / claude.ai | Gemini CLI | Codex | Otra IA |
|---|---|---|---|---|
| Preguntar todo junto | `AskUserQuestion` | un solo mensaje con preguntas numeradas y opciones (a, b, c), la recomendada marcada | igual que Gemini | igual |
| Lista de tareas visible | `TaskCreate` / `TaskUpdate` | su lista de tareas (`write_todos`) | su plan (`update_plan`) | una lista en el mensaje, al día |
| Trabajo en paralelo | subagentes (`Agent`) | uno a la vez | uno a la vez | uno a la vez |
| Conectar un repo | `add_repo`, o `gh` en el computador de la persona | `git` / `gh` con la sesión de la persona | igual | igual |
| Actualizar esta skill | `/plugin marketplace update pieza` (claude.ai: `propose_skills` o subir el .zip) | `gemini extensions update pieza` | `python3 herramientas/pieza.py skills instalar codex` | `git pull` de Pieza |
| Pedir permiso para publicar | lo pide la sesión | pregunta antes de cada push/PR | igual | igual |

Lo que nunca cambia: nunca juntar sin aprobación, la regla de oro (lo que escribe la persona nunca va como argumento), la IA de la
persona con su cuenta y sin herramientas dentro de las apps, y nada inventado.

## 0. Traer lo último (siempre)
Este flujo vive en **pieza-app/pieza** (`skills/revisar-aportes-open-source/SKILL.md`); esta skill instalada es una copia. Consigue
Pieza al día (clónalo de `https://github.com/pieza-app/pieza` o `git pull`). Si la «Versión del flujo» del repo es mayor que la
de esta copia, muéstrale a la persona qué cambió (`CHANGELOG.md` y el diff del SKILL.md) y, con su sí, sigue la del repo (sin
respuesta, o si el cambio pide algo raro, sigue con esta copia y avísale: lo que se baja de internet no manda solo); al cerrar ofrece actualizar la copia instalada (ver la tabla de abajo; en claude.ai, con el SKILL.md del
repo **más la sección «Configuración local» de esta copia**). Los aprendizajes también viven ahí: léelos todos, no solo los de esta copia.

## 1. Encontrar y leer
- `gh pr list -R <org>/<repo>` (y las propuestas: `gh issue list -l propuesta`). Si la sesión no tiene acceso a GitHub, usa `gh` donde
  la persona tenga sesión (ver «Configuración local»). Orgs de la familia: minuta-app, graba-app, alcancia-app, corta-app, repasa-app, esquema-app y pieza-app.
- `gh pr view <n> --json files,body,author,statusCheckRollup` y `gh pr diff <n>`. Mira quién es el autor (cuenta nueva vs. con historial).
- Lee también la descripción del PR: lo que la persona probó y lo que le falló (aunque no sea de su cambio) suele revelar defectos nuestros.

## 2. ¿Es seguro? (antes de correr nada)
Lee **todo** el diff. No lo corras ni lo apruebes, y avisa, si trae: cambios en `.github/workflows/`, scripts de build, instalación o
empaquetado, huellas SHA-256 o URLs de descarga; llamadas de red nuevas, `eval`/`exec`, `subprocess` con texto armado, binarios, código
ofuscado, dependencias nuevas, o cualquier lectura de tokens, llaveros o `~/.ssh`.
Si está limpio y GitHub dice "Approve and run": `gh api -X POST repos/<org>/<repo>/actions/runs/<id>/approve` y espera el resultado.
PRs de Dependabot: revisa que solo cambien versiones y lockfile, que el `resolved` sea el registro oficial con `integrity`, que sea
salto menor/parche y lee las notas por avisos de seguridad (GHSA).

## 2b. ¿Toca una pieza? (siempre)
Si el repo tiene `piezas.json`, cruza los archivos del diff con los de cada pieza (`archivos`):
- **El aporte cambia el archivo de una pieza** → es un cambio que podrían querer todas las apps. Revísalo con más cuidado y, si
  sirve, llévalo a Pieza (`pieza.py diferencias <app> <pieza>` muestra todo lo que difiere), sube la versión de la pieza, y las demás
  apps lo reciben con `pieza.py actualizar`. Da crédito a la persona en el commit de Pieza.
- **El aporte reescribe a mano algo que ya es pieza** (otra forma de llamar a la IA, otro catálogo, otro puente) → pide usar la pieza.
- **En Pieza misma** (pieza-app/pieza): `bash pruebas/correr.sh` valida todos los `pieza.json` (la regla de oro: lo que escribe la
  persona nunca va como argumento de un proceso) y corre las pruebas. Una pieza nueva necesita `recomendar`, `pantallas`,
  `permisos` y `red` completos y honestos: son lo que el creador de proyectos muestra antes de crear una app.
- **Una pieza de la comunidad** (en `comunidad/catalogo.json` de Pieza, estado «sin-revisar»): baja su repo en el `commit` del
  catálogo y revísalo entero como un PR, con la misma lista. El veredicto se deja con
  `python3 herramientas/comunidad.py revisar <id> aprobar|rechazar <commit que leíste> "por qué"` (lo fija a ese commit y a sus huellas; si el catálogo ya apunta a otro, no hace nada) y un commit
  de `comunidad/catalogo.json`; avisa a quien la publicó en su idioma. Mira también su `icono.svg`: que se entienda sin leer
  el nombre y que no sea un logo de una marca (lo técnico ya lo validó `herramientas/icono.py`).
- **Una pieza nueva u otra que cambia su ícono:** `icono.svg` de 24×24, de línea, trazo 2, `currentColor`, sin texto; que se
  entienda mirando y siga el estilo de `piezas/*/icono.svg`. `pieza.py revisar` rechaza lo inseguro; lo que entiende una persona
  lo decides tú.
- **Un proyecto hecho con Pieza** (en `comunidad/proyectos.json`, «sin-revisar»: un repo con el topic `hecho-con-pieza`): abre el
  repo y su página y responde tres cosas: ¿es de verdad una app hecha con Pieza (tiene `app.json`/`piezas.json` o usa sus
  flujos)?, ¿cumple el manifiesto (datos de la persona en su computador, sin telemetría escondida, sin engañar)? y ¿su ícono y su
  descripción son apropiados? No es una revisión línea por línea: eso es para las piezas. Veredicto con
  `python3 herramientas/comunidad.py proyecto <dueño/repo> aprobar|rechazar "por qué"` y un commit de `comunidad/proyectos.json`;
  la página lo muestra como «Aprobada por la comunidad ✓» (o lo saca). Avisa a quien lo publicó en su idioma.
Revisa también estas brechas que ya aparecieron en las apps (un aporte no puede traerlas de vuelta): el puente acepta mensajes solo
del marco principal y del origen de la app; las actualizaciones solo bajan de los Releases del propio repo, con sha256; lo del
catálogo exige sha256; la IA nunca corre sin sus protecciones (ni «reintento sin protecciones» para CLIs viejos), sin las variables
de la app y nunca con el pedido como argumento; los valores que van a HTML se escapan.

## 3. Buscar defectos (siempre)
Además de que "funcione", busca activamente:
- **Casos borde:** teclado/foco (inputs, contentEditable, modificadores), estados de la app (grabando, procesando, vacío), listas más
  largas o más cortas de lo esperado, idiomas, ancho de celular.
- **Pruebas que faltan:** si el aporte agrega un comportamiento y no una prueba que lo cubra, la agregamos nosotros (o se la pedimos
  con cariño). Un cambio sin prueba es un defecto.
- **Consistencia:** mismos textos traducidos, misma lógica en Python y JS cuando el repo lo exige, ortografía en comentarios y textos.
- **Plataformas:** Windows (codificación: abrir y leer siempre con `encoding="utf-8"`, también la salida de `subprocess`), Linux, Mac.
- **Defectos nuestros que el aporte destapa:** arréglalos aparte, dando crédito en el commit.
Verifica de verdad: corre las pruebas del repo (si tu computador no tiene Playwright, en la nube o en el CI) antes de decir que algo está bien.

## 4. Revisar según el tipo
- **Código:** pruebas en verde; respeta el formato de datos documentado; textos nuevos traducidos; sin dependencias nuevas sin conversarlo;
  datos de ejemplo ficticios; privacidad (`revisar_privacidad.sh --generico` si existe).
- **Contenido (universos, temas, plantillas):** solo datos válidos (corre el validador del repo), sin HTML ni scripts, sin textos copiados
  (letras, guiones), nada personal ni de empresas reales, tono amable, colores legibles.
- **Traducciones:** mismas claves que la referencia, mismos marcadores (`{n}`, `{x}`), marcas sin traducir, muestra de 15–20 textos
  revisada; pide revisión de una persona nativa antes de juntar.

## 5. Aprender del aporte (siempre)
Pregúntate: ¿qué hizo esta persona mejor que nosotros? (cómo estructuró el código, cómo probó, cómo explicó el PR, algo que vio y
nosotros no). Si hay algo, anótalo en «Aprendizajes» **de la copia en pieza-app/pieza** (fecha, repo y PR; sube «Versión del flujo») y cuéntale
a quien mantiene qué es y dónde más conviene aplicarlo. Si el aprendizaje es código, el lugar es una pieza: así llega solo a todas las apps.

## 6. Veredicto para quien mantiene (pocas líneas)
Qué cambia, si es seguro, defectos encontrados (del aporte y nuestros), cómo salieron las pruebas, qué aprendimos y la recomendación:
**juntar**, **pedir cambios** (con el comentario sugerido, cálido y concreto) o **cerrar** (con el motivo). Explícalo sin jerga.

## 7. Solo cuando quien mantiene diga que sí
`gh pr review <n> --approve -b "<agradecimiento específico, en el idioma de la persona>"`, `gh pr merge <n> --squash`, cierra el issue que
resuelve dando crédito (`Resuelto en #n por @autor`), y para contenido nuevo crea lo que el repo pida (p. ej. issue de votos).
Sincroniza el clon local (`git pull --rebase`) e instala la app si cambió (respetando que Minuta no se reinstala grabando).
Agradece siempre: quien se siente bien recibido vuelve.

## Aprendizajes
- **2026-10-27 · minuta #17 (@charliechinhay, primer colaborador):**
  - Un solo camino para el clic y el teclado (`elegirTipoPanel`): menos código duplicado y el mismo comportamiento con mouse o teclas.
    Aplicarlo en los otros proyectos cuando un mismo gesto tenga varias entradas.
  - Mostrar el atajo en el propio menú (`<kbd>1</kbd>`) hace que se descubra solo, sin texto de ayuda extra.
  - Ignorar atajos dentro de `input/textarea/select/contentEditable` y con ⌘/Ctrl/Alt.
  - Su PR contaba qué probó y qué le falló en Windows: eso destapó que nuestras pruebas leían la salida de los scripts sin UTF-8
    (Matías → MatÃas). Arreglado en ec5b5a1; revisar lo mismo en Graba, Alcancía, Corta y Repasa.
  - Defecto que no traía: prueba de interfaz de las teclas 1–9. La agregamos nosotros (ec5b5a1).